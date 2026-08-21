import { useTranslation } from 'react-i18next'

export default function ComingSoon({ title }) {
  const { t } = useTranslation()
  return (
    <div className="post-ad-page">
      <h2>{title}</h2>
      <p className="empty-hint">{t('misc.coming_soon')}</p>
    </div>
  )
}
