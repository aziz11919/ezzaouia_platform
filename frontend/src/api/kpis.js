import api from './axios'

export const kpisAPI = {
  getSummary: (year) => api.get(`/api/kpis/summary/${year ? `?year=${year}` : ''}`),
  getTrend: (year) => api.get(`/api/kpis/trend/${year ? `?year=${year}` : ''}`),
  getTopProducers: (year) => api.get(`/api/kpis/top-producers/${year ? `?year=${year}` : ''}`),
}
