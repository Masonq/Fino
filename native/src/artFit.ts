/**
 * Крупная картинка (84, чуть за правым и нижним краем) или прежняя (66) — для каждой плитки отдельно.
 * Первая строка названия всегда выше картинки; вторая и дальше — на её уровне. Раскладываем название по строкам
 * с запасом по самому широкому шрифту (у Plus Jakarta Sans нет кириллицы — буквы из запасного шрифта
 * устройства): 10,6 точки на букву при 14,5 жирным, м/ж/ш/щ/ю/ф/ы — ×1,4. Если вторая строка доходит
 * до картинки — у этой плитки картинка прежняя, иначе крупная. Та же формула — frontend/src/utils/artFit.js.
 */
const CHAR = 10.6
const SPACE = 4
const wordW = (w: string) => (w.length + 0.4 * (w.match(/[мжшщюфыМЖШЩЮФЫmwMW]/g) || []).length) * CHAR

export function bigArtFits(name: string, textMax: number, tileW: number, art = 84, right = 10): boolean {
  const lines: number[] = []
  let cur = 0
  for (const w of String(name || '').split(/\s+/)) {
    const ww = wordW(w)
    if (cur && cur + SPACE + ww > textMax) { lines.push(cur); cur = ww } else cur = cur ? cur + SPACE + ww : ww
  }
  if (cur) lines.push(cur)
  const artLeft = tileW + right - art // картинка в углу: 84 при right −10 (или прежняя 66 при −2)
  return lines.slice(1).every((w) => 13 + w <= artLeft - 4)
}

/** Название не помещается левее даже прежней картинки в своей плитке — плитку шире (240). */
export const needsWiderTile = (name: string, textMax: number, tileW: number) => !bigArtFits(name, textMax, tileW) && !bigArtFits(name, textMax, tileW, 66, 2)

export const ART_BIG = { position: 'absolute' as const, right: -10, bottom: -16, width: 84, height: 84 }
export const ART_SMALL = { position: 'absolute' as const, right: -2, bottom: -4, width: 66, height: 66 }
