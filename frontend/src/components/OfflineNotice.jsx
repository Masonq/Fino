import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

/**
 * Сообщение о проблемах со связью.
 *
 * Без него обрыв выглядит как «объявлений нет» — человек думает, что
 * сервис пустой, хотя дело в интернете. На мобильном связь рвётся часто,
 * поэтому важно говорить об этом прямо и давать кнопку повтора.
 */
export default function OfflineNotice({ onRetry }) {
  const { t } = useTranslation()
  const [offline, setOffline] = useState(!navigator.onLine)

  useEffect(() => {
    const goOffline = () => setOffline(true)
    const goOnline = () => {
      setOffline(false)
      onRetry?.()     // связь вернулась — сами перезагружаем
    }
    window.addEventListener('offline', goOffline)
    window.addEventListener('online', goOnline)
    return () => {
      window.removeEventListener('offline', goOffline)
      window.removeEventListener('online', goOnline)
    }
  }, [onRetry])

  if (!offline) return null

  return (
    <div className="offline-bar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M1 1l22 22M16.7 11.9a6 6 0 0 1 2.6 1.5M5 12.5a10 10 0 0 1 4-2.3M2 8.8a15 15 0 0 1 4.2-2.5M20.9 8.8a15 15 0 0 0-8.6-2.7M12 20h.01" />
      </svg>
      {t('net.offline')}
    </div>
  )
}

/**
 * Экран ошибки загрузки — когда запрос не прошёл, но связь вроде есть.
 * Отличается от пустого списка: здесь можно и нужно повторить.
 */
export function LoadError({ onRetry }) {
  const { t } = useTranslation()
  return (
    <div className="fav-empty">
      <div className="fav-empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
        </svg>
      </div>
      <p>{t('net.load_failed')}</p>
      <button className="fav-cta" onClick={onRetry}>{t('net.retry')}</button>
    </div>
  )
}
