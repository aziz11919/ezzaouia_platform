import api from './axios'

export const forecastingAPI = {
  getField: (kpi, periods) =>
    api.get(`/api/forecasting/field/?kpi=${kpi}&periods=${periods}`),
  getWell: (wellKey, kpi, periods) =>
    api.get(`/api/forecasting/well/${wellKey}/?kpi=${kpi}&periods=${periods}`),
  getAllWells: (kpi) =>
    api.get(`/api/forecasting/wells/?kpi=${kpi}`),
  getWellList: () =>
    api.get('/api/forecasting/well-list/'),
}
