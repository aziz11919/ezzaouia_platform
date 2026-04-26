import api from './axios'

export const libraryAPI = {
  list:   (params = {}) => api.get('/api/library/documents/', { params }),
  remove: (id)          => api.post(`/api/library/documents/${id}/delete/`),
}
