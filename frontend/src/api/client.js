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
}
