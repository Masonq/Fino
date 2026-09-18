import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { THEMES, applyTheme, storedTheme, watchSystemTheme } from '../utils/theme'

// Светлая / тёмная / как в системе.
//
// «Как в системе» стоит первым и выбрано по умолчанию: телефон уже
// знает, светло вокруг или темно, и вечером сам переключается. Явный
// выбор нужен тем, у кого система держит одну тему, а сайт хочется в
// другой.
const ICONS = {
  auto: <><circle cx="12" cy="12" r="9" /><path d="M12 3v18" /><path d="M12 3a9 9 0 0 1 0 18" fill="currentColor" stroke="none" /></>,
  light: <><circle cx="12" cy="12" r="4.2" /><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.2 5.2l1.4 1.4M17.4 17.4l1.4 1.4M18.8 5.2l-1.4 1.4M6.6 17.4l-1.4 1.4" /></>,
  dark: <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" />,
}

export default function ThemeSwitcher() {
  const { t } = useTranslation()
  const [theme, setTheme] = useState(storedTheme)

  // Пока выбрано «как в системе» — следим за системной настройкой.
  useEffect(() => watchSystemTheme(), [])

  const pick = (next) => {
    setTheme(next)
    applyTheme(next)
  }

  return (
    <div className="theme-switch">
      {THEMES.map((key) => (
        <button
          key={key}
          className={theme === key ? 'theme-btn on' : 'theme-btn'}
          onClick={() => pick(key)}
          aria-label={t(`profile.theme_${key}`)}
          aria-pressed={theme === key}
          title={t(`profile.theme_${key}`)}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            {ICONS[key]}
          </svg>
        </button>
      ))}
    </div>
  )
}
