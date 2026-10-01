import assert from 'node:assert/strict'
import test from 'node:test'
import { buildMatchSummary } from '../src/matchSummary.js'

test('summary separates career direction from this-cycle eligibility and limits preview length', () => {
  const result = buildMatchSummary({
    current_application_eligibility: { status: 'current_cycle_conflict', conflicting_conditions: ['届别不符'] },
    user_facing_explanation: { highly_aligned_points: ['真实需求对接'.repeat(40)] },
    gap_summary: { evidence_gaps: ['飞书工具缺少证据'] },
  }, { career_direction_label: 'worth_exploring', current_action_label: 'save_job_archetype', preference_coverage: 0.3, career_direction_summary: null })
  assert.equal(result.direction, '值得探索')
  assert.equal(result.eligibility, '本批次条件不符')
  assert.equal(result.hasScore, false)
  assert.equal(result.preferencePercent, 30)
  assert.ok(result.support.length <= 69)
  assert.match(result.nextStep, /新批次/)
})

test('unknown eligibility is not presented as an application pass', () => {
  const result = buildMatchSummary({}, {})
  assert.equal(result.eligibility, '条件待核实')
  assert.equal(result.hasScore, false)
})
