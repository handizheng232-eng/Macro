import { queryAllByAttribute, within } from '@testing-library/react'

// These disclosures are explicitly aria-labelled <details>, not form labels.
// Match the same unique label without re-scanning every archived descendant or
// computing the accessible name of every other group. Keep role/name assertions.
export function replayDisclosure(name: string) {
  const matches = queryAllByAttribute('aria-label', document.body, name)
  expect(matches).toHaveLength(1)
  expect(matches[0].tagName).toBe('DETAILS')
  expect(matches[0]).toHaveRole('group')
  expect(matches[0]).toHaveAccessibleName(name)
  return matches[0]
}

// Label queries scan every descendant, including the full archived research DOM.
// Scope controls to their small, unique containers, but still validate the actual
// label/control association (not just an input id or a test-only selector).
export function replayCutoff() {
  const toolbars = document.querySelectorAll<HTMLElement>('.replay-toolbar')
  expect(toolbars).toHaveLength(1)
  return within(toolbars[0]).getByLabelText('按日期截止查看')
}

export function replaySearch() {
  const headers = document.querySelectorAll<HTMLElement>('.replay-library > header')
  expect(headers).toHaveLength(1)
  return within(headers[0]).getByLabelText('检索资料')
}
