/**
 * Цена в виде, привычном для языка интерфейса.
 *
 * Разделитель тысяч у языков разный: в сербском это точка, и «1.800»
 * в русском интерфейсе читается как «1,8». Поэтому берём язык интерфейса,
 * а не язык объявления и не жёстко заданную локаль.
 *
 * Между числом и знаком — узкий пробел: обычный в моноширинном шрифте
 * оставлял заметный разрыв.
 */
export function formatPrice(value, currency, lang = 'ru') {
  if (value == null || value === '') return null
  const num = Number(value).toLocaleString(lang)
  return `${num}\u202F${currency === 'EUR' ? '€' : currency}`
}

/**
 * Сумма на балансе: целые без хвоста («1 500»), с копейками всегда двумя знаками («12 500,50», а не «12 500,5»).
 * Язык форматирования берём тот же, что для дат: сербский — латиницей и с точкой в тысячах.
 */
export function formatAmount(value, lang = 'ru') {
  const num = Number(value || 0)
  const locale = { ru: 'ru-RU', en: 'en-GB', sr: 'sr-Latn-RS' }[lang] || lang
  return Number.isInteger(num)
    ? num.toLocaleString(locale)
    : num.toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

