/**
 * Первое открытие приложения без «прыгающих» блоков: заставка держится, пока главная не соберёт первый экран
 * (город и настройки прочитаны, первая страница ленты есть — из кэша или с сервера), но не дольше 1,8 с —
 * если открыли сразу другой экран по ссылке, ждать главную незачем.
 */
let done: () => void = () => {}
const ready = new Promise<void>((r) => { done = r })
export const markHomeReady = () => done()
export const waitHomeReady = (maxMs = 1800) => Promise.race([ready, new Promise<void>((r) => setTimeout(r, maxMs))])
