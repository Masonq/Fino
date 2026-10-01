/** Пять звёзд по среднему рейтингу (округление до целой). Только картинка: число и «N отзывов» пишутся рядом текстом. */
export default function Stars({ value }) {
  const full = Math.round(Number(value) || 0)
  return (
    <span className="stars" aria-hidden="true">
      {[1, 2, 3, 4, 5].map((i) => (
        <svg key={i} viewBox="0 0 24 24" className={i <= full ? 'on' : ''}>
          <path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z" />
        </svg>
      ))}
    </span>
  )
}
