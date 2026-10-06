import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

/**
 * Шапка внутренней страницы. Кнопка «назад» нужна везде, кроме экранов
 * нижнего меню — там уходить некуда, для них back={false}.
 *
 * PLONK 2.0: с kicker — шапка как на главной: сверху ряд капсул (назад и действия), ниже маленькая строка-подводка
 * и крупный заголовок («Добрый вечер» / «Что ищем сегодня?» → «4 вещи · 1 подешевела» / «Избранное»).
 */
export default function PageHeader({ title, count, back = true, kicker, subtitle, compact = false, children }) {
  if (kicker === undefined && subtitle) kicker = subtitle
  const { t } = useTranslation()
  const navigate = useNavigate()
  const backBtn = back && (
    <button
      className="page-back"
      onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/'))}
      aria-label={t('actions.back')}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round">
        <path d="m15 18-6-6 6-6" />
      </svg>
    </button>
  )

  // PLONK 2.0: шапка-приветствие на всех страницах (как на главной); compact — старая строка для узких мест
  if (!compact) {
    // «назад», текст и действия — в одну строку: шапка вдвое ниже, чем ряд капсул над заголовком (было 137 px)
    return (
      <div className={`page-hero${back ? ' has-back' : ''}`}>
        {backBtn}
        <div className="ph-text">
          {kicker && <span className="ph-kicker">{kicker}</span>}
          <h1 className={`ph-title${String(title || '').length > (children ? 12 : 16) ? ' is-long' : ''}`}><span className="page-title-text">{title}</span>{count > 0 && <span className="fav-count">{count}</span>}</h1>
        </div>
        {children && <div className="ph-actions">{children}</div>}
      </div>
    )
  }

  return (
    <div className="page-header">
      {backBtn}
      <h2>
        {/* Заголовком бывает имя человека, а его пишет он сам: строка
            значков во всю ширину уносила за собой весь экран. */}
        <span className="page-title-text">{title}</span>
        {count > 0 && <span className="fav-count">{count}</span>}
      </h2>
      {children}
    </div>
  )
}
