import type { FeedItem } from './api'

/** Данные карточки, на которую нажали, — чтобы экран объявления показался мгновенно, до ответа сервера. */
const seeds = new Map<string, FeedItem>()
export const seedListing = (item: FeedItem) => { seeds.set(item.id, item) }
export const getSeed = (id: string) => seeds.get(id)
