import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'

export default [
  {
    files: ['src/**/*.{js,jsx}'],
    plugins: { 'react-hooks': reactHooks },
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      // Что считать известным снаружи: window, document, fetch и прочее
      // из браузера. Без этого правило ниже ругалось бы на них как на
      // опечатки.
      globals: { ...globals.browser, ...globals.es2021 },
    },
    rules: {
      // Обращение к тому, чего нет.
      //
      // Убирая с этой страницы блок про адреса iCloud, я вырезал кусок
      // файла целиком и захватил заодно две константы. Страница входа
      // после этого падала прямо в браузере — «Can't find variable:
      // RESEND_SEC», то есть войти было нельзя вовсе.
      //
      // Ни линт, ни сборка этого не заметили: сборка проверяет
      // синтаксис, а линт до сих пор знал только правила хуков. Файл
      // синтаксически безупречен, просто половины смысла в нём нет.
      'no-undef': 'error',
      // Только правила хуков — ловят ровно тот класс ошибок, что
      // сегодня трижды подряд прошёл мимо vite build (он проверяет
      // только синтаксис, не порядок вызова хуков относительно
      // условных return или того, что объявлено раньше/позже).
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
]
