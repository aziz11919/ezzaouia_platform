import api from './axios'

const AUTH_BASE = '/accounts'

export const authAPI = {
  me: () => api.get(`${AUTH_BASE}/me/`),
  login: (data) => api.post(`${AUTH_BASE}/login/`, data),
  logout: () => api.post(`${AUTH_BASE}/logout/`),
  changePassword: (data) => api.post(`${AUTH_BASE}/api-change-password/`, data),
  updateProfile: (data) => api.post(`${AUTH_BASE}/api-profile/`, data),
  listUsers: (params = {}) => api.get(`${AUTH_BASE}/users-api/`, { params }),
  toggleUser: (userId) => api.post(`${AUTH_BASE}/users-api/${userId}/toggle/`),
  deleteUser: (userId) => api.post(`${AUTH_BASE}/users-api/${userId}/delete/`),
  forgotPassword: (data) => api.post(`${AUTH_BASE}/api-forgot-password/`, data),
  validateResetToken: (token) => api.get(`${AUTH_BASE}/api-reset-password/${token}/`),
  resetPassword: (token, data) => api.post(`${AUTH_BASE}/api-reset-password/${token}/`, data),
  createUser: (data) => api.post(`${AUTH_BASE}/api-create-user/`, data),
  getUser: (userId) => api.get(`${AUTH_BASE}/users-api/${userId}/detail/`),
  editUser: (userId, data) => api.post(`${AUTH_BASE}/users-api/${userId}/edit/`, data),
  adminResetPassword: (userId, data) => api.post(`${AUTH_BASE}/users-api/${userId}/reset-password/`, data),
}
