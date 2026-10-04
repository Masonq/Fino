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
export const TILE = { w: 124, h: 88, wide: 172, xwide: 220, pad: 11, text: { narrow: 92, wide: 130, xwide: 184, long: 122 }, art: 70, artH: 52, artRight: 7, artBottom: 6, small: 56, smallH: 44, smallRight: 6, smallBottom: 6, lineH: 17, textTop: 13 }

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
    const colBig = tile - TILE.artRight - TILE.art - 4 - TILE.textTop
    if (longest <= colBig) return { kind, tile, text: colBig, art: 'big' }
    const colSmall = tile - TILE.smallRight - TILE.small - 4 - TILE.textTop
    if (longest <= colSmall) return { kind, tile, text: colSmall, art: 'small' }
  }
  return { kind: 'xwide', tile: TILE.xwide, text: TILE.text.xwide, art: 'small' }
}

/**
 * Размер картинки на плитке по форме самой картинки — крупно, но целиком внутри плитки и не задевая надпись.
 * Места два: рядом с надписью (на всю высоту) или под первой строкой (на всю ширину); берётся то, где картинка
 * этой формы выходит крупнее. Надпись — с запасом по самому широкому шрифту. Координаты — внутри рамки плитки.
 */
export function artBox(name, fit, aspect) {
  const Wi = fit.tile - 4, Hi = TILE.h - 4
  const R = 5, B = 5, TOP = 6, LINE1 = 28, TEXT_X = 11
  const words = String(name || '').split(/\s+/).filter(Boolean)
  const oneLine = words.reduce((s, w, i) => s + wordWidth(w) + (i ? 4 : 0), 0) + 2
  const contain = (w, h) => (w <= 0 || h <= 0 ? [0, 0] : w / h > aspect ? [h * aspect, h] : [w, w / aspect])
  const options = []
  if (oneLine <= fit.text) {
    options.push(contain(Wi - R - (TEXT_X + oneLine + 6), Hi - B - TOP)) // рядом с надписью
    options.push(contain(Wi - R - 8, Hi - B - (LINE1 - 1))) // под надписью (буквы кончаются выше нижней границы строки)
  } else {
    options.push(contain(Wi - R - (TEXT_X + fit.text + 6), Hi - B - TOP)) // справа от колонки надписи
    // под всеми строками: их число — по самому широкому шрифту (на любом устройстве строк столько же или меньше)
    let lines = 1, cur = 0
    for (const w of words) { const ww = wordWidth(w); if (cur && cur + 4 + ww > fit.text) { lines += 1; cur = ww } else cur = cur ? cur + 4 + ww : ww }
    options.push(contain(Wi - R - 8, Hi - B - (TEXT_X + lines * 17 - 1)))
  }
  let [w, h] = options.reduce((best, o) => (o[0] * o[1] > best[0] * best[1] ? o : best), [0, 0])
  const k = Math.min(1, (Wi * 0.66) / Math.max(w, 1), 72 / Math.max(h, 1)) // не крупнее 2/3 плитки и 72 по высоте
  w *= k; h *= k
  return { position: 'absolute', right: R, bottom: B, width: Math.round(w), height: Math.round(h) }
}

/** Ширина самого длинного слова названия — с запасом по самому широкому шрифту (чтобы слово не рвалось). */
export const longestWordWidth = (name) => Math.ceil(Math.max(...String(name || '').split(/\s+/).filter(Boolean).map(wordWidth), 0))
/** Название одной строкой — ширина с запасом по самому широкому шрифту. */
export const oneLineWidth = (name) => Math.ceil(String(name || '').split(/\s+/).filter(Boolean).reduce((s, w, i) => s + wordWidth(w) + (i ? 4 : 0), 0) + 2)
