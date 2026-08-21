const API_BASE = import.meta.env.VITE_API_BASE || '/api'

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  getCategories: () => request('/categories'),
  getCategorySchema: (slug) => request(`/categories/${slug}/schema`),
  searchListings: (params) => request(`/listings?${new URLSearchParams(params)}`),
  getListing: (id) => request(`/listings/${id}`),
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
  startChat: (listingId, buyerId) => request('/chats/start', {
    method: 'POST',
    body: JSON.stringify({ listing_id: listingId, buyer_id: buyerId }),
  }),
  getChat: (chatId) => request(`/chats/${chatId}`),
  getChatMessages: (chatId) => request(`/chats/${chatId}/messages`),
  sendMessage: (chatId, senderId, text) => request(`/chats/${chatId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ sender_id: senderId, text }),
  }),
}
