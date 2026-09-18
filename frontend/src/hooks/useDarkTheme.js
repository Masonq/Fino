import { useEffect, useState } from 'react'

// Тёмная ли сейчас тема. Смотрим на тот же data-theme, который ставит
// скрипт в index.html и переключатель в профиле, и следим за его
// изменением: человек может переключить тему на любом экране, и
// картинки должны поменяться сразу, без перезагрузки.
export default function useDarkTheme() {
  const [dark, setDark] = useState(
    () => document.documentElement.getAttribute('data-theme') === 'dark',
  )
  useEffect(() => {
    const el = document.documentElement
    const observer = new MutationObserver(() => {
      setDark(el.getAttribute('data-theme') === 'dark')
    })
    observer.observe(el, { attributes: true, attributeFilter: ['data-theme'] })
    return () => observer.disconnect()
  }, [])
  return dark
}
