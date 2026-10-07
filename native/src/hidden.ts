/**
 * «Не интересно» и «Скрыть продавца» (долгое нажатие на карточку) — как на сайте: хранится на устройстве,
 * карточки пропадают из лент сразу. useHidden() перерисовывает экран, когда список меняется.
 */
import { useSyncExternalStore } from 'react'
import { prefs } from './prefs'

type Hidden = { l: string[]; s: string[] }
let state: Hidden = { l: [], s: [] }
const subs = new Set<() => void>()
prefs.get('plonk_hidden').then((v) => { try { if (v) { state = JSON.parse(v); subs.forEach((f) => f()) } } catch { /* пусто */ } })

function save(next: Hidden) {
  state = next
  prefs.set('plonk_hidden', JSON.stringify(next))
  subs.forEach((f) => f())
}
export const hideListing = (id: string) => save({ ...state, l: [...new Set([...state.l, id])].slice(-500) })
export const unhideListing = (id: string) => save({ ...state, l: state.l.filter((x) => x !== id) })
export const hideSeller = (id: string) => save({ ...state, s: [...new Set([...state.s, id])].slice(-200) })
export const unhideSeller = (id: string) => save({ ...state, s: state.s.filter((x) => x !== id) })
export const isHidden = (it: { id: string; owner_id?: string | null }) => state.l.includes(it.id) || (!!it.owner_id && state.s.includes(it.owner_id))

export function useHidden() {
  return useSyncExternalStore((f) => { subs.add(f); return () => { subs.delete(f) } }, () => state)
}
