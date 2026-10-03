import { router } from 'expo-router'
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { DICT } from './i18n-dict'
import { prefs } from './prefs'

/**
 * Язык приложения: RU / EN / SR (сербский — латиницей, как на сайте). Тексты в коде пишутся по-русски и
 * оборачиваются в tr('…'): русский — исходник, для en/sr берётся перевод из словаря (i18n-dict.ts); нет
 * перевода — показываем русский, а не пустоту. Подстановки — {n}: tr('Отправить снова через {n} с', { n: 5 }).
 * Выбор запоминается на телефоне; при смене язык меняется сразу во всём приложении (экраны перерисовываются).
 */
export type Lang = 'ru' | 'en' | 'sr'
export const LANGS: { key: Lang; label: string }[] = [{ key: 'ru', label: 'RU' }, { key: 'en', label: 'EN' }, { key: 'sr', label: 'SR' }]

let current: Lang = 'ru'
export const getLang = () => current

export function tr(text: string, params?: Record<string, string | number>): string {
  const row = DICT[text]
  let out = current === 'ru' || !row ? text : (row[current] || text)
  if (params) for (const [k, v] of Object.entries(params)) out = out.split(`{${k}}`).join(String(v))
  return out
}

type Ctx = { lang: Lang; setLang: (l: Lang) => void; ready: boolean }
const LangCtx = createContext<Ctx>({ lang: 'ru', setLang: () => {}, ready: false })

export function LangProvider({ children }: { children: (lang: Lang) => ReactNode }) {
  const [lang, setLangState] = useState<Lang>('ru')
  const [ready, setReady] = useState(false)
  useEffect(() => {
    prefs.get('plonk_lang').then((v) => {
      if (v === 'en' || v === 'sr' || v === 'ru') { current = v; setLangState(v) }
      setReady(true)
    })
  }, [])
  const setLang = useCallback((l: Lang) => {
    current = l
    setLangState(l)
    prefs.set('plonk_lang', l)
    // экраны перестраиваются с новым языком — возвращаем человека туда, где он менял язык
    setTimeout(() => router.replace('/profile'), 0)
  }, [])
  const value = useMemo(() => ({ lang, setLang, ready }), [lang, setLang, ready])
  return <LangCtx.Provider value={value}>{children(lang)}</LangCtx.Provider>
}

export const useLang = () => useContext(LangCtx)
