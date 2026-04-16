import { useEffect, useRef } from 'react'
import { loadChartJs } from '../../utils/chartjsLoader'

export default function TrendChart({ labels = [], oilData = [], bswData = [] }) {
  const canvasRef = useRef(null)
  const chartRef = useRef(null)

  useEffect(() => {
    let mounted = true

    async function render() {
      const Chart = await loadChartJs()
      if (!mounted || !Chart || !canvasRef.current) return

      if (chartRef.current) {
        chartRef.current.destroy()
        chartRef.current = null
      }

      Chart.defaults.font.family = "'Inter', sans-serif"
      Chart.defaults.font.size = 11
      Chart.defaults.color = '#6B85A8'

      chartRef.current = new Chart(canvasRef.current, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: 'Huile (STB)',
              data: oilData,
              borderColor: '#FF6B35',
              backgroundColor: 'rgba(255,107,53,0.1)',
              borderWidth: 2,
              pointRadius: 3,
              pointBackgroundColor: '#FF6B35',
              tension: 0.4,
              fill: true,
              yAxisID: 'y',
            },
            {
              label: 'BSW %',
              data: bswData,
              borderColor: '#FFD700',
              backgroundColor: 'rgba(255,215,0,0.08)',
              borderWidth: 2,
              borderDash: [5, 5],
              pointRadius: 3,
              pointBackgroundColor: '#FFD700',
              tension: 0.4,
              fill: false,
              yAxisID: 'y1',
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                color: '#9CAAC4',
                boxWidth: 14,
                padding: 20,
                usePointStyle: true,
              },
            },
            tooltip: {
              backgroundColor: '#0A1628',
              borderColor: 'rgba(201,168,76,0.2)',
              borderWidth: 1,
              titleColor: '#9CAAC4',
              bodyColor: '#E8EEF8',
              padding: 10,
            },
          },
          scales: {
            x: {
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { color: '#AAA' },
            },
            y: {
              position: 'left',
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { color: '#FF6B35' },
              title: { display: true, text: 'Huile (STB)', color: '#FF6B35', font: { size: 10 } },
            },
            y1: {
              position: 'right',
              grid: { drawOnChartArea: false },
              min: 0,
              max: 100,
              ticks: { color: '#FFD700', callback: (v) => `${v}%` },
              title: { display: true, text: 'BSW %', color: '#FFD700', font: { size: 10 } },
            },
          },
        },
      })
    }

    render()

    return () => {
      mounted = false
      if (chartRef.current) {
        chartRef.current.destroy()
        chartRef.current = null
      }
    }
  }, [labels, oilData, bswData])

  return (
    <div style={{ position: 'relative', height: 240 }}>
      <canvas ref={canvasRef} />
    </div>
  )
}
