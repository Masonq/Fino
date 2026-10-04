/**
 * Ширина плитки раздела/подраздела по названию — одна формула для приложения и сайта (frontend/src/utils/tileSize.js).
 * Картинка 80 стоит в правом нижнем углу (right −6): её левый край = ширина плитки − 74. Надпись должна быть
 * и левее картинки, и не уже самого длинного слова — иначе слово рвётся посреди. Запас — по самому широкому
 * из наших шрифтов (≈10,9 точки на букву при 14,5 жирным: у Plus Jakarta Sans нет кириллицы, буквы берутся из запасного шрифта устройства — считаем по самому широкому).
 */
export function tileSize(name: string): { tile: number; text: number } {
  const words = name.split(/\s+/)
  const longest = Math.max(...words.map((w) => w.length))
  // широкие буквы (м, ж, ш, щ, ю, ф, ы) — за 1,4 обычной: «Комплектующие», «парфюмерия» иначе рвались
  const weight = (w: string) => w.length + 0.4 * (w.match(/[мжшщюфыМЖШЩЮФЫmwMW]/g) || []).length
  const widest = Math.max(...words.map(weight))
  if (name.length <= 13 && longest <= 8) return { tile: 142, text: 92 }
  const text = Math.max(106, Math.ceil(widest * 10.9) + 4)
  return { tile: text + 90, text }
}
