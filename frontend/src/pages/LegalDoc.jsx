import { Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import PageHeader from '../components/PageHeader'
import { TERMS, PRIVACY, RULES } from '../data/legalContent'

const DOCS = { terms: TERMS, privacy: PRIVACY, rules: RULES }

/**
 * Условия использования и Политика конфиденциальности — один
 * компонент на оба документа: структура (заголовок, дата, разделы)
 * у них одинаковая, различается только содержимое.
 */
export default function LegalDoc({ doc }) {
  const { t, i18n } = useTranslation()
  const source = DOCS[doc]
  if (!source) return <Navigate to="/" replace />

  const content = source[i18n.language] || source.ru

  return (
    <div className="page legal-page page-narrow">
      <PageHeader title={content.title} />
      <p className="legal-updated">{content.updated}</p>
      {/* содержание — чипами: длинный документ, переход к нужному разделу одним нажатием */}
      <nav className="legal-toc">
        {content.sections.map((s, i) => (
          <a key={s.h} href={`#s${i}`} onClick={(e) => { e.preventDefault(); document.getElementById(`s${i}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }}>{s.h.replace(/^\d+\.\s*/, '')}</a>
        ))}
      </nav>
      {content.sections.map((s, i) => (
        <div className="legal-section" key={s.h} id={`s${i}`}>
          <h3>{s.h}</h3>
          {s.p.map((paragraph, i) => (
            <p key={i}>{paragraph}</p>
          ))}
        </div>
      ))}
    </div>
  )
}
