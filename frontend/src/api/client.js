const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export const TOKEN_KEY = 'plonk_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

async function request(path, options = {}) {
  const token = getToken()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
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

  modQueue: (lang) => request(`/moderation/queue?${new URLSearchParams({ lang })}`),
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
  createListing: (payload) => request('/listings', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  uploadPhoto: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API_BASE}/media/upload`, { method: 'POST', body: form })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  },
  getFavorites: (lang) => request(`/favorites?${new URLSearchParams({ lang })}`),
  getFavoriteIds: () => request('/favorites/ids'),
  addFavorite: (listingId) => request(`/favorites/${listingId}`, { method: 'POST' }),
  removeFavorite: (listingId) => request(`/favorites/${listingId}`, { method: 'DELETE' }),
  uploadPhoto: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API_BASE}/media/upload`, { method: 'POST', body: form })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  },
  startChat: (listingId) => request('/chats/start', {
    method: 'POST',
    body: JSON.stringify({ listing_id: listingId }),
  }),
  getChats: (lang) => request(`/chats?${new URLSearchParams({ lang })}`),
  markChatRead: (chatId) => request(`/chats/${chatId}/read`, { method: 'POST' }),
  getChat: (chatId) => request(`/chats/${chatId}`),
  getChatMessages: (chatId, before) => request(`/chats/${chatId}/messages${before ? `?before=${encodeURIComponent(before)}` : ''}`),
  sendMessage: (chatId, text) => request(`/chats/${chatId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ text }),
  }),
}
