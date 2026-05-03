import api from './axios'

export const maintenanceAPI = {
  status: () => api.get('/api/maintenance/status/'),
  toggle: (data) => api.post('/api/maintenance/toggle/', data),
}
