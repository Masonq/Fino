import CAT_ART from '../data/catArt.json'

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
 * Места три: рядом со всей надписью (на всю высоту), рядом с последней строкой (она обычно короче остальных)
 * и под всеми строками (на всю ширину); берётся то, где картинка этой формы выходит крупнее. Надпись — с запасом
 * по самому широкому шрифту: при узком шрифте слова уходят в строки раньше, последняя строка только короче.
 *
 * fill — доля непрозрачного в картинке (из catArt.json). Видимый размер считается по ней: разреженная
 * композиция (самокат с велосипедом) в той же рамке выглядит мельче плотной (стопка кирпичей). Крупные
 * уменьшаются до общего размера ART_TARGET, мелкие берут всё доступное место — так плитки ровнее друг с другом.
 */
/** Адрес картинки раздела с меткой содержимого: картинку заменили — адрес другой, старая из кэша не покажется. */
export const catSrc = (slug) => `/cat/${slug}.png${CAT_ART[slug] ? `?v=${CAT_ART[slug][2]}` : ''}`

export const ART_TARGET = 48
export const artSize = (w, h, fill) => Math.sqrt(w * h) * Math.pow(fill, 0.4)
export function artBox(name, fit, aspect, fill, noTarget = false) {
  const Wi = fit.tile - 4, Hi = TILE.h - 4
  const R = 5, B = 5, TOP = 6, TEXT_X = 11
  const words = String(name || '').split(/\s+/).filter(Boolean)
  const oneLine = words.reduce((s, w, i) => s + wordWidth(w) + (i ? 4 : 0), 0) + 2
  const contain = (w, h) => (w <= 0 || h <= 0 ? [0, 0] : w / h > aspect ? [h * aspect, h] : [w, w / aspect])
  // строки по самому широкому шрифту: их число и ширина последней
  const lines = []
  if (oneLine <= fit.text) lines.push(oneLine)
  else {
    let cur = 0
    for (const w of words) { const ww = wordWidth(w); if (cur && cur + 4 + ww > fit.text) { lines.push(cur); cur = ww } else cur = cur ? cur + 4 + ww : ww }
    if (cur) lines.push(cur)
  }
  const n = lines.length
  const col = n > 1 ? fit.text : oneLine
  const bottomOf = (k) => TEXT_X + k * 17 - 1 // низ k-й строки (буквы кончаются выше)
  const options = [
    contain(Wi - R - (TEXT_X + col + 6), Hi - B - TOP), // рядом со всей надписью
    contain(Wi - R - 8, Hi - B - (n === 1 ? 27 : bottomOf(n))), // под всеми строками
  ]
  if (n > 1) options.push(contain(Wi - R - (TEXT_X + lines[n - 1] + 6), Hi - B - bottomOf(n - 1))) // рядом с последней строкой
  let [w, h] = options.reduce((best, o) => (o[0] * o[1] > best[0] * best[1] ? o : best), [0, 0])
  let k = Math.min(1, (Wi * 0.85) / Math.max(w, 1), 72 / Math.max(h, 1)) // не крупнее 85% ширины плитки и 72 по высоте
  if (fill > 0 && !noTarget) k = Math.min(k, ART_TARGET / Math.max(artSize(w, h, fill), 1))
  w *= k; h *= k
  return { position: 'absolute', right: R, bottom: B, width: Math.round(w), height: Math.round(h) }
}

/**
 * Плитка раздела целиком: ширина надписи и рамка картинки — вместе. Если надпись в колонку поуже (лишняя строка,
 * не больше трёх) освобождает место и картинка выходит заметно крупнее — колонка уже. Картинка — из catArt.json
 * по коду раздела (форма известна сразу, без ожидания загрузки); нет в списке — форма из aspect, без выравнивания.
 */
export function artLayout(name, fit, slug, aspect = 1.3) {
  const known = CAT_ART[slug]
  const [asp, fill] = known || [aspect, undefined]
  if (!known) return { fit, box: artBox(name, fit, asp) }
  const size = (f) => { const b = artBox(name, f, asp, fill, true); return artSize(b.width, b.height, fill) }
  let best = fit, bestSize = size(fit)
  const minText = Math.ceil(Math.max(...String(name || '').split(/\s+/).filter(Boolean).map(wordWidth), 0)) + 2
  for (let t = fit.text - 4; t >= minText; t -= 4) {
    const f = { ...fit, text: t }
    if (lineCount(name, t) > 3) break
    if (loneShort(name, t)) continue // строка из одного короткого слова («и», «za») — некрасиво, такую колонку не берём
    const s2 = size(f)
    if (s2 > bestSize * 1.08 && s2 > bestSize + 3) { best = f; bestSize = s2 }
  }
  return { fit: best, box: artBox(name, best, asp, fill) }
}
/** Картинка в квадрате-кружке (разделы «Бизнеса»): видимый размер у всех один, не больше 76 из 84. */
export function circleArt(slug) {
  const [asp, fill] = CAT_ART[slug] || [1, 0]
  let [w, h] = asp > 1 ? [66, 66 / asp] : [66 * asp, 66]
  if (fill > 0) { const k = Math.min(52 / artSize(w, h, fill), 76 / Math.max(w, h)); w *= k; h *= k }
  return { width: Math.round(w), height: Math.round(h) }
}
const loneShort = (name, text) => {
  const ls = []
  let cur = 0
  for (const w of String(name || '').split(/\s+/).filter(Boolean)) { const ww = wordWidth(w); if (cur && cur + 4 + ww > text) { ls.push([w]); cur = ww } else { if (!ls.length) ls.push([]); ls[ls.length - 1].push(w); cur = cur ? cur + 4 + ww : ww } }
  return ls.length > 1 && ls.some((l) => l.length === 1 && l[0].length <= 3)
}
const lineCount = (name, text) => {
  let n = 0, cur = 0
  for (const w of String(name || '').split(/\s+/).filter(Boolean)) { const ww = wordWidth(w); if (cur && cur + 4 + ww > text) { n += 1; cur = ww } else cur = cur ? cur + 4 + ww : ww }
  return n + (cur ? 1 : 0)
}

/** Ширина самого длинного слова названия — с запасом по самому широкому шрифту (чтобы слово не рвалось). */
export const longestWordWidth = (name) => Math.ceil(Math.max(...String(name || '').split(/\s+/).filter(Boolean).map(wordWidth), 0))
/** Название одной строкой — ширина с запасом по самому широкому шрифту. */
export const oneLineWidth = (name) => Math.ceil(String(name || '').split(/\s+/).filter(Boolean).reduce((s, w, i) => s + wordWidth(w) + (i ? 4 : 0), 0) + 2)
