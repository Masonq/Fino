import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

// Раньше несуществующий адрес (битая ссылка, опечатка, старая
// закладка) просто открывал пустой экран — ни ошибки, ни объяснения,
// ни выхода. Ловим это здесь: маршрут стоит последним, после /:city/
// /:category/:slug, и подхватывает всё, что не подошло ни под одно
// правило выше.
export default function NotFound() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <div className="fav-page no-header">
      <div className="fav-empty">
        <div className="fav-empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
          </svg>
        </div>
        <p>{t('misc.not_found')}</p>
        <button className="fav-cta" onClick={() => navigate('/')}>
          {t('actions.to_home')}
        </button>
      </div>
    </div>
  )
}
