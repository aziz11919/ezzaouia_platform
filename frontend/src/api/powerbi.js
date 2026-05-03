import api from './axios'

export const powerbiAPI = {
  reports: ()   => api.get('/api/powerbi/reports/'),
  list:    ()   => api.get('/api/powerbi/'),
  detail:  (id) => api.get(`/api/powerbi/${id}/`),
  create:  (data) => api.post('/api/powerbi/create/', data),
  update:  (id, data) => api.patch(`/api/powerbi/${id}/update/`, data),
  remove:  (id) => api.delete(`/api/powerbi/${id}/delete/`),
}
