import { useTranslation } from 'react-i18next'

export default function PostAd() {
  const { t } = useTranslation()
  return (
    <div className="post-ad-page">
      <h2>{t('listing.post_new')}</h2>
      <p className="empty-hint">
        Динамическая форма (категория → атрибуты по схеме → фото → цена → описание) — следующая итерация
      </p>
    </div>
  )
}
