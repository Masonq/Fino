/**
 * Ширина плитки раздела/подраздела по названию — та же формула, что в приложении (native/src/tileSize.ts).
 * Надпись и левее картинки (80 в углу), и не уже самого длинного слова.
 */
export function tileSize(name) {
  const words = String(name || '').split(/\s+/)
  const longest = Math.max(...words.map((w) => w.length))
  // широкие буквы (м, ж, ш, щ, ю, ф, ы) — за 1,4 обычной: «Комплектующие», «парфюмерия» иначе рвались
  const weight = (w) => w.length + 0.4 * (w.match(/[мжшщюфыМЖШЩЮФЫmwMW]/g) || []).length
  const widest = Math.max(...words.map(weight))
  if (name.length <= 13 && longest <= 8) return { tile: 142, text: 92 }
  const text = Math.max(106, Math.ceil(widest * 10.9) + 4)
  return { tile: text + 90, text }
}
