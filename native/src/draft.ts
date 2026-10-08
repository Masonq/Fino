/**
 * Черновик объявления — как на сайте: недописанное объявление сохраняется на телефоне, и при следующем открытии
 * «Разместить» можно продолжить с того же места. Храним в файле (а не в SecureStore — там лимит ~2 КБ, а описание
 * бывает длиннее); в веб-превью — в хранилище браузера.
 */
import { Platform } from 'react-native'
import * as FS from 'expo-file-system/legacy'

const NAME = 'post-draft.json'
const KEY = 'plonk_post_draft'
const path = () => `${FS.documentDirectory ?? ''}${NAME}`

export type Draft = {
  savedAt: number
  step: number
  cat?: { slug: string; id: string; name: unknown; path: string } | null
  title: string; desc: string; price: string; currency: 'EUR' | 'RSD'; negotiable: boolean
  city: string | null; point: { lat: number | null; lng: number | null }; hideAddr: boolean
  attrs: Record<string, unknown>
  shots: { key: string; uri: string; mime: string; uploaded?: unknown }[]
}

export async function saveDraft(d: Draft): Promise<void> {
  const s = JSON.stringify(d)
  try {
    if (Platform.OS === 'web') globalThis.localStorage?.setItem(KEY, s)
    else await FS.writeAsStringAsync(path(), s)
  } catch { /* не беда — черновик просто не сохранится */ }
}

export async function loadDraft(): Promise<Draft | null> {
  try {
    const s = Platform.OS === 'web' ? globalThis.localStorage?.getItem(KEY) ?? null : await FS.readAsStringAsync(path())
    if (!s) return null
    const d = JSON.parse(s) as Draft
    // старше двух недель — не предлагаем, фото на сервере могли уже удалить
    if (!d.savedAt || Date.now() - d.savedAt > 14 * 864e5) return null
    return d
  } catch { return null }
}

export async function clearDraft(): Promise<void> {
  try {
    if (Platform.OS === 'web') globalThis.localStorage?.removeItem(KEY)
    else await FS.deleteAsync(path(), { idempotent: true })
  } catch { /* нечего удалять */ }
}

/** Есть ли в черновике что-то, ради чего стоит предлагать «Продолжить». */
export const draftHasContent = (d: Draft | null) => !!d && (!!d.cat || !!d.title.trim() || !!d.desc.trim() || d.shots.length > 0)
