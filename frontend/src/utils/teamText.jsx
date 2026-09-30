// Письмо от команды — единственное, что мы пишем сами, поэтому только
// в нём разбираем разметку: заголовок, жирный, пункты списка, ссылки.
// В обычной переписке всё остаётся текстом — кликабельная чужая ссылка
// в чате объявлений это подарок мошеннику.
import { Link } from 'react-router-dom'

function inlineParts(line, keyPrefix) {
  // Сначала ссылки, внутри остального — **жирный**.
  return String(line).split(/(https?:\/\/\S+)/g).flatMap((chunk, i) => {
    if (/^https?:\/\//.test(chunk)) {
      return [<a key={`${keyPrefix}-l${i}`} href={chunk} target="_blank" rel="noopener noreferrer">{chunk}</a>]
    }
    return chunk.split(/\*\*(.+?)\*\*/g).map((part, j) => (
      j % 2 ? <b key={`${keyPrefix}-b${i}-${j}`}>{part}</b> : part
    ))
  })
}

export default function teamText(text) {
  const lines = String(text || '').split('\n')
  const blocks = []
  let list = null

  const flushList = () => {
    if (list) { blocks.push(<ul key={`u${blocks.length}`} className="team-list">{list}</ul>); list = null }
  }

  lines.forEach((raw, i) => {
    const line = raw.trimEnd()
    if (/^[-•*]\s+/.test(line)) {
      list = list || []
      list.push(<li key={`i${i}`}>{inlineParts(line.replace(/^[-•*]\s+/, ''), i)}</li>)
      return
    }
    flushList()
    // Кнопка: [[Подпись|/путь]]. Только внутренние пути — письмо пишем мы, но
    // кнопка не должна уметь вести за пределы сайта.
    const button = line.match(/^\[\[(.+?)\|(\/[A-Za-z0-9_\-/]*)\]\]$/)
    if (button) {
      blocks.push(<Link key={`b${i}`} to={button[2]} className="team-btn">{button[1]}</Link>)
      return
    }
    if (!line) return                      // пустая строка — это зазор между блоками, он от отступов
    if (/^#{1,3}\s+/.test(line)) {
      blocks.push(<div key={`h${i}`} className="team-head">{inlineParts(line.replace(/^#{1,3}\s+/, ''), i)}</div>)
      return
    }
    blocks.push(<p key={`p${i}`} className="team-p">{inlineParts(line, i)}</p>)
  })
  flushList()
  return <div className="team-letter">{blocks}</div>
}

// То же письмо без разметки — для превью в списке и на острове, где
// «# Привет!» и «**+**» смотрятся мусором.
export function plainTeamText(text) {
  return String(text || '')
    .replace(/^#{1,3}\s+/gm, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/^[-•*]\s+/gm, '')
    .replace(/\[\[.+?\|\/[^\]]*\]\]/g, '')          // кнопка в превью не нужна
    .replace(/\s+/g, ' ')
    .trim()
}
