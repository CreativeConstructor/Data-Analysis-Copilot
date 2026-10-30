const API = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

async function csrfToken() {
  const response = await fetch(`${API}/csrf/`, { credentials: 'include' })
  if (!response.ok) throw new Error('Sign in to DataPilot before using the analysis workspace.')
  return (await response.json()).csrfToken
}

export async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (options.method && options.method !== 'GET') headers['X-CSRFToken'] = await csrfToken()
  if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  const response = await fetch(`${API}${path}`, { credentials: 'include', ...options, headers })
  const data = response.status === 204 ? null : await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(data?.error || data?.detail || `Request failed (${response.status}).`)
    error.status = response.status; error.data = data
    throw error
  }
  return data
}
