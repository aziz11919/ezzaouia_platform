import api from './axios'

export const ingestionAPI = {
  getRecentFiles: ()         => api.get('/ingestion/recent/'),
  upload:         (formData) => api.post('/ingestion/api-upload/', formData),
  getStatus:      (fileId)   => api.get(`/ingestion/api-status/${fileId}/`),
}
