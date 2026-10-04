/**
 * Крупная картинка (84) или прежняя (66) — для каждой плитки отдельно; та же формула, что в приложении
 * (native/src/artFit.ts): если вторая строка названия доходит до места картинки — у этой плитки картинка прежняя.
 */
// у сайта запасной шрифт для кириллицы уже, чем у приложения (≈9 против 10,6 точки на букву) — запас 9,8
const CHAR = 9.1 // надпись 13,5 (было 14,5): 9,8 × 13,5/14,5
const SPACE = 4
// самый узкий из наших шрифтов для кириллицы при 13,5 жирным (сайт): ≈8,3 точки на букву
const BREAK_CHAR = 8.3
const wordW = (w) => (w.length + 0.4 * (w.match(/[мжшщюфыМЖШЩЮФЫmwMW]/g) || []).length) * CHAR

/** Размеры плиток — те же, что в приложении (native/src/artFit.ts, TILE). */
export const TILE = { w: 124, h: 88, wide: 172, xwide: 220, pad: 11, text: { narrow: 92, wide: 130, xwide: 184, long: 122 }, art: 74, artRight: 9, artBottom: 17, small: 58, lineH: 17, textTop: 13 }

export function bigArtFits(name, textMax, tileW, art = TILE.art, right = TILE.artRight) {
  const lines = []
  let cur = 0
  let curB = 0
  for (const w of String(name || '').split(/\s+/)) {
    // раскладка по самому узкому шрифту (в строку влезает больше слов — так строки бывают длиннее), длина — по широкому
    const wb = wordW(w) * BREAK_CHAR / CHAR
    if (cur && curB + SPACE + wb > textMax) { lines.push(cur); cur = wordW(w); curB = wb } else { cur = cur ? cur + SPACE + wordW(w) : wordW(w); curB = curB ? curB + SPACE + wb : wb }
  }
  if (cur) lines.push(cur)
  const artLeft = tileW + right - art
  const artTop = TILE.h + (art === TILE.art ? TILE.artBottom : 3) - art
  return lines.every((w, i) => TILE.textTop + (i + 1) * TILE.lineH <= artTop + 3 || TILE.textTop + w <= artLeft - 4)
}

/** Название не помещается левее даже прежней картинки — плитку шире (xwide, 240). */
export const needsWiderTile = (name, textMax, tileW) => !bigArtFits(name, textMax, tileW) && !bigArtFits(name, textMax, tileW, TILE.small, 2)

/**
 * Плитка по названию — одна функция для сайта и приложения (native/src/artFit.ts — то же).
 * Переносы строк на разных устройствах разные, поэтому решение не зависит от того, где пройдёт перенос:
 *  - название целиком в одну строку (с запасом по самому широкому шрифту) — строка выше картинки → картинка крупная;
 *  - иначе надписи отводится колонка строго левее картинки (крупной, если в неё влезает самое длинное слово,
 *    иначе прежней) — где бы ни прошёл перенос, строки до картинки не дотянутся;
 *  - не влезает ни так, ни так — плитка шире.
 */
const WIDE_CHAR = 9.9 // самый широкий из наших шрифтов для кириллицы при 13,5 жирным (приложение)
const wordWidth = (w) => (w.length + 0.4 * (w.match(/[мжшщюфыМЖШЩЮФЫmwMW]/g) || []).length) * WIDE_CHAR
export function tileFor(name) {
  const words = String(name || '').split(/\s+/).filter(Boolean)
  const longest = Math.max(...words.map(wordWidth)) + 2
  const oneLine = words.reduce((s, w, i) => s + wordWidth(w) + (i ? 4 : 0), 0) + 2
  const kinds = [['', TILE.w, TILE.text.narrow], ['wide', TILE.wide, TILE.text.wide], ['xwide', TILE.xwide, TILE.text.xwide]]
  for (const [kind, tile, text] of kinds) {
    if (oneLine <= text) return { kind, tile, text, art: 'big' }
    if (!kind) continue // узкая плитка — только для названий в одну строку
    const colBig = tile + TILE.artRight - TILE.art - 4 - TILE.textTop
    if (longest <= colBig) return { kind, tile, text: colBig, art: 'big' }
    const colSmall = tile + 2 - TILE.small - 4 - TILE.textTop
    if (longest <= colSmall) return { kind, tile, text: colSmall, art: 'small' }
  }
  return { kind: 'xwide', tile: TILE.xwide, text: TILE.text.xwide, art: 'small' }
}
