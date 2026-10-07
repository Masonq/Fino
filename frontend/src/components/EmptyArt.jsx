/**
 * Картинка пустого экрана (public/empty/*.webp): объёмный предмет без фона, как плитки разделов.
 * Место держится заранее (width/height), загрузка не сдвигает текст под ней.
 */
export default function EmptyArt({ name }) {
  return <img className="empty-art" src={`/empty/${name}.webp`} alt="" width="168" height="168" decoding="async" aria-hidden="true" />
}
