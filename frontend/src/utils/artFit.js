/**
 * Крупная картинка (84) или прежняя (66) — для каждой плитки отдельно; та же формула, что в приложении
 * (native/src/artFit.ts): если вторая строка названия доходит до места картинки — у этой плитки картинка прежняя.
 */
// у сайта запасной шрифт для кириллицы уже, чем у приложения (≈9 против 10,6 точки на букву) — запас 9,8
const CHAR = 9.8
const SPACE = 4
const wordW = (w) => (w.length + 0.4 * (w.match(/[мжшщюфыМЖШЩЮФЫmwMW]/g) || []).length) * CHAR

export function bigArtFits(name, textMax, tileW, art = 84, right = 10) {
  const lines = []
  let cur = 0
  for (const w of String(name || '').split(/\s+/)) {
    const ww = wordW(w)
    if (cur && cur + SPACE + ww > textMax) { lines.push(cur); cur = ww } else cur = cur ? cur + SPACE + ww : ww
  }
  if (cur) lines.push(cur)
  const artLeft = tileW + right - art
  return lines.slice(1).every((w) => 13 + w <= artLeft - 4)
}

/** Название не помещается левее даже прежней картинки — плитку шире (xwide, 240). */
export const needsWiderTile = (name, textMax, tileW) => !bigArtFits(name, textMax, tileW) && !bigArtFits(name, textMax, tileW, 66, 2)
