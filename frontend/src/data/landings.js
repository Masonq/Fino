/**
 * Что спрашивать на входе в раздел.
 *
 * Человек, зашедший в «Недвижимость», ищет не «что-нибудь» — он хочет
 * снять двушку до тысячи евро. Общее поле поиска этого не спрашивает, и
 * ему приходится листать всё подряд.
 *
 * Поля свои у каждого раздела: у квартир комнатность и цена, у авто
 * марка и год, у работы — ищет он или нанимает. Общие поля вроде города
 * тут не повторяем, они и так в отборе.
 */

import { CAR_BRANDS } from './carBrands'

// Что показывать вместо цены там, где её принято называть иначе.
export const LANDINGS = {
  'real-estate': {
    // Первый вопрос — самый крупный: он делит раздел надвое, и без
    // ответа на него остальное бессмысленно.
    deal: {
      label: 'landing.deal',
      options: [
        { value: 'sale', label: 'landing.buy' },
        { value: 'rent', label: 'landing.rent' },
        { value: 'daily', label: 'landing.daily' },
      ],
    },
    fields: [
      { key: 'rooms', label: 'landing.rooms', type: 'chips',
        options: ['1', '2', '3', '4+'] },
      { key: 'price', label: 'landing.price', type: 'range' },
    ],
  },

  auto: {
    fields: [
      { key: 'brand', label: 'landing.brand', type: 'select',
        placeholder: 'landing.brand_placeholder', options: CAR_BRANDS },
      { key: 'model', label: 'landing.model', type: 'car-model' },
      { key: 'year', label: 'landing.year', type: 'range' },
      { key: 'price', label: 'landing.price', type: 'range' },
    ],
  },

  jobs: {
    // deal (Ищу работу/Ищу сотрудников) сюда сознательно не входит —
    // тот же выбор теперь настоящей подкатегорией (Вакансии/Резюме,
    // плитки чуть ниже на этой же странице): бэкенд научили превращать
    // эти слаги в фильтр по jobs + attributes.listing_kind. Прежде оба
    // вели к одному и тому же, но плитки всегда возвращали пустую
    // выдачу — теперь оба варианта рабочие, держать два ряда под одно
    // и то же незачем.
    fields: [],
  },

  fashion: {
    fields: [
      { key: 'size', label: 'landing.size', type: 'chips',
        options: ['XS', 'S', 'M', 'L', 'XL'] },
      { key: 'price', label: 'landing.price', type: 'range' },
    ],
  },

  kids: {
    fields: [
      { key: 'price', label: 'landing.price', type: 'range' },
    ],
  },

  electronics: {
    fields: [
      { key: 'q', label: 'landing.model', type: 'text',
        hint: 'landing.model_hint' },
      { key: 'price', label: 'landing.price', type: 'range' },
    ],
  },

  'home-garden': {
    fields: [
      { key: 'price', label: 'landing.price', type: 'range' },
    ],
  },

  'hobby-sport': {
    fields: [
      { key: 'price', label: 'landing.price', type: 'range' },
    ],
  },

  pets: {
    fields: [
      { key: 'price', label: 'landing.price', type: 'range' },
    ],
  },

  beauty: {
    fields: [
      { key: 'price', label: 'landing.price', type: 'range' },
    ],
  },

  services: {
    fields: [
      { key: 'price', label: 'landing.price', type: 'range' },
    ],
  },

  business: {
    fields: [
      { key: 'price', label: 'landing.price', type: 'range' },
    ],
  },
}

/** Есть ли у раздела свои поля. */
export function hasLanding(slug) {
  return Boolean(LANDINGS[slug])
}
