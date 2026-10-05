import { useTranslation } from 'react-i18next'

/**
 * Галочка у имени. official — команда PLONK (администратор или модератор): зелёный «розеточный» значок,
 * как у официальных аккаунтов; verified — личность или компания подтверждены: простая галочка в круге.
 */
export default function VerifiedMark({ official, verified, size = 18, label = false }) {
  const { t } = useTranslation()
  if (!official && !verified) return null
  const title = official ? t('verify.official') : t('verify.verified')
  return (
    <span className={`vmark${official ? ' is-official' : ''}`} title={title} aria-label={title} role="img">
      {official ? (
        <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
          <path fill="var(--primary)" d="M12 1.6l2.4 1.8 3-.1.9 2.9 2.5 1.7-.9 2.9.9 2.9-2.5 1.7-.9 2.9-3-.1L12 22.4l-2.4-1.8-3 .1-.9-2.9-2.5-1.7.9-2.9-.9-2.9 2.5-1.7.9-2.9 3 .1z" />
          <path d="m8 12.2 2.7 2.7L16.2 9.4" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      ) : (
        <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10" fill="var(--primary)" />
          <path d="m7.8 12.3 2.8 2.8 5.6-5.8" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
      {label && <span className="vmark-label">{title}</span>}
    </span>
  )
}
