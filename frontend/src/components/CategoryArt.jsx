import { useState } from 'react'
import { CATEGORY_ICONS, FALLBACK_ICON } from './CategoryIcons'

/**
 * Картинка категории. Если файла нет или он не загрузился — показываем
 * контурную иконку: пустое место в плитке выглядит как поломка, а иконка
 * читается нормально.
 *
 * Все картинки приведены к общему квадрату 512×512 с равными полями, так
 * что подгонять масштаб и сдвиг под каждую категорию не нужно.
 */
export default function CategoryArt({ slug }) {
  const [failed, setFailed] = useState(false)

  if (failed || !slug) {
    return CATEGORY_ICONS[slug] || FALLBACK_ICON
  }

  return (
    <img
      className="cat-art"
      src={`/cat/${slug}.png`}
      alt=""
      loading="lazy"
      onError={() => setFailed(true)}
    />
  )
}
