import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './i18n'
import App from './App.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
// Onest — свой шрифт с сайта (кириллица + латиница), без запроса к Google: быстрее и не зависит от их доступности
import '@fontsource/onest/400.css'
import '@fontsource/onest/500.css'
import '@fontsource/onest/600.css'
import '@fontsource/onest/700.css'
import '@fontsource/onest/800.css'
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
// Кусок кода страницы не загрузился — «Importing a module script
// failed». Так бывает у вкладки, открытой до выкладки: она просит файл
// по старому имени, а на сервере уже новые. Перезагружаем страницу —
// придёт свежий index.html с правильными именами. Один раз в минуту,
// чтобы при настоящей поломке не устроить бесконечный круг.
function reloadOnceAfterFailedChunk() {
  const KEY = 'plonk_chunk_reload_at'
  let last = 0
  try { last = Number(sessionStorage.getItem(KEY) || 0) } catch { /* приватный режим */ }
  if (Date.now() - last < 60000) return
  try { sessionStorage.setItem(KEY, String(Date.now())) } catch { /* не беда */ }
  window.location.reload()
}

window.addEventListener('vite:preloadError', (event) => {
  event.preventDefault()
  reloadOnceAfterFailedChunk()
})

window.addEventListener('unhandledrejection', (event) => {
  const text = String(event.reason?.message || event.reason || '')
  if (/Importing a module script failed|Failed to fetch dynamically imported module|error loading dynamically imported module/i.test(text)) {
    reloadOnceAfterFailedChunk()
  }
})

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
