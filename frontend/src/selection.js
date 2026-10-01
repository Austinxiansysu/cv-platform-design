// Result links contain only local record IDs, never profile contents or keys.
export function resolveSelection(search, remembered = {}) {
  const query = new URLSearchParams(search)
  const selection = { ...remembered }
  for (const field of ['profileVersion', 'jobId', 'matchId']) {
    const value = query.get(field)
    if (value) selection[field] = value
  }
  return selection
}
