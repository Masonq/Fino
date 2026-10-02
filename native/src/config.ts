/**
 * Откуда приложение берёт данные. По умолчанию — боевой plonk.rs; для проверки на компьютере можно подставить
 * свой адрес через EXPO_PUBLIC_SITE (пустая строка — тот же адрес, откуда открыта страница).
 */
const fromEnv = process.env.EXPO_PUBLIC_SITE
export const SITE = fromEnv !== undefined ? fromEnv : 'https://plonk.rs'
export const API = `${SITE}/api`

/** Ссылка на картинку: с сервера приходят пути вида /media/abc.webp — дописываем адрес сайта. */
export function mediaUrl(url?: string | null): string | null {
  if (!url) return null
  return /^https?:\/\//.test(url) ? url : `${SITE}${url}`
}
