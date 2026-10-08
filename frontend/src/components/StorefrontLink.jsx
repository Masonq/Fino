import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'

/** В объявлении: «Ещё N товаров продавца → Витрина» — главный вход в витрину и во второй просмотр. */
export default function StorefrontLink({ ownerId, listingId, initial }) {
  const { t } = useTranslation()
  // initial — витрина уже пришла вместе с объявлением: блок рисуется сразу, без второго запроса и без скачка
  const [sf, setSf] = useState(initial === undefined ? null : initial)
  useEffect(() => {
    if (!ownerId) return
    if (initial !== undefined) return
    api.sfByOwner(ownerId).then((r) => setSf(r.storefront)).catch(() => {})
  }, [ownerId])
  if (!sf) return null
  const more = Math.max(0, sf.count - (listingId ? 1 : 0))
  if (more < 1) return null
  return (
    <Link className="sf-link" to={`/s/${sf.slug}`}>
      <span className="sf-link-cover">{sf.cover_url ? <img src={sf.cover_url} alt="" /> : null}</span>
      <span className="sf-link-text">
        <span className="sf-link-title">{t('sf.more_from', { count: more })}</span>
        <span className="jr-muted">{t('sf.vitrina_of', { name: sf.name })}</span>
      </span>
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
    </Link>
  )
}
