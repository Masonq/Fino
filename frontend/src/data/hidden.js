/**
 * «Не интересно» и «Скрыть продавца» — долгим нажатием на карточку. Хранится на устройстве; карточки скрытых
 * вещей и продавцов не показываются нигде в лентах. Подписка — чтобы все карточки на экране исчезли сразу.
 */
const KEY = 'plonk_hidden'
let state = read()
const subs = new Set()
function read() {
  try { const v = JSON.parse(localStorage.getItem(KEY) || '{}'); return { l: v.l || [], s: v.s || [] } } catch { return { l: [], s: [] } }
}
function save() { try { localStorage.setItem(KEY, JSON.stringify(state)) } catch { /* не беда */ } subs.forEach((f) => f()) }
export const hidden = {
  get: () => state,
  subscribe: (f) => { subs.add(f); return () => subs.delete(f) },
  isHidden: (listing) => state.l.includes(String(listing.id)) || (listing.owner_id && state.s.includes(String(listing.owner_id))),
  hideListing: (id) => { state = { ...state, l: [...state.l.filter((x) => x !== String(id)), String(id)].slice(-500) }; save() },
  hideSeller: (id) => { state = { ...state, s: [...state.s.filter((x) => x !== String(id)), String(id)].slice(-200) }; save() },
  unhideListing: (id) => { state = { ...state, l: state.l.filter((x) => x !== String(id)) }; save() },
  unhideSeller: (id) => { state = { ...state, s: state.s.filter((x) => x !== String(id)) }; save() },
}
