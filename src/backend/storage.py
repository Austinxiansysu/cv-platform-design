"""Small SQLite store. Frozen AI payloads remain intact as JSON documents."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not path.exists():
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS profiles (
                    profile_version TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    company TEXT,
                    title TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS matches (
                    match_id TEXT PRIMARY KEY,
                    profile_version TEXT NOT NULL REFERENCES profiles(profile_version),
                    job_id TEXT NOT NULL REFERENCES jobs(job_id),
                    alignment_json TEXT NOT NULL,
                    score_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS applications (
                    application_id TEXT PRIMARY KEY,
                    job_id TEXT REFERENCES jobs(job_id),
                    match_id TEXT REFERENCES matches(match_id),
                    company TEXT NOT NULL,
                    role TEXT NOT NULL,
                    applied_on TEXT,
                    status TEXT NOT NULL,
                    interviewed INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS applications_updated_idx
                    ON applications(updated_at DESC);
            """)

    def create_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        version = payload["profile_meta"]["profile_version"]
        created = _now()
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO profiles VALUES (?, ?, ?)", (version, _json(payload), created)
            )
        return {"profile_version": version, "created_at": created}

    def get_profile(self, version: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload_json FROM profiles WHERE profile_version = ?", (version,)
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        meta = payload["job_meta"]
        created = _now()
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, ?, ?)",
                (meta["job_id"], meta["company"], meta["original_title"], _json(payload), created),
            )
        return {"job_id": meta["job_id"], "created_at": created}

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload_json FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_jobs(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT job_id, company, title, created_at FROM jobs ORDER BY created_at DESC, job_id"
            ).fetchall()
        return [dict(row) for row in rows]

    def create_match(self, alignment: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
        meta = alignment["match_meta"]
        created = _now()
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO matches VALUES (?, ?, ?, ?, ?, ?)",
                (
                    meta["match_id"], meta["profile_version"], meta["job_id"],
                    _json(alignment), _json(score), created,
                ),
            )
        return {"match_id": meta["match_id"], "created_at": created, "score": score}

    def get_match(self, match_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT alignment_json, score_json, created_at FROM matches WHERE match_id = ?",
                (match_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "alignment": json.loads(row["alignment_json"]),
            "score": json.loads(row["score_json"]),
            "created_at": row["created_at"],
        }

    def create_application(self, values: dict[str, Any]) -> dict[str, Any]:
        application_id = str(uuid4())
        created = _now()
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT INTO applications
                (application_id, job_id, match_id, company, role, applied_on, status,
                 interviewed, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    application_id, values["job_id"], values["match_id"], values["company"],
                    values["role"], values["applied_on"], values["status"],
                    int(values["interviewed"]), values["notes"], created, created,
                ),
            )
        return self.get_application(application_id)

    def get_application(self, application_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM applications WHERE application_id = ?", (application_id,)
            ).fetchone()
        if row is None:
            return None
        value = dict(row)
        value["interviewed"] = bool(value["interviewed"])
        return value

    def list_applications(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM applications ORDER BY updated_at DESC, application_id"
            ).fetchall()
        results = [dict(row) for row in rows]
        for result in results:
            result["interviewed"] = bool(result["interviewed"])
        return results

    def update_application(self, application_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
        if not changes:
            return self.get_application(application_id)
        allowed = {"applied_on", "status", "interviewed", "notes"}
        if set(changes) - allowed:
            raise ValueError("Unsupported application field")
        assignments = ", ".join(f"{column} = ?" for column in changes)
        values = [int(value) if column == "interviewed" else value for column, value in changes.items()]
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                f"UPDATE applications SET {assignments}, updated_at = ? WHERE application_id = ?",
                (*values, _now(), application_id),
            )
        return self.get_application(application_id) if cursor.rowcount else None

    def delete_application(self, application_id: str) -> bool:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "DELETE FROM applications WHERE application_id = ?", (application_id,)
            )
        return cursor.rowcount > 0
