import CAT_ART_JSON from './catArt.json'

// форма и заполненность картинок разделов (tools/art_manifest.py): [ширина/высота, доля непрозрачного]
const CAT_ART = CAT_ART_JSON as unknown as Record<string, [number, number, string]>

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
  // картинка целиком внутри плитки, прижата к правому нижнему углу (не уходит за край)
  art: 70, artH: 52, artRight: 7, artBottom: 6, small: 56, smallH: 44, smallRight: 6, smallBottom: 6, lineH: 17, textTop: 13,
}
/** Плитки разделов на главной — меньше, чем внутри разделов (картинка при этом заходит за край, как у Авито). */
export const HOME_TILE: typeof TILE = { ...TILE, w: 112, h: 80, wide: 156, xwide: 200, text: { narrow: 80, wide: 114, xwide: 164, long: 110 } }

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

export const ART_BIG = { position: 'absolute' as const, right: TILE.artRight, bottom: TILE.artBottom, width: TILE.art, height: TILE.artH }
export const ART_SMALL = { position: 'absolute' as const, right: TILE.smallRight, bottom: TILE.smallBottom, width: TILE.small, height: TILE.smallH }
/** предмет прижат к правому нижнему углу своей области — без пустоты снизу и справа */
export const ART_POSITION = { right: 0, bottom: 0 }

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
export type TileFit = { kind: TileKind; tile: number; text: number; art: 'big' | 'small'; h?: number }
export function tileFor(name: string, T: typeof TILE = TILE): TileFit {
  const words = String(name || '').split(/\s+/).filter(Boolean)
  const longest = Math.max(...words.map(wordWidth)) + 2
  const oneLine = words.reduce((s, w, i) => s + wordWidth(w) + (i ? 4 : 0), 0) + 2
  const kinds: [TileKind, number, number][] = [['', T.w, T.text.narrow], ['wide', T.wide, T.text.wide], ['xwide', T.xwide, T.text.xwide]]
  for (const [kind, tile, text] of kinds) {
    if (oneLine <= text) return { kind, tile, text, art: 'big', h: T.h }
    if (!kind) continue // узкая плитка — только для названий в одну строку
    const colBig = tile - T.artRight - T.art - 4 - T.textTop
    if (longest <= colBig) return { kind, tile, text: colBig, art: 'big', h: T.h }
    const colSmall = tile - T.smallRight - T.small - 4 - T.textTop
    if (longest <= colSmall) return { kind, tile, text: colSmall, art: 'small', h: T.h }
  }
  return { kind: 'xwide', tile: T.xwide, text: T.text.xwide, art: 'small', h: T.h }
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
/** Адрес картинки раздела с меткой содержимого (как на сайте): картинку заменили — адрес другой, кэш не мешает. */
export const catPath = (slug: string) => `/cat/${slug}.png${CAT_ART[slug] ? `?v=${CAT_ART[slug][2]}` : ''}`

export const ART_TARGET = 52
export const artSize = (w: number, h: number, fill: number) => Math.sqrt(w * h) * Math.pow(fill, 0.4)
export type TextLine = { right: number; bottom: number }
export function artBox(name: string, fit: TileFit, aspect: number, fill?: number, noTarget = false, lines: TextLine[] | null = null) {
  return artBoxFromLines(fit.tile, aspect, fill, lines || estimateLines(name, fit), noTarget, fit.h || TILE.h)
}

/**
 * Строки надписи по оценке (самый широкий шрифт): правый край и низ каждой — в координатах внутри рамки плитки.
 * Все строки, кроме последней, считаем во всю колонку: при другом шрифте перенос может пройти в другом месте.
 */
export function estimateLines(name: string, fit: TileFit): TextLine[] {
  const TEXT_X = 11
  const words = String(name || '').split(/\s+/).filter(Boolean)
  const oneLine = words.reduce((s, w, i) => s + wordWidth(w) + (i ? 4 : 0), 0) + 2
  const ws: number[] = []
  if (oneLine <= fit.text) ws.push(oneLine)
  else {
    let cur = 0
    for (const w of words) { const ww = wordWidth(w); if (cur && cur + 4 + ww > fit.text) { ws.push(cur); cur = ww } else cur = cur ? cur + 4 + ww : ww }
    if (cur) ws.push(cur)
  }
  return ws.map((w, i) => ({ right: TEXT_X + (i < ws.length - 1 ? fit.text : w), bottom: TEXT_X + (i + 1) * 17 - 1 }))
}

/**
 * Рамка картинки по настоящим строкам надписи (сайт меряет их в браузере, приложение — по раскладке текста):
 * картинка в правом нижнем углу поднимается до низа k-й строки, если строки ниже кончаются левее неё.
 * Перебираем все k и берём рамку, где картинка этой формы выходит крупнее.
 */
export const ART_BLEED = 0.08
export function artBoxFromLines(tileW: number, aspect: number, fill: number | undefined, lines: TextLine[], noTarget = false, tileH = TILE.h) {
  // Как у Авито: картинка прижата к правому нижнему углу вплотную и чуть уходит за край (ART_BLEED её ширины и
  // высоты срезает скругление плитки) — так она крупнее и «живее», чем целиком в рамке с полями.
  const Wi = tileW - 4, Hi = tileH - 4
  const TOP = 6, GAP = 4
  const contain = (w: number, h: number): number[] => (w <= 0 || h <= 0 ? [0, 0] : w / h > aspect ? [h * aspect, h] : [w, w / aspect])
  let best: number[] = [0, 0]
  for (let k = 0; k <= lines.length; k += 1) {
    const top = k ? lines[k - 1].bottom - 3 : TOP // как у Авито: верх картинки может чуть зайти под низ строки (надпись поверх)
    const below = lines.slice(k)
    const left = below.length ? Math.max(...below.map((l) => l.right)) + GAP : 8
    const o = contain(Wi - left, Hi - top) // видимая часть картинки
    if (o[0] * o[1] > best[0] * best[1]) best = o
  }
  let [w, h] = best
  let k = Math.min(1, (Wi * 0.9) / Math.max(w, 1), (Hi - 6) / Math.max(h, 1))
  // общий видимый размер — пропорционально высоте плитки (на главной плитки ниже); в широкой плитке (две в ряд,
  // одна на всю строку) картинка чуть крупнее — иначе она теряется в пустом поле, как «Часы и украшения»
  const wideBoost = Math.min(1.25, Math.max(1, Math.sqrt(tileW / 150)))
  if (fill && fill > 0 && !noTarget) k = Math.min(k, (ART_TARGET * wideBoost * tileH / TILE.h) / Math.max(artSize(w, h, fill), 1))
  w *= k; h *= k
  const W = w / (1 - ART_BLEED), H = h / (1 - ART_BLEED)
  return { position: 'absolute' as const, right: -Math.round(W - w), bottom: -Math.round(H - h), width: Math.round(W), height: Math.round(H) }
}


/**
 * Плитка раздела целиком: ширина надписи и рамка картинки — вместе. Если надпись в колонку поуже (лишняя строка,
 * не больше трёх) освобождает место и картинка выходит заметно крупнее — колонка уже. Картинка — из catArt.json
 * по коду раздела (форма известна сразу, без ожидания загрузки); нет в списке — форма из aspect, без выравнивания.
 */
export function artLayout(name: string, fit: TileFit, slug: string, aspect = 1.3, lines: TextLine[] | null = null): { fit: TileFit; box: ReturnType<typeof artBox> } {
  const known = CAT_ART[slug]
  const [asp, fill] = known ? [known[0], known[1]] : [aspect, 0]
  if (!known) return { fit, box: artBox(name, fit, asp, undefined, false, lines) }
  const size = (f: TileFit) => { const b = artBox(name, f, asp, fill, true); return artSize(b.width, b.height, fill) }
  let best = fit, bestSize = size(fit)
  const minText = Math.ceil(Math.max(...String(name || '').split(/\s+/).filter(Boolean).map(wordWidth), 0)) + 2
  for (let t = fit.text - 4; t >= minText; t -= 4) {
    const f = { ...fit, text: t }
    if (lineCount(name, t) > 3) break
    if (loneShort(name, t)) continue // строка из одного короткого слова («и», «za») — некрасиво, такую колонку не берём
    const s2 = size(f)
    if (s2 > bestSize * 1.08 && s2 > bestSize + 3) { best = f; bestSize = s2 }
  }
  // настоящие строки (если уже измерены) — их мерили по этой же колонке: надпись выводится с best.text
  return { fit: best, box: artBox(name, best, asp, fill, false, lines) }
}
/** Картинка в квадрате-кружке (разделы «Бизнеса»): видимый размер у всех один, не больше 76 из 84. */
export function circleArt(slug: string) {
  const [asp, fill] = CAT_ART[slug] || [1, 0, '']
  let [w, h] = asp > 1 ? [66, 66 / asp] : [66 * asp, 66]
  if (fill > 0) { const k = Math.min(52 / artSize(w, h, fill), 76 / Math.max(w, h)); w *= k; h *= k }
  return { width: Math.round(w), height: Math.round(h) }
}
const loneShort = (name: string, text: number) => {
  const ls: string[][] = []
  let cur = 0
  for (const w of String(name || '').split(/\s+/).filter(Boolean)) { const ww = wordWidth(w); if (cur && cur + 4 + ww > text) { ls.push([w]); cur = ww } else { if (!ls.length) ls.push([]); ls[ls.length - 1].push(w); cur = cur ? cur + 4 + ww : ww } }
  return ls.length > 1 && ls.some((l) => l.length === 1 && l[0].length <= 3)
}
const lineCount = (name: string, text: number) => {
  let n = 0, cur = 0
  for (const w of String(name || '').split(/\s+/).filter(Boolean)) { const ww = wordWidth(w); if (cur && cur + 4 + ww > text) { n += 1; cur = ww } else cur = cur ? cur + 4 + ww : ww }
  return n + (cur ? 1 : 0)
}

/** Ширина самого длинного слова названия — с запасом по самому широкому шрифту (чтобы слово не рвалось). */
export const longestWordWidth = (name: string) => Math.ceil(Math.max(...String(name || '').split(/\s+/).filter(Boolean).map(wordWidth), 0))
/** Название одной строкой — ширина с запасом по самому широкому шрифту. */
export const oneLineWidth = (name: string) => Math.ceil(String(name || '').split(/\s+/).filter(Boolean).reduce((s, w, i) => s + wordWidth(w) + (i ? 4 : 0), 0) + 2)
