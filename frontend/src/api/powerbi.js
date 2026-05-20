import api from './axios'

export const powerbiAPI = {
  reports: ()   => api.get('/api/powerbi/reports/'),
  list:    ()   => api.get('/api/powerbi/'),
  detail:  (id) => api.get(`/api/powerbi/${id}/`),
}
