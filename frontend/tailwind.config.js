export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        maretap: {
          // Primary accent — gold (matching Django templates)
          gold:         '#C9A84C',
          'gold-light': '#E8C97A',
          'gold-dim':   'rgba(201,168,76,0.15)',
          // Backgrounds (matching Django --dark, --dark2, --dark3, --dark4)
          dark:         '#050D18',
          dark2:        '#0A1628',
          dark3:        '#0F1F38',
          dark4:        '#162847',
          // Semantic colors
          red:          '#E05555',
          green:        '#4DAA7A',
          blue:         '#4D8FCC',
          // Keep legacy aliases so existing code doesn't break
          'red-light':  '#E74C3C',
          border:       'rgba(201,168,76,0.12)',
        },
      },
      fontFamily: {
        rajdhani: ['Rajdhani', 'sans-serif'],
        inter:    ['Inter',    'sans-serif'],
      },
    },
  },
  plugins: [],
}
