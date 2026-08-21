import { useTranslation } from 'react-i18next'

export default function Search() {
  const { t } = useTranslation()
  return (
    <div className="search-page">
      <input className="search-input" placeholder={t('search.placeholder')} />
      <p className="empty-hint">Список объявлений и фильтры — следующая итерация</p>
    </div>
  )
}
