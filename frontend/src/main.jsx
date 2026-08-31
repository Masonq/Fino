import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './i18n'
import App from './App.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import './styles.css'

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
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>,
)
