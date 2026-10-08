import i18n from '../i18n'
const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export const TOKEN_KEY = 'plonk_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(value) {
  try { localStorage.setItem(TOKEN_KEY, value) } catch { /* не беда */ }
}

// Адрес живого чата — тот же хост, что и у обычных запросов, только
// http(s) меняем на ws(s) и добавляем токен параметром: браузер не
// даёт выставить заголовок Authorization при открытии WebSocket,
// только то, что помещается в сам URL.
export function chatWsUrl(chatId) {
  const token = getToken()
  if (!token) return null
  const base = API_BASE.startsWith('http')
    ? API_BASE.replace(/^http/, 'ws')
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${API_BASE}`
  return `${base}/chats/${chatId}/ws?token=${encodeURIComponent(token)}`
}

// Случайный id устройства — заводится один раз и хранится в localStorage,
// не отпечаток в строгом смысле (сбрасывается очисткой данных сайта), но
// достаточно, чтобы при входе отличить «тот же браузер, что обычно» от
// «совсем другой» — см. record_login на бэкенде.
const DEVICE_KEY = 'plonk_device_id'
function getDeviceId() {
  let id = localStorage.getItem(DEVICE_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(DEVICE_KEY, id)
  }
  return id
}

async function request(path, options = {}) {
  const token = getToken()

  // Тело запроса всегда строкой.
  //
  // Передал объект как есть — fetch отправил «[object Object]», сервер
  // ответил «неверные данные», а на экране появилось общее «не
  // получилось». Ошибка тихая: ни в консоли, ни в журнале ничего
  // внятного, только код 422 в логе сервера. Раз уж такое возможно —
  // превращаем сами, а не полагаемся на память.
  const body = options.body && typeof options.body === 'object'
    && !(options.body instanceof FormData)
    ? JSON.stringify(options.body)
    : options.body

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    ...(body === undefined ? {} : { body }),
    headers: {
      'Content-Type': 'application/json',
      // язык страницы — сервер показывает имена людей латиницей на сербском и английском
      'X-Lang': (i18n.language || 'sr').slice(0, 2),
      'X-Device-Id': getDeviceId(),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  })
  if (!res.ok) {
    // пробрасываем код ошибки от сервера — экранам нужно отличать
    // «неверный код» от «слишком много попыток»
    let detail = null
    try { detail = (await res.json()).detail } catch { /* тело пустое */ }
    const err = new Error(detail || `API error ${res.status}`)
    err.status = res.status
    err.code = detail
    throw err
  }
  return res.json()
}

// Заранее запрошенные объявления: ключ — номер, значение — обещание
// ответа. Живёт до перехода на карточку, дальше запись убирается.
const prefetched = new Map()

/**
 * Собирает строку запроса, выбрасывая пустые значения.
 *
 * URLSearchParams превращает undefined в строку «undefined», и сервер
 * получал city=undefined как настоящее название города — лента при
 * выборе «Все города» становилась пустой. Ошибка тихая: запрос
 * выполняется, ответ приходит, просто в нём ничего нет.
 */
function query(params) {
  const clean = {}
  for (const [key, value] of Object.entries(params || {})) {
    if (value === undefined || value === null || value === '') continue
    clean[key] = value
  }
  return new URLSearchParams(clean).toString()
}

export const api = {
  // Витрина продавца (backend/app/routers/storefronts.py)
  sfMe: (lang) => request(`/storefronts/me?lang=${lang || 'sr'}`),
  sfAutobuild: (body, lang) => request(`/storefronts/me/autobuild?lang=${lang || 'sr'}`, { method: 'POST', body }),
  sfEdit: (body, lang) => request(`/storefronts/me?lang=${lang || 'sr'}`, { method: 'PATCH', body }),
  sfItems: (ids, lang) => request(`/storefronts/me/items?lang=${lang || 'sr'}`, { method: 'PUT', body: { listing_ids: ids } }),
  sfAddCollection: (body, lang) => request(`/storefronts/me/collections?lang=${lang || 'sr'}`, { method: 'POST', body }),
  sfEditCollection: (id, body, lang) => request(`/storefronts/me/collections/${id}?lang=${lang || 'sr'}`, { method: 'PUT', body }),
  sfDeleteCollection: (id, lang) => request(`/storefronts/me/collections/${id}?lang=${lang || 'sr'}`, { method: 'DELETE' }),
  sfState: (body, lang) => request(`/storefronts/me/state?lang=${lang || 'sr'}`, { method: 'POST', body }),
  sfPublic: (slug, lang) => request(`/storefronts/${encodeURIComponent(slug)}?lang=${lang || 'sr'}`),
  sfByOwner: (ownerId) => request(`/storefronts/by-owner/${ownerId}`),
  chatPref: (id, action) => request(`/chats/${id}/prefs`, { method: 'POST', body: JSON.stringify({ action }) }),
  guides: (lang) => request(`/guides?lang=${lang || 'sr'}`),
  guide: (slug, lang) => request(`/guides/${slug}?lang=${lang || 'sr'}`),
  searchSuggest: (q, lang) => request(`/search/suggest?${new URLSearchParams({ q, lang: lang || 'sr' })}`),
  searchPopular: (lang) => request(`/search/popular?lang=${lang || 'sr'}`),
  searchReport: (days = 7) => request(`/search/admin-report?days=${days}`),
  sfDiscover: (params = {}) => request(`/storefronts/discover?${query(params)}`),
  sfFollow: (slug, on) => request(`/storefronts/${encodeURIComponent(slug)}/follow`, { method: on ? 'POST' : 'DELETE' }),
  sfReport: (slug, body) => request(`/storefronts/${encodeURIComponent(slug)}/report`, { method: 'POST', body }),
  // Отклики на вакансии (backend/app/routers/job_responses.py)
  jobRespond: (listingId, body) => request(`/jobs/${listingId}/respond`, { method: 'POST', body }),
  jobMyResponse: (listingId) => request(`/jobs/${listingId}/my-response`),
  jobMyResponses: () => request('/jobs/my-responses'),
  jobIncoming: () => request('/jobs/incoming'),
  jobResponses: (listingId, folder = 'new') => request(`/jobs/${listingId}/responses?folder=${folder}`),
  jobSetStatus: (id, body) => request(`/jobs/responses/${id}/status`, { method: 'POST', body }),
  // Шопсы (backend/app/routers/shops.py)
  shopsFeed: (params = {}) => request(`/shops/feed?${query(params)}`),
  shopsMine: () => request('/shops/mine'),
  shopLike: (id, on) => request(`/shops/${id}/like?on=${on ? 'true' : 'false'}`, { method: 'POST' }),
  shopComments: (id) => request(`/shops/${id}/comments`),
  shopComment: (id, text) => request(`/shops/${id}/comments`, { method: 'POST', body: { text } }),
  shopCommentDelete: (id, cid) => request(`/shops/${id}/comments/${cid}`, { method: 'DELETE' }),
  shopCommentReport: (id, cid) => request(`/shops/${id}/comments/${cid}/report`, { method: 'POST' }),
  shopGet: (id) => request(`/shops/${id}`),
  shopUpdate: (id, body) => request(`/shops/${id}`, { method: 'PUT', body }),
  shopSubmit: (id) => request(`/shops/${id}/submit`, { method: 'POST' }),
  shopRemove: (id) => request(`/shops/${id}`, { method: 'DELETE' }),
  shopEvent: (id, body) => request(`/shops/${id}/event`, { method: 'POST', body }).catch(() => null),
  shopStats: (id) => request(`/shops/${id}/stats`),
  shopCreatorApply: (body) => request('/shops/creator/apply', { method: 'POST', body }),
  shopOrders: (scope = 'open') => request(`/shops/orders/list?scope=${scope}`),
  shopOrderCreate: (body) => request('/shops/orders', { method: 'POST', body }),
  shopOrderTake: (id) => request(`/shops/orders/${id}/take`, { method: 'POST' }),
  shopOrderCancel: (id) => request(`/shops/orders/${id}/cancel`, { method: 'POST' }),
  shopAdminQueue: () => request('/shops/admin/queue'),
  shopAdminShop: (id, body) => request(`/shops/admin/shops/${id}`, { method: 'POST', body }),
  shopAdminCreator: (id, body) => request(`/shops/admin/creators/${id}`, { method: 'POST', body }),
  // Видео шопса — с ходом загрузки (XHR: у fetch нет прогресса отправки)
  shopUpload: (file, onProgress) => new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE}/shops/upload`)
    const token = getToken()
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    xhr.upload.onprogress = (e) => { if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total) }
    xhr.onload = () => {
      let data = null
      try { data = JSON.parse(xhr.responseText) } catch { /* не JSON */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data)
      else { const err = new Error(`Upload failed: ${xhr.status}`); err.code = data?.detail; reject(err) }
    }
    xhr.onerror = () => reject(new Error('network'))
    const form = new FormData()
    form.append('file', file)
    xhr.send(form)
  }),
  requestCode: (destination, channel) => request('/auth/request-code', {
    method: 'POST',
    body: JSON.stringify({ destination, channel }),
  }),
  verifyCode: (destination, code, channel, displayName) => request('/auth/verify-code', {
    method: 'POST',
    body: JSON.stringify({
      destination, code, channel, display_name: displayName,
      // Язык страницы — на нём команда напишет первое сообщение новичку.
      lang: localStorage.getItem('fino_lang') || 'sr',
      // Кто пригласил — запомнили при заходе по ссылке ?ref=<id>
      // (см. main.jsx), значение имеет смысл только для НОВОГО
      // человека, на существующий аккаунт сервер его просто не смотрит.
      referred_by: localStorage.getItem('fino_ref') || null,
    }),
  }),
  googleLogin: (credential) => request('/auth/google', {
    method: 'POST',
    body: JSON.stringify({ credential }),
  }),
  me: () => request('/auth/me'),
  deleteMe: () => request('/auth/me', { method: 'DELETE' }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  savedSearches: () => request('/saved-searches'),
  saveSearch: (filters, name) => request('/saved-searches', {
    method: 'POST',
    body: JSON.stringify({ filters, name: name || null }),
  }),
  deleteSavedSearch: (id) => request(`/saved-searches/${id}`, { method: 'DELETE' }),
  toggleSavedSearch: (id, enabled) => request(`/saved-searches/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ notify_enabled: enabled }),
  }),
  userReviews: (userId, lang, offset = 0) => request(`/reviews/user/${userId}?${new URLSearchParams({ lang: lang || 'sr', offset })}`),
  canReview: (targetId) => request(`/reviews/can-review/${targetId}`),
  dismissInvite: (chatId) => request(`/reviews/invite/${chatId}/dismiss`, { method: 'POST' }),
  createReview: (payload) => request('/reviews', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  createReport: (payload) => request('/reports', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  reportsQueue: () => request('/reports/queue'),
  resolveReport: (id, action) => request(`/reports/${id}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  }),
  // ——— админка ———
  adminUsers: (params) => request(`/admin/users?${query(params)}`),
  adminUsersOverview: () => request('/admin/users/overview'),
  adminAlerts: () => request('/admin/users/alerts'),
  adminUser: (id) => request(`/admin/users/${id}`),
  adminUserListings: (id) => request(`/admin/users/${id}/listings`),
  adminUserLogins: (id) => request(`/admin/users/${id}/logins`),
  adminUserSummary: (id) => request(`/admin/users/${id}/summary`),
  adminSetRole: (id, role) => request(`/admin/users/${id}/role`, {
    method: 'POST',
    body: JSON.stringify({ role }),
  }),
  adminVerify: (id, verified) => request(`/admin/users/${id}/verify`, { method: 'POST', body: { verified } }),
  adminBlock: (id, reason) => request(`/admin/users/${id}/block`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  }),
  adminUnblock: (id) => request(`/admin/users/${id}/unblock`, { method: 'POST' }),
  adminDeleteUser: (id) => request(`/admin/users/${id}`, { method: 'DELETE' }),
  adminResetName: (id) => request(`/admin/users/${id}/reset-name`, { method: 'POST' }),
  adminRequestReverify: (id) => request(`/verification/moderation/${id}/reverify`, { method: 'POST' }),
  // Платное продвижение объявления — три типа, оплата через ЮKassa
  // или с баланса.
  listingPromotions: (id) => request(`/listings/${id}/promotions`),
  startPromotion: (id, type, payMethod, consentImmediate = false) => request(`/listings/${id}/promotions`, {
    method: 'POST',
    body: JSON.stringify({ type, pay_method: payMethod, consent_immediate: consentImmediate }),
  }),
  getBalance: () => request('/balance'),
  startTopup: (amount) => request('/balance/topup', {
    method: 'POST',
    body: JSON.stringify({ amount }),
  }),
  adminStats: (days) => request(`/admin/stats?${new URLSearchParams({ days })}`),
  adminStatsDaily: (days) => request(`/admin/stats/daily?${new URLSearchParams({ days })}`),
  adminStatsCategories: () => request('/admin/stats/categories'),
  adminStatsSources: () => request('/admin/stats/sources'),
  adminStatsFunnel: (days) => request(`/admin/stats/funnel?${new URLSearchParams({ days })}`),
  adminStatsQuality: () => request('/admin/stats/quality'),
  adminAudit: (params) => request(`/admin/audit?${query(params)}`),
  adminAuditActors: (days) => request(`/admin/audit/actors?${new URLSearchParams({ days })}`),

  // ——— техподдержка ———
  supportCreate: (payload) => request('/support', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  supportMine: () => request('/support/mine'),
  teamChats: (params) => request(`/team/chats?${query(params)}`),
  teamChat: (id) => request(`/team/chats/${id}`),
  teamChatReply: (id, text) => request(`/team/chats/${id}/reply`, { method: 'POST', body: JSON.stringify({ text }) }),
  volunteerMine: () => request('/volunteer/mine'),
  volunteerConsent: () => request('/volunteer/consent', { method: 'POST' }),
  volunteerApply: (payload) => request('/volunteer/apply', { method: 'POST', body: JSON.stringify(payload) }),
  volunteerQueue: (params) => request(`/volunteer/queue?${query(params)}`),
  volunteerDecide: (id, payload) => request(`/volunteer/${id}/decide`, { method: 'POST', body: JSON.stringify(payload) }),
  supportReply: (id, body) => request(`/support/${id}/reply`, {
    method: 'POST', body: JSON.stringify({ body }),
  }),
  supportQueue: (params) => request(`/support/queue?${query(params)}`),
  supportTicket: (id) => request(`/support/${id}`),
  supportAnswer: (id, body) => request(`/support/${id}/answer`, {
    method: 'POST', body: JSON.stringify({ body }),
  }),
  supportClose: (id) => request(`/support/${id}/close`, { method: 'POST' }),
  myProfile: () => request('/users/me'),
  editProfile: (payload) => request('/users/me', {
    method: 'PATCH', body: JSON.stringify(payload),
  }),
  requestEmailChange: (newEmail) => request('/auth/change-email/request', {
    method: 'POST', body: JSON.stringify({ new_email: newEmail }),
  }),
  verifyEmailChange: (newEmail, code) => request('/auth/change-email/verify', {
    method: 'POST', body: JSON.stringify({ new_email: newEmail, code }),
  }),
  enterByTelegram: (key) => request('/auth/telegram/enter', {
    method: 'POST', body: JSON.stringify({ key }),
  }),

  modQueue: (lang, offset) => request(`/moderation/queue?${new URLSearchParams({ lang, offset: offset || 0 })}`),
  // Два числа для служебного раздела в профиле: сколько объявлений ждёт
  // проверки и сколько обращений без ответа.
  modCounters: () => request('/moderation/counters'),
  // Разговоры с приметами обмана — для служебного раздела.
  flaggedChats: () => request('/moderation/flagged-chats'),
  clearChatFlag: (id) => request(`/moderation/flagged-chats/${id}/clear`, { method: 'POST' }),

  modApprove: (id) => request(`/moderation/${id}/approve`, { method: 'POST' }),
  modReturn: (id) => request(`/moderation/${id}/return`, { method: 'POST' }),
  modBulk: (ids, approve, reason) => request('/moderation/bulk', {
    method: 'POST',
    body: JSON.stringify({ ids, approve, reason: reason || null }),
  }),
  modMyDay: () => request('/moderation/my-day'),
  // Перенос объявления в другой раздел — только меняет раздел, всё
  // остальное (текст, фото, автор, переписка) остаётся как было.
  modMove: (id, categoryId) => request(`/moderation/${id}/move`, {
    method: 'POST', body: JSON.stringify({ category_id: categoryId }),
  }),
  modReject: (id, reason) => request(`/moderation/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  }),
  updateMe: (payload) => request('/auth/me', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  }),

  // Дерево разделов держим в браузере.
  //
  // Оно почти не меняется, а страница раздела без него не может
  // нарисовать ни одной плитки: сперва ждём ответа сервера, потом
  // рисуем плитки, потом грузим их картинки — раздел «доезжает» на
  // глазах. Из памяти он открывается сразу.
  //
  // Держим сутки и всё равно обновляем в фоне: если разделы поменялись,
  // человек увидит новое при следующем заходе, а не будет ждать сейчас.
  // Свежие объявления для полоски «Только что» в шапке главной.
  getFresh: (city, lang) => request(`/listings/fresh?${new URLSearchParams({ lang, ...(city ? { city } : {}) })}`),

  getCategories: async () => {
    // В имени — метка сборки: после обновления сайта (слили дубли, переименовали раздел) список берётся заново,
    // а не из часового запаса на устройстве — раньше удалённые дубли ещё час висели у тех, кто уже заходил.
    // eslint-disable-next-line no-undef
    const CACHE_KEY = `plonk_categories_${typeof __BUILD__ !== 'undefined' ? __BUILD__ : 'dev'}`
    try { Object.keys(localStorage).filter((k) => k.startsWith('plonk_categories') && k !== CACHE_KEY).forEach((k) => localStorage.removeItem(k)) } catch { /* не беда */ }
    // Час, а не сутки.
    //
    // Разделы меняются редко, но когда меняются — ждать сутки нельзя:
    // завели двадцать три новых, а на сайте их не видно, и непонятно,
    // сломалось что-то или нет. Дерево весит немного, лишний запрос раз
    // в час незаметен.
    const FRESH_FOR = 60 * 60 * 1000

    let saved = null
    try {
      const raw = localStorage.getItem(CACHE_KEY)
      if (raw) saved = JSON.parse(raw)
    } catch { /* хранилище недоступно — не беда */ }

    const refresh = () => request('/categories').then((fresh) => {
      try {
        localStorage.setItem(CACHE_KEY, JSON.stringify({ at: Date.now(), tree: fresh }))
      } catch { /* не беда */ }
      return fresh
    })

    if (saved?.tree?.length) {
      const stale = Date.now() - (saved.at || 0) > FRESH_FOR
      if (!stale) return saved.tree

      // Устарело — берём свежее и показываем его.
      //
      // Раньше показывали старое, а свежее подтягивали в фоне: новые
      // разделы появлялись только со второго захода. Человек заходил,
      // не видел их и решал, что не работает.
      //
      // Если запрос не удался, показываем сохранённое: пустое дерево
      // хуже устаревшего.
      return refresh().catch(() => saved.tree)
    }
    return refresh()
  },
  getCategorySchema: (slug) => request(`/categories/${slug}/schema`),
  getCategoryIntro: (slug) => request(`/categories/${slug}/intro`),
  searchListings: (params) => request(`/listings?${query(params)}`),
  getListing: (id) => {
    // Отдаём заранее запрошенный ответ, если он есть (см. prefetchListing).
    const ready = prefetched.get(id)
    if (ready) {
      prefetched.delete(id)
      return ready
    }
    return request(`/listings/${id}`)
  },

  // Запрашиваем объявление заранее — пока палец лежит на карточке.
  //
  // Между касанием и переходом проходит 100-300 миллисекунд: человек
  // отпускает палец, срабатывает переход, рисуется страница. Если
  // начать запрос в момент касания, к открытию ответ уже готов, и
  // карточка показывается без ожидания.
  //
  // Ошибки глушим: это лишь попытка ускорить, и провалившийся запрос
  // не должен ничего ломать — обычная загрузка повторит его сама.
  prefetchListing: (id) => {
    if (!id || prefetched.has(id)) return
    prefetched.set(id, request(`/listings/${id}`).catch(() => {
      prefetched.delete(id)
      return null
    }))
    // Не копим память: держим только последние несколько.
    if (prefetched.size > 8) {
      prefetched.delete(prefetched.keys().next().value)
    }
  },
  // Тихий сигнал глубины взаимодействия — пролистал фото дальше первой
  // или развернул полное описание. Не блокирует интерфейс: ошибка
  // сети тут не должна ничего ломать, поэтому catch молча глотает её
  // в месте вызова, не здесь (см. ListingDetail.jsx).
  sendListingSignal: (id, type) => request(`/listings/${id}/signal`, {
    method: 'POST',
    body: JSON.stringify({ type }),
  }),
  getListingDashboard: (id, days) => request(`/listings/${id}/dashboard?${new URLSearchParams({ days: days || 30 })}`),
  listingsByIds: (ids, lang) => request(`/listings/by-ids?${new URLSearchParams({ ids: ids.join(','), lang })}`),
  renewListing: (id) => request(`/listings/${id}/renew`, { method: 'POST' }),
  forYou: (lang) => request(`/listings/for-you?${new URLSearchParams({ lang })}`),
  priceCheck: (id, lang) => request(`/listings/${id}/price-check?${new URLSearchParams({ lang })}`),
  similarListings: (id, lang) => request(`/listings/${id}/similar?${new URLSearchParams({ lang })}`),
  myListings: (lang) => request(`/listings/my/list?${new URLSearchParams({ lang })}`),
  sellerProfile: (userId, lang) => request(`/users/${userId}/public?${new URLSearchParams({ lang })}`),
  sellerListings: (userId, lang, offset = 0) => request(`/listings/by-seller/${userId}?${new URLSearchParams({ lang, offset })}`),
  subscribeToSeller: (userId) => request(`/users/${userId}/subscribe`, { method: 'POST' }),
  vapidPublicKey: () => request('/push/vapid-public-key'),
  pushSubscribe: (sub) => request('/push/subscribe', { method: 'POST', body: JSON.stringify(sub) }),
  pushUnsubscribe: (endpoint) => request('/push/unsubscribe', { method: 'POST', body: JSON.stringify({ endpoint }) }),
  unsubscribeFromSeller: (userId) => request(`/users/${userId}/subscribe`, { method: 'DELETE' }),
  setListingStatus: (id, status) => request(`/listings/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  }),
  deleteListing: (id, force) => request(`/listings/${id}${force ? '?force=true' : ''}`, { method: 'DELETE' }),
  updateListing: (id, payload) => request(`/listings/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  }),
  addListingPhoto: (id, payload) => request(`/listings/${id}/photos`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  deleteListingPhoto: (id, photoId) => request(`/listings/${id}/photos/${photoId}`, {
    method: 'DELETE',
  }),
  reorderListingPhotos: (id, photoIds) => request(`/listings/${id}/photos/order`, {
    method: 'PATCH',
    body: JSON.stringify({ photo_ids: photoIds }),
  }),
  createListing: (payload) => request('/listings', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  setToken,
  // Публикатор в боте: вход по подписи Telegram и быстрая публикация.
  tgWebAppAuth: (initData) => request('/tg/webapp/auth', {
    method: 'POST',
    body: JSON.stringify({ init_data: initData }),
  }),
  tgGuessCategory: (payload) => request('/tg/guess-category', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  linkTelegramStart: () => request('/users/me/link-telegram', { method: 'POST' }),
  unlinkTelegram: () => request('/users/me/link-telegram', { method: 'DELETE' }),
  tgLinkTelegram: (initData) => request('/tg/link', {
    method: 'POST',
    body: JSON.stringify({ init_data: initData }),
  }),
  tgLinkEmail: (email) => request('/tg/link-email', {
    method: 'POST',
    body: JSON.stringify({ email }),
  }),
  tgLinkEmailConfirm: (email, code) => request('/tg/link-email/confirm', {
    method: 'POST',
    body: JSON.stringify({ email, code }),
  }),
  adminSettings: () => request('/admin/settings'),
  setCardPayments: (enabled) => request('/admin/settings/card-payments', { method: 'POST', body: JSON.stringify({ enabled }) }),
  adminJobs: (days = 7) => request(`/admin/audit/jobs?days=${days}`),
  tgSiteLink: (initData, next) => request('/tg/site-link', {
    method: 'POST',
    body: JSON.stringify({ init_data: initData, next }),
  }),
  tgMyListings: (lang) => request(`/tg/my?${new URLSearchParams({ lang })}`),
  tgMarkSold: (id) => request(`/tg/my/${id}/sold`, { method: 'POST' }),
  tgRenewListing: (id) => request(`/tg/my/${id}/renew`, { method: 'POST' }),
  tgEditListing: (id, payload) => request(`/tg/my/${id}/edit`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  tgPublish: (payload) => request('/tg/publish', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  uploadPhoto: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const token = getToken()
    const res = await fetch(`${API_BASE}/media/upload`, {
      method: 'POST',
      // Тут отдельный fetch в обход request() (нельзя ставить
      // Content-Type: multipart сам браузер расставляет границы) —
      // но заголовок авторизации из-за этого тоже не долетал никогда.
      // Пока бэкенд не проверял вход, это работало по случайности.
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  },
  uploadVideo: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const token = getToken()
    const res = await fetch(`${API_BASE}/media/upload-video`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    })
    if (!res.ok) {
      const err = new Error(`Upload failed: ${res.status}`)
      try { err.code = (await res.json()).detail } catch { /* тело не JSON — код так и останется пустым */ }
      throw err
    }
    return res.json()
  },
  // Проверка документа — сторонний сервис (Didit): начинаем сессию,
  // человек снимает документ и селфи уже у них, к нам ни то ни другое
  // не попадает вовсе. Решение приходит вебхуком, статус спрашиваем
  // отдельным запросом.
  startVerification: () => request('/verification/start', { method: 'POST' }),
  getVerificationStatus: () => request('/verification/me'),
  getFavorites: (lang) => request(`/favorites?${new URLSearchParams({ lang })}`),
  getFavoriteIds: () => request('/favorites/ids'),
  addFavorite: (listingId) => request(`/favorites/${listingId}`, { method: 'POST' }),
  removeFavorite: (listingId) => request(`/favorites/${listingId}`, { method: 'DELETE' }),
  startChat: (listingId, lang) => request(`/chats/start?${new URLSearchParams({ lang })}`, {
    method: 'POST',
    body: JSON.stringify({ listing_id: listingId }),
  }),
  getChats: (lang) => request(`/chats?${new URLSearchParams({ lang })}`),
  getNotifications: (offset) => request(`/notifications?${new URLSearchParams({ offset: offset || 0 })}`),
  getNotificationsUnread: () => request('/notifications/unread-count'),
  markNotificationRead: (id) => request(`/notifications/${id}/read`, { method: 'POST' }),
  deleteNotification: (id) => request(`/notifications/${id}`, { method: 'DELETE' }),
  markAllNotificationsRead: () => request('/notifications/read-all', { method: 'POST' }),
  deleteAllNotifications: () => request('/notifications', { method: 'DELETE' }),
  markChatRead: (chatId) => request(`/chats/${chatId}/read`, { method: 'POST' }),
  blockChatPartner: (chatId) => request(`/chats/${chatId}/block`, { method: 'POST' }),
  unblockChatPartner: (chatId) => request(`/chats/${chatId}/unblock`, { method: 'POST' }),
  listBlockedUsers: () => request('/users/blocked'),
  myReferrals: () => request('/users/me/referrals'),
  waitingReviews: (lang) => request(`/reviews/waiting?${new URLSearchParams({ lang })}`),
  myStats: () => request('/users/me/stats'),
  unblockUser: (userId) => request(`/users/blocked/${userId}/unblock`, { method: 'POST' }),
  requestCall: (chatId) => request(`/chats/${chatId}/call-request`, { method: 'POST' }),
  allowCall: (chatId) => request(`/chats/${chatId}/call-allow`, { method: 'POST' }),
  declineCall: (chatId) => request(`/chats/${chatId}/call-decline`, { method: 'POST' }),
  revokeCall: (chatId) => request(`/chats/${chatId}/call-revoke`, { method: 'POST' }),
  getChat: (chatId, lang) => request(`/chats/${chatId}?${new URLSearchParams({ lang })}`),
  // Бэкенд уже отдаёт сообщения в хронологическом порядке (сортирует
  // по убыванию только для эффективной выборки последних N, потом
  // разворачивает обратно перед ответом — см. list_messages в
  // routers/chats.py). Раньше здесь стоял .reverse() — ошибка: решил,
  // что раз в запросе .desc(), то и ответ такой же, не дочитав код на
  // строку ниже. Из-за этого фронтенд переворачивал уже правильный
  // порядок в неправильный. Без разворота здесь.
  getChatMessages: (chatId, before) => request(`/chats/${chatId}/messages${before ? `?before=${encodeURIComponent(before)}` : ''}`),
  sendMessage: (chatId, text, offerPrice, replyTo) => request(`/chats/${chatId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ text: text || null, offer_price: offerPrice || null, reply_to_id: replyTo || null }),
  }),
  editMessage: (chatId, messageId, text) => request(`/chats/${chatId}/messages/${messageId}`, { method: 'PATCH', body: JSON.stringify({ text }) }),
  notifyPrefs: () => request('/users/me/notify-prefs'),
  setNotifyPrefs: (prefs) => request('/users/me/notify-prefs', { method: 'PUT', body: JSON.stringify({ prefs }) }),
  deleteMessage: (chatId, messageId) => request(`/chats/${chatId}/messages/${messageId}`, { method: 'DELETE' }),
  reactMessage: (chatId, messageId, emoji) => request(`/chats/${chatId}/messages/${messageId}/react`, { method: 'POST', body: JSON.stringify({ emoji }) }),
  translateMessage: (chatId, messageId, lang) => request(`/chats/${chatId}/messages/${messageId}/translate?lang=${lang}`, { method: 'POST' }),
  sendVoice: (chatId, blob, seconds, replyTo) => {
    const fd = new FormData()
    fd.append('file', blob, blob.type.includes('mp4') ? 'voice.m4a' : 'voice.webm')
    fd.append('seconds', String(Math.round(seconds)))
    if (replyTo) fd.append('reply_to_id', replyTo)
    return request(`/chats/${chatId}/voice`, { method: 'POST', body: fd })
  },
  respondToOffer: (chatId, messageId, status) => request(`/chats/${chatId}/offers/${messageId}/respond`, {
    method: 'POST',
    body: JSON.stringify({ status }),
  }),
  reserveListing: (listingId, buyerId, hours) => request(`/listings/${listingId}/reserve`, {
    method: 'POST',
    body: JSON.stringify({ buyer_id: buyerId, hours: hours || 48 }),
  }),
  cancelReservation: (listingId) => request(`/listings/${listingId}/reserve/cancel`, { method: 'POST' }),
}
