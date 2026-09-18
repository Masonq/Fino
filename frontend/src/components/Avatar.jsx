import { useState } from 'react'

/**
 * Кружок с фотографией человека или его буквой.
 *
 * Картинка бывает недоступна: аватар из Telegram живёт на их серверах и
 * иногда перестаёт отдаваться, а ссылка в базе остаётся. Браузер в таком
 * случае рисует значок битой картинки — именно он и появился в карточке
 * человека вместо лица. Ловим ошибку загрузки и показываем букву, как
 * если бы фотографии не было вовсе.
 */
export default function Avatar({ src, name, className = '' }) {
  const [broken, setBroken] = useState(false)
  const letter = (name || '?').trim().charAt(0).toUpperCase() || '?'

  return (
    <span className={className}>
      {src && !broken
        ? <img src={src} alt="" onError={() => setBroken(true)} />
        : letter}
    </span>
  )
}
