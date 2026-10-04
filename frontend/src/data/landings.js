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

/**
 * Поля для подраздела: берём поля его раздела и оставляем те, что у
 * объявлений этого подраздела и правда заполняются.
 *
 * Свои поля были только у двенадцати разделов верхнего уровня, а
 * страница открывается и у подразделов — «Легковые», «Квартиры»,
 * «Телефоны». Там не было ничего, даже цены. Просто унаследовать нельзя:
 * на «Запчастях» появился бы пробег, на «Гаражах» — комнаты. Поэтому
 * сверяемся со схемой формы размещения: о чём продавца не спрашивали,
 * по тому и искать нечего.
 *
 * Список марок и подбор модели — только там, где марка в форме тоже
 * выбирается из списка: у шин и запчастей она пишется текстом, и
 * автомобильный список там чужой.
 */
export function landingFor(slug, rootSlug, schema) {
  if (LANDINGS[slug]) return LANDINGS[slug]
  const base = LANDINGS[rootSlug]
  if (!base || !schema) return null
  const byKey = Object.fromEntries(schema.map((f) => [f.key, f]))
  const fields = (base.fields || []).filter((field) => {
    if (field.key === 'price' || field.key === 'q') return true
    const own = byKey[field.key === 'model' && field.type === 'car-model' ? 'brand' : field.key]
    if (!own) return false
    if (field.type === 'select' || field.type === 'car-model') return own.type === 'select'
    return true
  })
  return { deal: byKey.deal_type ? base.deal : undefined, fields }
}

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
        options: [{ value: 'studio', label: 'landing.rooms_studio' }, '1', '2', '3', '4+'] },
      { key: 'price', label: 'landing.price', type: 'range' },
    ],
  },

  auto: {
    fields: [
      { key: 'brand', label: 'landing.brand', type: 'select',
        placeholder: 'landing.brand_placeholder', options: CAR_BRANDS },
      { key: 'model', label: 'landing.model', type: 'car-model' },
      { key: 'year', label: 'landing.year', type: 'range' },
      // Пробег и коробка — тот же стандартный набор, что уже есть у
      // формы размещения (mileage_km/transmission в schemas.py), но
      // раньше на входе в раздел их не спрашивали вовсе — только марка,
      // модель, год, цена. Реальный человек, ищущий машину, почти
      // всегда уточняет и то, и другое сразу.
      { key: 'mileage_km', label: 'landing.mileage', type: 'range' },
      { key: 'transmission', label: 'landing.transmission', type: 'chips',
        options: [
          { value: 'manual', label: 'landing.transmission_manual' },
          { value: 'automatic', label: 'landing.transmission_automatic' },
        ] },
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
      // age_group — уже есть в форме размещения (AGE_GROUP,
      // schemas.py) и главный ориентир покупателя детских товаров —
      // подойдёт ли ребёнку по возрасту, важнее почти всего
      // остального. Раньше на входе в раздел спрашивали только цену.
      { key: 'age_group', label: 'landing.age', type: 'chips',
        options: [
          { value: 'baby', label: 'landing.age_baby' },
          { value: 'toddler', label: 'landing.age_toddler' },
          { value: 'preschool', label: 'landing.age_preschool' },
          { value: 'school', label: 'landing.age_school' },
        ] },
      { key: 'price', label: 'landing.price', type: 'range' },
    ],
  },

  electronics: {
    fields: [
      { key: 'q', label: 'landing.model', type: 'text',
        hint: 'landing.model_hint' },
      // Состояние — уже есть в форме размещения (CONDITION,
      // schemas.py), для электроники разница в цене между «новое» и
      // «б/у» велика, и это один из первых вопросов у покупателя.
      { key: 'condition', label: 'landing.condition', type: 'chips',
        options: [
          { value: 'new', label: 'landing.condition_new' },
          { value: 'like_new', label: 'landing.condition_like_new' },
          { value: 'used', label: 'landing.condition_used' },
        ] },
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

/**
 * Комнаты на входе в раздел → значения поля «Комнат» у объявлений (schemas.py, ROOMS): «1» — это и полуторка,
 * «2» — и двушка с половиной, «4+» — четыре и больше (старые объявления могли хранить 5, 6…). Отбор по полю,
 * а не по словам в тексте: словами «4+» находил и однушки.
 */
export const ROOMS_IN = {
  studio: ['studio'],
  1: ['1', '1.5'],
  2: ['2', '2.5'],
  3: ['3', '3.5'],
  '4+': ['4', '4.5', '5', '6', '7', '8', '9', '10'],
}
