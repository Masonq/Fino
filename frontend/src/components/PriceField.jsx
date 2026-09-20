/**
 * Цена и валюта одним полем.
 *
 * Валюта — часть цены, а не отдельная настройка: «9000» без неё ничего
 * не значит. Поэтому переключатель стоит внутри поля, у правого края, а
 * не отдельным списком рядом (в размещении) и не отсутствует вовсе (в
 * редактировании валюту поменять было нельзя: ошибся при размещении —
 * удаляй объявление).
 *
 * Динары первыми: это валюта страны, евро — для жилья и машин.
 */
const CODES = ['RSD', 'EUR']

export default function PriceField({ label, price, currency, onPrice, onCurrency }) {
  return (
    <div className="post-field">
      <label htmlFor="price-input">{label}</label>
      <div className="price-field">
        <input
          id="price-input"
          type="number"
          inputMode="decimal"
          pattern="[0-9]*"
          min="0"
          value={price}
          onChange={(e) => onPrice(e.target.value)}
        />
        <div className="price-currency" role="radiogroup" aria-label={label}>
          {CODES.map((code) => (
            <button
              key={code}
              type="button"
              role="radio"
              aria-checked={currency === code}
              className={currency === code ? 'price-currency-btn on' : 'price-currency-btn'}
              onClick={() => onCurrency(code)}
            >
              {code}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
