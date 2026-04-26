import api from './axios'

export const chatbotAPI = {
  getSessions:      ()              => api.get('/chatbot/sessions/'),
  getMessages:      (sessionId)     => api.get(`/chatbot/session/${sessionId}/messages/`),
  ask:              (payload)       => api.post('/chatbot/ask/', payload),
  upload:           (formData)      => api.post('/chatbot/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  deleteSession:    (id)            => api.post(`/chatbot/session/${id}/delete/`),
  newSession:       ()              => api.post('/chatbot/new/'),
  renameSession:    (id, title)     => api.post(`/chatbot/session/${id}/rename/`, { title }),
  shareWithUsers:   (id, userIds)   => api.post(`/chatbot/share/${id}/`, { user_ids: userIds }),
  stopGeneration:   ()              => api.post('/chatbot/stop/'),
  getSuggestions:   ()              => api.get('/chatbot/morning-suggestions/'),
  rate:             (data)          => api.post('/chatbot/rate/', data),
  addComment:       (data)          => api.post('/chatbot/add-comment/', data),
  getComments:      (messageId)     => api.get(`/chatbot/comments/${messageId}/`),
  getStats:         ()              => api.get('/chatbot/api/stats/'),
  getUsers:         ()              => api.get('/chatbot/users/'),
  getSharedWithMe:  ()              => api.get('/chatbot/shared-with-me/'),
}
