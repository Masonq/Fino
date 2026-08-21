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
  userReviews: (userId) => request(`/reviews/user/${userId}`),
  canReview: (targetId) => request(`/reviews/can-review/${targetId}`),
  dismissInvite: (chatId) => request(`/reviews/invite/${chatId}/dismiss`, { method: 'POST' }),
  createReview: (payload) => request('/reviews', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
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
  myListings: (lang) => request(`/listings/my/list?${new URLSearchParams({ lang })}`),
  setListingStatus: (id, status) => request(`/listings/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  }),
  deleteListing: (id) => request(`/listings/${id}`, { method: 'DELETE' }),
  quickIdentify: (phone, displayName) => request('/users/quick', {
    method: 'POST',
    body: JSON.stringify({ phone, display_name: displayName }),
  }),
  createListing: (payload, ownerId) => request(`/listings?${new URLSearchParams({ owner_id: ownerId })}`, {
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
  getFavorites: (userId, lang) => request(`/favorites?${new URLSearchParams({ user_id: userId, lang })}`),
  getFavoriteIds: (userId) => request(`/favorites/ids?${new URLSearchParams({ user_id: userId })}`),
  addFavorite: (listingId, userId) => request(`/favorites/${listingId}?${new URLSearchParams({ user_id: userId })}`, { method: 'POST' }),
  removeFavorite: (listingId, userId) => request(`/favorites/${listingId}?${new URLSearchParams({ user_id: userId })}`, { method: 'DELETE' }),
  uploadPhoto: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API_BASE}/media/upload`, { method: 'POST', body: form })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  },
  startChat: (listingId, buyerId) => request('/chats/start', {
    method: 'POST',
    body: JSON.stringify({ listing_id: listingId, buyer_id: buyerId }),
  }),
  getChats: (userId, lang) => request(`/chats?${new URLSearchParams({ user_id: userId, lang })}`),
  markChatRead: (chatId, userId) => request(`/chats/${chatId}/read?${new URLSearchParams({ user_id: userId })}`, { method: 'POST' }),
  getChat: (chatId) => request(`/chats/${chatId}`),
  getChatMessages: (chatId) => request(`/chats/${chatId}/messages`),
  sendMessage: (chatId, senderId, text) => request(`/chats/${chatId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ sender_id: senderId, text }),
  }),
}
