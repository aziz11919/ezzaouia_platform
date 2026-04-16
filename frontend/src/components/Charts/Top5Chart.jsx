import { useEffect, useRef } from 'react'
import { loadChartJs } from '../../utils/chartjsLoader'

const WELL_COLORS = ['#FF4444', '#FF8C00', '#FFD700', '#00BFFF', '#00FF7F']

export default function Top5Chart({ labels = [], data = [] }) {
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

      chartRef.current = new Chart(canvasRef.current, {
        type: 'bar',
        data: {
          labels,
          datasets: [
            {
              label: 'BOPD moyen',
              data,
              backgroundColor: WELL_COLORS.slice(0, labels.length),
              borderRadius: 4,
              barThickness: 22,
            },
          ],
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
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
              grid: { display: false },
              ticks: {
                color: '#FFF',
                font: { family: "'Rajdhani', sans-serif", size: 13, weight: 'bold' },
              },
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
  }, [labels, data])

  return (
    <div style={{ position: 'relative', height: 240 }}>
      <canvas ref={canvasRef} />
    </div>
  )
}
