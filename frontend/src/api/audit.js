import api from './axios'

export const auditAPI = {
  list: (params = {}) => api.get('/api/audit/logs/', { params }),
}
