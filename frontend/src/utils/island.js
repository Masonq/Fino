/*
 * Остров — короткое сообщение вверху экрана (см. components/Island.jsx).
 *
 * Любое место сайта зовёт showIsland({ text, kind, to }) и не знает,
 * где и как это нарисуется. Так «ссылка скопирована» и «новое
 * сообщение» — один и тот же элемент, а не две самодельные всплывашки.
 *
 *   kind: 'ok' — сделано; 'msg' — сообщение (нажатие ведёт по to);
 *         'warn' — что-то не вышло
 */
export function showIsland(item) {
  window.dispatchEvent(new CustomEvent('plonk:island', { detail: item }))
}
