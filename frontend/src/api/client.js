const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export const TOKEN_KEY = 'plonk_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
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
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
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
  requestCode: (destination, channel) => request('/auth/request-code', {
    method: 'POST',
    body: JSON.stringify({ destination, channel }),
  }),
  verifyCode: (destination, code, channel, displayName) => request('/auth/verify-code', {
    method: 'POST',
    body: JSON.stringify({
      destination, code, channel, display_name: displayName,
      // Кто пригласил — запомнили при заходе по ссылке ?ref=<id>
      // (см. main.jsx), значение имеет смысл только для НОВОГО
      // человека, на существующий аккаунт сервер его просто не смотрит.
      referred_by: localStorage.getItem('fino_ref') || null,
    }),
  }),
  oauthLogin: (payload) => request('/auth/oauth', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  me: () => request('/auth/me'),
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
  userReviews: (userId, lang, offset = 0) => request(`/reviews/user/${userId}?${new URLSearchParams({ lang: lang || 'ru', offset })}`),
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
  adminUser: (id) => request(`/admin/users/${id}`),
  adminUserListings: (id) => request(`/admin/users/${id}/listings`),
  adminUserLogins: (id) => request(`/admin/users/${id}/logins`),
  adminUserSummary: (id) => request(`/admin/users/${id}/summary`),
  adminSetRole: (id, role) => request(`/admin/users/${id}/role`, {
    method: 'POST',
    body: JSON.stringify({ role }),
  }),
  adminBlock: (id, reason) => request(`/admin/users/${id}/block`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  }),
  adminUnblock: (id) => request(`/admin/users/${id}/unblock`, { method: 'POST' }),
  adminRequestReverify: (id) => request(`/verification/moderation/${id}/reverify`, { method: 'POST' }),
  // Платное продвижение объявления — три типа, оплата через ЮKassa
  // или с баланса.
  listingPromotions: (id) => request(`/listings/${id}/promotions`),
  startPromotion: (id, type, payMethod) => request(`/listings/${id}/promotions`, {
    method: 'POST',
    body: JSON.stringify({ type, pay_method: payMethod }),
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
  adminStatsQuality: () => request('/admin/stats/quality'),
  adminAudit: (params) => request(`/admin/audit?${query(params)}`),
  adminAuditSummary: (days) => request(`/admin/audit/summary?${new URLSearchParams({ days })}`),

  // ——— техподдержка ———
  supportCreate: (payload) => request('/support', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  supportMine: () => request('/support/mine'),
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
  modApprove: (id) => request(`/moderation/${id}/approve`, { method: 'POST' }),
  // Перенос объявления в другой раздел — только меняет раздел, всё
  // остальное (текст, фото, автор, переписка) остаётся как было.
  modMove: (id, categoryId) => request(`/moderation/${id}/move`, {
    method: 'POST', body: { category_id: categoryId },
  }),
  modReject: (id, reason) => request(`/moderation/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  }),
  updateMe: (payload) => request('/auth/me', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  }),

  getCategories: () => request('/categories'),
  getCategorySchema: (slug) => request(`/categories/${slug}/schema`),
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
  sendMessage: (chatId, text, offerPrice) => request(`/chats/${chatId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ text: text || null, offer_price: offerPrice || null }),
  }),
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
