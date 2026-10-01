const directionLabels = { priority_direction: '优先探索', worth_exploring: '值得探索', low_priority_direction: '暂不优先', needs_more_experience: '先体验再判断' }
const eligibilityLabels = { pass: '已知条件符合', pending: '还需核实条件', current_cycle_conflict: '本批次条件不符', structural_conflict: '当前安排不适合' }
const nextSteps = {
  save_job_archetype: '收藏这类岗位，关注与你届别和时间相符的新批次。',
  not_recommended_now: '先核对与个人安排冲突的条件，不急着申请。',
  gather_information: '先问清最关键的申请条件，再决定是否投递。',
  explore_before_applying: '先体验一项核心任务，再决定是否申请。',
  priority_apply: '核实招聘仍开放后，准备基于真实经历的申请。',
  stretch_apply: '核实条件后可以尝试申请，同时补足关键证据。',
  worth_applying: '核实条件后可以考虑申请。',
  low_priority: '先比较其他岗位，把这条作为备选。',
}
function brief(value, limit = 68) {
  const plain = value.replace(/（[^）]*个人画像[^）]*）/g, '').replace(/\(must\)/g, '').replace(/用户为/g, '你是').replace(/evidence gap/gi, '证据缺口')
  return plain.length > limit ? `${plain.slice(0, limit)}…` : plain
}
export function buildMatchSummary(alignment, score) {
  const text = alignment.user_facing_explanation || {}
  const eligibility = alignment.current_application_eligibility || {}
  const support = text.highly_aligned_points?.[0]
  const gap = alignment.gap_summary?.evidence_gaps?.[0] || text.main_risks?.[0]
  return {
    direction: directionLabels[score.career_direction_label] || '需要更多证据',
    eligibility: eligibilityLabels[eligibility.status] || '条件待核实',
    condition: brief(eligibility.conflicting_conditions?.[0] || eligibility.unknown_conditions?.[0] || '仍需核验招聘状态及完整条件。'),
    nextStep: nextSteps[score.current_action_label] || '先核对完整解释与证据，再作决定。',
    support: support ? brief(support) : '目前还没有明确支持点。',
    gap: gap ? brief(gap) : '请展开查看仍需核实的信息。',
    hasScore: score.career_direction_summary != null,
    preferencePercent: Math.round((score.preference_coverage || 0) * 100),
  }
}
