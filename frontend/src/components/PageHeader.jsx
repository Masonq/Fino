import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

/**
 * Шапка внутренней страницы. Кнопка «назад» нужна везде, кроме экранов
 * нижнего меню — там уходить некуда, для них back={false}.
 */
export default function PageHeader({ title, count, back = true, children }) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <div className="page-header">
      {back && (
        <button
          className="page-back"
          onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/'))}
          aria-label={t('actions.back')}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round">
            <path d="m15 18-6-6 6-6" />
          </svg>
        </button>
      )}
      <h2>
        {title}
        {count > 0 && <span className="fav-count">{count}</span>}
      </h2>
      {children}
    </div>
  )
}
