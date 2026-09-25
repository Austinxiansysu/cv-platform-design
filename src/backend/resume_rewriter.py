"""Optional natural wording for evidence-bound resume suggestions."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from src.backend.job_parser import ResponseClient
from src.backend.model_gateway import (
    ModelFailure,
    provider_settings,
    response_format,
    responses_client,
)
from src.backend.privacy import redact_contact_details
from src.matching.resume_advice import build_resume_advice


SCHEMA_PATH = Path(__file__).with_name("resume_rewrite.schema.json")
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?%?")
TOOL_WORDS = (
    "SQL", "Python", "Pandas", "NumPy", "Matplotlib", "Excel", "Power BI",
    "Tableau", "SPSS", "Figma", "飞书", "Claude Code", "Codex", "AI工具",
    "大模型", "工作流",
)
HIGH_CLAIM_WORDS = (
    "主导", "独立负责", "负责", "领导", "管理团队", "客户调研", "客户访谈",
    "培训", "上线", "搭建", "开发", "策划", "提升", "增长", "转化率",
    "降低", "节省", "需求分析", "产品设计", "数据建模", "产品经理", "FDE",
)

REWRITE_INSTRUCTIONS = """你是简历表达编辑，不是经历创作者。只输出 JSON。
每个候选经历只给一句自然、简洁的中文简历表达。可以调整语序和连接词，但不得添加输入中未出现的行动、工具、角色、日期、数字、结果、客户或技能。岗位关注点只用于选择强调角度，不能变成“我做过”的事实。
used_source_facts 必须逐字从该经历给出的 title、source_actions、source_deliverables 中选择。若不能安全改写，suggested_sentence 返回空字符串。不要使用“主导”“负责”“提升”等更强动词，除非原始事实本身明确写了。"""


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def _supported_sentence(sentence: str, suggestion: dict[str, Any]) -> str | None:
    facts = [suggestion["title"], *suggestion["source_actions"], *suggestion["source_deliverables"]]
    source = _compact(" ".join(facts))
    candidate = _compact(sentence)
    if not sentence.strip() or len(sentence) > 220 or "\n" in sentence:
        return "句子为空、过长或包含换行"
    for number in NUMBER_RE.findall(sentence):
        if number not in NUMBER_RE.findall(" ".join(facts)):
            return f"出现原始事实没有的数字 {number}"
    for phrase in suggestion["prohibited_claims"]:
        if phrase and _compact(phrase) in candidate:
            return f"包含已禁止的经历表述：{phrase}"
    for phrase in TOOL_WORDS + HIGH_CLAIM_WORDS:
        if _compact(phrase) in candidate and _compact(phrase) not in source:
            return f"出现原始事实没有的工具或强主张：{phrase}"
    return None


def rewrite_resume_advice(
    profile: dict[str, Any],
    job: dict[str, Any],
    alignment: dict[str, Any],
    responses: ResponseClient | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Return review-only wording; unsafe model sentences fall back to exact facts."""
    base = build_resume_advice(profile, job, alignment)
    if not base["suggestions"]:
        return {"match_id": base["match_id"], "rewrites": [], "needs_more_information": base["needs_more_information"], "saved": False}

    provider, settings = provider_settings()
    if responses is None:
        responses = responses_client(settings, api_key)
    request_facts = [{
        "experience_id": item["experience_id"],
        "title": item["title"],
        "source_actions": item["source_actions"],
        "source_deliverables": item["source_deliverables"],
        "job_focus": item["job_focus"],
    } for item in base["suggestions"]]
    try:
        options = {
            "model": os.environ.get("CV_ASSISTANT_MODEL", str(settings["model"])),
            "instructions": REWRITE_INSTRUCTIONS,
            "input": json.dumps(redact_contact_details({
                "job_title": job["job_meta"]["original_title"],
                "job_function": job["function_classification"]["primary_function"],
                "experiences": request_facts,
            }), ensure_ascii=False),
            "text": {"format": response_format(SCHEMA_PATH, provider)},
            "max_output_tokens": 3000,
            "store": False,
        }
        if provider == "deepseek":
            options["reasoning"] = {"effort": "low"}
        response = responses.create(**options)
    except Exception as error:
        raise ModelFailure("Resume rewrite request failed") from error
    if response.status != "completed" or not response.output_text:
        raise ModelFailure("Resume rewrite response was incomplete or empty")
    try:
        model_output = json.loads(response.output_text)
    except json.JSONDecodeError as error:
        raise ModelFailure("Resume rewrite response was not valid JSON") from error
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["schema"]
    errors = list(Draft202012Validator(schema).iter_errors(model_output))
    if errors:
        raise ModelFailure("Resume rewrite response did not match its format")

    offered: dict[str, dict[str, Any]] = {}
    for item in model_output["rewrites"]:
        if item["experience_id"] in offered:
            raise ModelFailure("Resume rewrite returned a duplicate experience")
        offered[item["experience_id"]] = item
    eligible = {item["experience_id"] for item in base["suggestions"]}
    if set(offered) - eligible:
        raise ModelFailure("Resume rewrite referenced an unknown experience")

    rewrites = []
    for source_item in base["suggestions"]:
        item = offered.get(source_item["experience_id"])
        valid_facts = {
            source_item["title"], *source_item["source_actions"],
            *source_item["source_deliverables"],
        }
        rejection = None
        if item is None:
            rejection = "模型未返回这段经历"
        elif not item["used_source_facts"] or not set(item["used_source_facts"]).issubset(valid_facts):
            rejection = "来源事实与个人画像不一致"
        else:
            rejection = _supported_sentence(item["suggested_sentence"], source_item)
        rewrites.append({
            "experience_id": source_item["experience_id"],
            "title": source_item["title"],
            "original_facts": {
                "actions": source_item["source_actions"],
                "deliverables": source_item["source_deliverables"],
                "evidence_ids": source_item["source_evidence_ids"],
            },
            "job_focus": source_item["job_focus"],
            "suggested_sentence": source_item["suggested_sentence"] if rejection else item["suggested_sentence"],
            "model_sentence_accepted": rejection is None,
            "rejection_reason": rejection,
            "prohibited_claims": source_item["prohibited_claims"],
            "requires_user_review": True,
        })
    return {
        "match_id": base["match_id"],
        "rewrites": rewrites,
        "needs_more_information": base["needs_more_information"],
        "saved": False,
    }
