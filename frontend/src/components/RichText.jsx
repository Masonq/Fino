/**
 * Текст объявления с простой разметкой.
 *
 * Продавцы пишут объявления в Telegram, а там **звёздочками** выделяют
 * главное: цену, площадь, что передаётся. У нас описание показывалось
 * как есть, и человек видел «**Цена:** €59 800» — звёздочки посреди
 * текста, будто ошибка.
 *
 * Поддерживаем только жирный: этого хватает, чтобы объявление читалось
 * так, как его писали. Никакого HTML из текста продавца не строим —
 * разбираем строку сами и выводим обычные узлы, поэтому вставить со
 * страницы чужую разметку нельзя.
 */
const BOLD = /\*\*(.+?)\*\*|__(.+?)__/g

export default function RichText({ text, className = '' }) {
  const source = text || ''
  const nodes = []
  let last = 0
  let match

  BOLD.lastIndex = 0
  while ((match = BOLD.exec(source)) !== null) {
    if (match.index > last) nodes.push(source.slice(last, match.index))
    nodes.push(<b key={match.index}>{match[1] ?? match[2]}</b>)
    last = match.index + match[0].length
  }
  if (last < source.length) nodes.push(source.slice(last))

  return <div className={className}>{nodes}</div>
}
