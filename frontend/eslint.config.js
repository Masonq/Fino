import reactHooks from 'eslint-plugin-react-hooks'

export default [
  {
    files: ['src/**/*.{js,jsx}'],
    plugins: { 'react-hooks': reactHooks },
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      // Только правила хуков — ловят ровно тот класс ошибок, что
      // сегодня трижды подряд прошёл мимо vite build (он проверяет
      // только синтаксис, не порядок вызова хуков относительно
      // условных return или того, что объявлено раньше/позже).
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
]
