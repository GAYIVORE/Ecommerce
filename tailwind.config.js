/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './apps/**/templates/**/*.html',
  ],
  safelist: [
    // Dynamic coupon banner colors are set inline from the DB, everything else is static.
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#14151C',
          900: '#14151C',
          800: '#1D1F2B',
          700: '#2A2C3D',
        },
        brand: {
          DEFAULT: '#28338A',
          50: '#EEF0FB',
          100: '#D8DCF3',
          200: '#B2B9E8',
          400: '#4B57AD',
          500: '#28338A',
          600: '#212B72',
          700: '#1A2259',
        },
        marigold: {
          DEFAULT: '#F2A310',
          50: '#FEF6E6',
          100: '#FCE9BF',
          400: '#F5B733',
          500: '#F2A310',
          600: '#CC8600',
          700: '#996500',
        },
        papaya: {
          DEFAULT: '#F2542D',
          50: '#FEEEEA',
          100: '#FBD1C3',
          500: '#F2542D',
          600: '#D93F1B',
          700: '#B23315',
        },
        jade: {
          DEFAULT: '#0E9F6E',
          50: '#E7F9F2',
          100: '#C3F0DE',
          500: '#0E9F6E',
          600: '#0B8059',
          700: '#086249',
        },
        paper: '#F7F7F4',
        line: '#E7E5DE',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        body: ['"Inter"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(20,21,28,0.04), 0 8px 24px -12px rgba(20,21,28,0.12)',
        lift: '0 4px 8px rgba(20,21,28,0.06), 0 16px 32px -16px rgba(20,21,28,0.22)',
      },
      borderRadius: {
        xl2: '1.25rem',
      },
    },
  },
  plugins: [],
}
