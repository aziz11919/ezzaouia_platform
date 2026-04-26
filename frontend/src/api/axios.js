import axios from 'axios'

const api = axios.create({
  baseURL: '',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// Ajouter CSRF token automatiquement
api.interceptors.request.use(config => {
  const csrfToken = document.cookie
    .split(';')
    .find(c => c.trim().startsWith('csrftoken='))
    ?.split('=')[1]
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken
  }
  return config
})

// Rediriger vers /login si 401 — SAUF pour /accounts/me/ qui est le check
// initial de session (AuthContext gère lui-même le 401 via .catch).
// Évite la boucle infinie : me() → 401 → redirect → me() → ...
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      const url = error.config?.url || ''
      if (!url.includes('/accounts/me/')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
