import assert from 'node:assert/strict'
import test from 'node:test'
import { resolveSelection } from '../src/selection.js'

test('local result links select explicit record IDs without accepting other fields', () => {
  assert.deepEqual(resolveSelection('?profileVersion=p2&jobId=j2&matchId=m2&api_key=ignored', { profileVersion: 'p1' }), {
    profileVersion: 'p2', jobId: 'j2', matchId: 'm2',
  })
})

test('opening without a result link preserves the existing local selection', () => {
  assert.deepEqual(resolveSelection('', { profileVersion: 'p1' }), { profileVersion: 'p1' })
})
