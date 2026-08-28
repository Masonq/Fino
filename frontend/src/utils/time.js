/**
 * «Сколько прошло» для дат с сервера.
 *
 * Сервер отдаёт время в UTC без пометки зоны, поэтому дописываем Z —
 * без этого браузер читал бы его как местное и промахивался на пару часов.
 */
export function timeAgo(iso, t, lang) {
  if (!iso) return ''
  const diff = (Date.now() - new Date(iso + 'Z').getTime()) / 1000
  if (diff < 60) return t('chats.just_now')
  if (diff < 3600) return `${Math.floor(diff / 60)} ${t('chats.min')}`
  if (diff < 86400) return `${Math.floor(diff / 3600)} ${t('chats.hour')}`
  const days = Math.floor(diff / 86400)
  if (days < 7) return `${days} ${t('chats.day')}`
  return new Date(iso + 'Z').toLocaleDateString(lang)
}

/**
 * Дата отзыва: месяц и год.
 *
 * Точный день ничего не решает, а вот свежий отзыв и трёхлетний — вес
 * у них разный, и без даты их было не отличить.
 */
export function monthYear(iso, lang) {
  if (!iso) return ''
  return new Date(iso + 'Z').toLocaleDateString(lang, { year: 'numeric', month: 'long' })
}

/**
 * «сегодня», «вчера», «3 дня назад» — как у Авито, вместо голой даты,
 * которую пришлось бы читать дольше, чем она того стоит. Раньше жила
 * только внутри ListingCard.jsx — теперь общая, использует её и
 * карточка объявления в ленте, и сама страница объявления.
 */
export function relativeDate(iso, t) {
  if (!iso) return ''
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
  if (days <= 0) return t('misc.date_today')
  if (days === 1) return t('misc.date_yesterday')
  if (days < 7) return t('misc.date_days_ago', { count: days })
  return new Date(iso).toLocaleDateString()
}
