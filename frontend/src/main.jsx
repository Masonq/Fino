import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './i18n'
import App from './App.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import './styles.css'

// Языковые адреса: /en/... и /sr/... Русский живёт без приставки —
// он основной, и ломать существующие ссылки на него нельзя.
//
// Зачем вообще: поисковику нужен отдельный адрес на каждый язык. Пока
// все три жили по одному адресу, серб и англичанин находили в выдаче
// русскую страницу — а это половина людей в Белграде.
//
// Приставку снимаем здесь и отдаём роутеру как basename: тогда все
// ссылки внутри приложения получают её сами, и ни одну из них не
// нужно переписывать.
const LANG_PREFIXES = ['en', 'sr']
const first = window.location.pathname.split('/')[1]
const urlLang = LANG_PREFIXES.includes(first) ? first : null
const basename = urlLang ? `/${urlLang}` : '/'
if (urlLang) {
  // Адрес главнее сохранённого выбора: человек пришёл по ссылке из
  // выдачи или от знакомого именно на этом языке.
  // Язык из адреса догружается тем же способом — сам i18n уже знает,
  // что делать (см. i18n/index.js), поэтому здесь только сохраняем выбор.
  try { localStorage.setItem('fino_lang', urlLang) } catch { /* не беда */ }
}

// _v в адресе — только чтобы протолкнуть перезагрузку мимо кэша
// Safari (см. index.html), самому React Router он не нужен и не
// должен туда попасть: убираем ДО того, как BrowserRouter вообще
// прочитает URL, а не после — иначе его внутреннее представление
// адреса разойдётся с тем, что реально в строке браузера.
try {
  const u = new URL(window.location.href)
  let changed = false

  // Реферальная ссылка — plonk.rs/?ref=<id пригласившего>. Запоминаем
  // на телефоне сразу при заходе, используем только при последующей
  // регистрации (см. api.verifyCode в client.js) — большинство перейдёт
  // по ссылке, но зарегистрируется не в ту же секунду. Новый переход
  // по чужой ссылке перезаписывает старую — последняя выигрывает.
  const ref = u.searchParams.get('ref')
  if (ref) {
    try { localStorage.setItem('fino_ref', ref) } catch { /* недоступен — просто без реферала */ }
    u.searchParams.delete('ref')
    changed = true
  }

  if (u.searchParams.has('_v')) {
    u.searchParams.delete('_v')
    changed = true
  }
  if (changed) window.history.replaceState({}, '', u.pathname + u.search + u.hash)
} catch { /* всё равно ничего не сломает, просто параметры останутся в строке */ }

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter basename={basename}>
        <App />
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>,
)
