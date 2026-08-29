import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

/**
 * Мягкое напоминание указать телефон в профиле — не модалка,
 * не обязательное поле, просто заметная строка. Без номера теряет
 * смысл вся функция звонка (см. ChatScreen.jsx): нечего раскрывать
 * покупателю, кнопка «Позвонить» у него просто не появляется.
 *
 * Закрывается на текущую сессию через sessionStorage — не насовсем
 * (иначе человек, который отложил дело один раз, никогда больше не
 * увидит подсказку), но и не при каждом переходе между страницами в
 * одной сессии — вернётся сама при следующем настоящем входе.
 */
export default function PhoneReminder({ user }) {
  const { t } = useTranslation()
  const [dismissed, setDismissed] = useState(() => sessionStorage.getItem('phone_reminder_dismissed') === '1')

  if (!user || user.phone || dismissed) return null

  const close = () => {
    sessionStorage.setItem('phone_reminder_dismissed', '1')
    setDismissed(true)
  }

  return (
    <div className="phone-reminder">
      <span className="phone-reminder-text">{t('home.phone_reminder')}</span>
      <Link to="/profile/edit" className="phone-reminder-link">{t('home.phone_reminder_cta')}</Link>
      <button className="phone-reminder-close" onClick={close} aria-label={t('actions.close')}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>
      </button>
    </div>
  )
}
