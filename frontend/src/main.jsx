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
  if (u.searchParams.has('_v')) {
    u.searchParams.delete('_v')
    window.history.replaceState({}, '', u.pathname + u.search + u.hash)
  }
} catch { /* всё равно ничего не сломает, просто параметр останется в строке */ }

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>,
)
