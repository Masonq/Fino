import { useEffect, useState } from 'react'
// Подключение именем, а не по умолчанию: в этой версии библиотека
// отдаёт набор, и «import Lottie from» ломал сборку.
import { Lottie } from 'lottie-react'

/**
 * Анимация из файла — на важных мгновениях.
 *
 * Грузится по требованию, а не вместе с сайтом: сам файл анимации
 * весит немало, и тянуть его на каждую страницу ради одного
 * поздравления неразумно.
 *
 * Пока файл едет, ничего не показываем: пустота лучше, чем мигающая
 * заглушка на полсекунды.
 *
 * Кому движение мешает — не показываем вовсе, как и прочие наши
 * анимации.
 */
export default function LottieOnce({ name, size = 160, onDone }) {
  const [data, setData] = useState(null)

  const reduced = typeof window !== 'undefined'
    && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

  useEffect(() => {
    if (reduced) {
      onDone?.()
      return
    }
    let alive = true
    fetch(`/lottie/${name}.json`)
      .then((r) => (r.ok ? r.json() : null))
      .then((json) => { if (alive) setData(json) })
      // Файла нет или не загрузился — просто молчим: это украшение,
      // без него всё работает.
      .catch(() => {})
    return () => { alive = false }
  }, [name, reduced, onDone])

  if (reduced || !data) return null

  return (
    <Lottie
      animationData={data}
      loop={false}
      onComplete={onDone}
      style={{ width: size, height: size, margin: '0 auto' }}
    />
  )
}
