const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export const TOKEN_KEY = 'plonk_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
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

export const api = {
  requestCode: (destination, channel) => request('/auth/request-code', {
    method: 'POST',
    body: JSON.stringify({ destination, channel }),
  }),
  verifyCode: (destination, code, channel, displayName) => request('/auth/verify-code', {
    method: 'POST',
    body: JSON.stringify({ destination, code, channel, display_name: displayName }),
  }),
  loginPassword: (email, password) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  }),
  oauthLogin: (payload) => request('/auth/oauth', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  me: () => request('/auth/me'),
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
  adminUsers: (params) => request(`/admin/users?${new URLSearchParams(params)}`),
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
  // Платное продвижение объявления — три типа, оплата через ЮKassa.
  listingPromotions: (id) => request(`/listings/${id}/promotions`),
  startPromotion: (id, type) => request(`/listings/${id}/promotions`, {
    method: 'POST',
    body: JSON.stringify({ type }),
  }),
  adminStats: (days) => request(`/admin/stats?${new URLSearchParams({ days })}`),
  adminStatsDaily: (days) => request(`/admin/stats/daily?${new URLSearchParams({ days })}`),
  adminStatsCategories: () => request('/admin/stats/categories'),
  adminStatsSources: () => request('/admin/stats/sources'),
  adminStatsQuality: () => request('/admin/stats/quality'),
  adminAudit: (params) => request(`/admin/audit?${new URLSearchParams(params)}`),
  adminAuditSummary: (days) => request(`/admin/audit/summary?${new URLSearchParams({ days })}`),

  // ——— техподдержка ———
  supportCreate: (payload) => request('/support', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  supportMine: () => request('/support/mine'),
  supportReply: (id, body) => request(`/support/${id}/reply`, {
    method: 'POST', body: JSON.stringify({ body }),
  }),
  supportQueue: (params) => request(`/support/queue?${new URLSearchParams(params)}`),
  supportTicket: (id) => request(`/support/${id}`),
  supportAnswer: (id, body) => request(`/support/${id}/answer`, {
    method: 'POST', body: JSON.stringify({ body }),
  }),
  supportClose: (id) => request(`/support/${id}/close`, { method: 'POST' }),
  myProfile: () => request('/users/me'),
  editProfile: (payload) => request('/users/me', {
    method: 'PATCH', body: JSON.stringify(payload),
  }),
  enterByTelegram: (key) => request('/auth/telegram/enter', {
    method: 'POST', body: JSON.stringify({ key }),
  }),

  modQueue: (lang, offset) => request(`/moderation/queue?${new URLSearchParams({ lang, offset: offset || 0 })}`),
  modApprove: (id) => request(`/moderation/${id}/approve`, { method: 'POST' }),
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
  searchListings: (params) => request(`/listings?${new URLSearchParams(params)}`),
  getListing: (id) => request(`/listings/${id}`),
  getListingDashboard: (id, days) => request(`/listings/${id}/dashboard?${new URLSearchParams({ days: days || 30 })}`),
  listingsByIds: (ids, lang) => request(`/listings/by-ids?${new URLSearchParams({ ids: ids.join(','), lang })}`),
  similarListings: (id, lang) => request(`/listings/${id}/similar?${new URLSearchParams({ lang })}`),
  myListings: (lang) => request(`/listings/my/list?${new URLSearchParams({ lang })}`),
  sellerProfile: (userId, lang) => request(`/users/${userId}/public?${new URLSearchParams({ lang })}`),
  sellerListings: (userId, lang, offset = 0) => request(`/listings/by-seller/${userId}?${new URLSearchParams({ lang, offset })}`),
  setListingStatus: (id, status) => request(`/listings/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  }),
  deleteListing: (id) => request(`/listings/${id}`, { method: 'DELETE' }),
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
  markAllNotificationsRead: () => request('/notifications/read-all', { method: 'POST' }),
  markChatRead: (chatId) => request(`/chats/${chatId}/read`, { method: 'POST' }),
  blockChatPartner: (chatId) => request(`/chats/${chatId}/block`, { method: 'POST' }),
  unblockChatPartner: (chatId) => request(`/chats/${chatId}/unblock`, { method: 'POST' }),
  getChat: (chatId, lang) => request(`/chats/${chatId}?${new URLSearchParams({ lang })}`),
  getChatMessages: (chatId, before) => request(`/chats/${chatId}/messages${before ? `?before=${encodeURIComponent(before)}` : ''}`),
  sendMessage: (chatId, text) => request(`/chats/${chatId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ text }),
  }),
}
