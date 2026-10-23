import { isInaccessible, within } from '@testing-library/react'

// A workbench is explicitly aria-labelled. Avoid computing names for thousands
// of unrelated research <article>s; still reject duplicates, wrong roles/names,
// and inaccessible matches just as the original getByRole query did.
export function queryReplayWorkbench(name: string) {
  const matches = document.querySelectorAll<HTMLElement>(`[aria-label=${JSON.stringify(name)}]`)
  expect(matches.length).toBeLessThanOrEqual(1)
  if (!matches.length) return null
  expect(matches[0]).toHaveRole('article')
  expect(matches[0]).toHaveAccessibleName(name)
  expect(isInaccessible(matches[0])).toBe(false)
  return matches[0]
}

export function replayWorkbench(name: string) {
  const workbench = queryReplayWorkbench(name)
  expect(workbench).not.toBeNull()
  return workbench!
}

function replayWithin(selector: string) {
  const matches = document.querySelectorAll<HTMLElement>(selector)
  expect(matches).toHaveLength(1)
  return within(matches[0])
}

export const replayToolbar = () => replayWithin('.replay-toolbar')
export const replayHeading = () => replayWithin('.replay-heading')

// These disclosures are explicitly aria-labelled <details>, not form labels.
// Match the same unique label without re-scanning every archived descendant or
// computing the accessible name of every other group. Keep role/name assertions.
export function replayDisclosure(name: string) {
  const matches = document.querySelectorAll<HTMLElement>(`[aria-label=${JSON.stringify(name)}]`)
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
