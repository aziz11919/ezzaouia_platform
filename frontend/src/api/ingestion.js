import api from './axios'

export const ingestionAPI = {
  getRecentFiles: ()         => api.get('/ingestion/recent/'),
  upload:         (formData) => api.post('/ingestion/api-upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  getStatus:      (fileId)   => api.get(`/ingestion/api-status/${fileId}/`),
}
