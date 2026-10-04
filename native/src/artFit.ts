/**
 * Крупная картинка (84, чуть за правым и нижним краем) или прежняя (66) — для каждой плитки отдельно.
 * Первая строка названия всегда выше картинки; вторая и дальше — на её уровне. Раскладываем название по строкам
 * с запасом по самому широкому шрифту (у Plus Jakarta Sans нет кириллицы — буквы из запасного шрифта
 * устройства): 10,6 точки на букву при 14,5 жирным, м/ж/ш/щ/ю/ф/ы — ×1,4. Если вторая строка доходит
 * до картинки — у этой плитки картинка прежняя, иначе крупная. Та же формула — frontend/src/utils/artFit.js.
 */
// надпись 13,5 жирным (было 14,5): запас 9,9 точки на букву
/** Размеры плиток — одни на главной, в разделах и в «Работе» (сайт: .jl-tile / .cat-tile-2row в styles.css). */
export const TILE = {
  w: 124, h: 88, wide: 172, xwide: 220, pad: 11,
  text: { narrow: 92, wide: 130, xwide: 184, long: 122 },
  art: 74, artRight: 9, artBottom: 17, small: 58, lineH: 17, textTop: 13,
}

const CHAR = 9.9
const SPACE = 4
// самый узкий из наших шрифтов для кириллицы при 13,5 жирным (сайт): ≈8,3 точки на букву
const BREAK_CHAR = 8.3
const wordW = (w: string) => (w.length + 0.4 * (w.match(/[мжшщюфыМЖШЩЮФЫmwMW]/g) || []).length) * CHAR

export function bigArtFits(name: string, textMax: number, tileW: number, art = TILE.art, right = TILE.artRight): boolean {
  const lines: number[] = []
  let cur = 0
  let curB = 0
  for (const w of String(name || '').split(/\s+/)) {
    // раскладка по самому узкому шрифту (в строку влезает больше слов — так строки бывают длиннее), длина — по широкому
    const wb = wordW(w) * BREAK_CHAR / CHAR
    if (cur && curB + SPACE + wb > textMax) { lines.push(cur); cur = wordW(w); curB = wb } else { cur = cur ? cur + SPACE + wordW(w) : wordW(w); curB = curB ? curB + SPACE + wb : wb }
  }
  if (cur) lines.push(cur)
  const artLeft = tileW + right - art // картинка в углу: 84 при right −10 (или прежняя 66 при −2)
  // строки, которые доходят до верха картинки, должны кончаться левее неё (любая строка — и первая тоже)
  const artTop = TILE.h + (art === TILE.art ? TILE.artBottom : 3) - art
  return lines.every((w, i) => TILE.textTop + (i + 1) * TILE.lineH <= artTop + 3 || TILE.textTop + w <= artLeft - 4)
}

/** Название не помещается левее даже прежней картинки в своей плитке — плитку шире (240). */
export const needsWiderTile = (name: string, textMax: number, tileW: number) => !bigArtFits(name, textMax, tileW) && !bigArtFits(name, textMax, tileW, TILE.small, 2)

export const ART_BIG = { position: 'absolute' as const, right: -TILE.artRight, bottom: -TILE.artBottom, width: TILE.art, height: TILE.art }
export const ART_SMALL = { position: 'absolute' as const, right: -2, bottom: -3, width: TILE.small, height: TILE.small }

/**
 * Плитка по названию — одна функция для сайта и приложения (frontend/src/utils/artFit.js — то же).
 * Переносы строк на разных устройствах разные, поэтому решение не зависит от того, где пройдёт перенос:
 *  - название целиком в одну строку (с запасом по самому широкому шрифту) — строка выше картинки → картинка крупная;
 *  - иначе надписи отводится колонка строго левее картинки (крупной, если в неё влезает самое длинное слово,
 *    иначе прежней) — где бы ни прошёл перенос, строки до картинки не дотянутся;
 *  - не влезает ни так, ни так — плитка шире.
 */
const WIDE_CHAR = 9.9 // самый широкий из наших шрифтов для кириллицы при 13,5 жирным (приложение)
const wordWidth = (w: string) => (w.length + 0.4 * (w.match(/[мжшщюфыМЖШЩЮФЫmwMW]/g) || []).length) * WIDE_CHAR
export type TileKind = '' | 'wide' | 'xwide'
export type TileFit = { kind: TileKind; tile: number; text: number; art: 'big' | 'small' }
export function tileFor(name: string): TileFit {
  const words = String(name || '').split(/\s+/).filter(Boolean)
  const longest = Math.max(...words.map(wordWidth)) + 2
  const oneLine = words.reduce((s, w, i) => s + wordWidth(w) + (i ? 4 : 0), 0) + 2
  const kinds: [TileKind, number, number][] = [['', TILE.w, TILE.text.narrow], ['wide', TILE.wide, TILE.text.wide], ['xwide', TILE.xwide, TILE.text.xwide]]
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
