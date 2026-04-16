let chartLoader

export function loadChartJs() {
  if (typeof window === 'undefined') return Promise.resolve(null)
  if (window.Chart) return Promise.resolve(window.Chart)
  if (chartLoader) return chartLoader

  chartLoader = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'
    script.async = true
    script.onload = () => resolve(window.Chart)
    script.onerror = () => reject(new Error('Failed to load Chart.js'))
    document.head.appendChild(script)
  })

  return chartLoader
}
