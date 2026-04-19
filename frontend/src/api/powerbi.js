import api from './axios'

export const powerbiAPI = {
  list:   ()   => api.get('/api/powerbi/'),
  detail: (id) => api.get(`/api/powerbi/${id}/`),
}
