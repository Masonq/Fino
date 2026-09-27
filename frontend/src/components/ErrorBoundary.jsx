import { Component } from 'react'

/**
 * Без этого — любая необработанная ошибка рендера стирает всё дерево
 * React целиком, и человек видит просто пустой экран, без единого
 * слова о том, что случилось. React Error Boundary умеет ловить такое
 * только через классовый компонент — хуками (componentDidCatch,
 * getDerivedStateFromError) это не делается в принципе.
 *
 * Показываем не техническую стену текста по умолчанию, а понятный
 * человеку экран с кнопкой «Обновить» — и рядом техническую строку
 * помельче, специально для того, чтобы прислать её мне при жалобе,
 * а не гадать по одному только «пустая страница».
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    // В консоль браузера — на компьютере это видно через инструменты
    // разработчика, на телефоне толку меньше, но пусть будет.
    console.error('ErrorBoundary поймал:', error, info)

    // Не загрузился кусок кода страницы — это не поломка приложения, а
    // вкладка, открытая до выкладки: она просит файлы по старым
    // именам. Показывать ей «что-то пошло не так» незачем,
    // перезагружаемся сами (один раз в минуту, см. main.jsx).
    const text = String(error?.message || error || '')
    if (/Importing a module script failed|dynamically imported module/i.test(text)) {
      const KEY = 'plonk_chunk_reload_at'
      let last = 0
      try { last = Number(sessionStorage.getItem(KEY) || 0) } catch { /* приватный режим */ }
      if (Date.now() - last > 60000) {
        try { sessionStorage.setItem(KEY, String(Date.now())) } catch { /* не беда */ }
        window.location.reload()
      }
    }
  }

  render() {
    if (!this.state.error) return this.props.children

    const message = this.state.error?.message || String(this.state.error)
    const stack = this.state.error?.stack || ''

    return (
      <div style={{
        minHeight: '100vh', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', padding: '32px 20px',
        textAlign: 'center', fontFamily: '-apple-system, sans-serif', background: 'var(--bg, #F6F6F2)', color: 'var(--ink, #1C2620)',
      }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>⚠️</div>
        <div style={{ fontSize: 17, fontWeight: 800, color: '#1C2620', marginBottom: 6 }}>
          Что-то пошло не так
        </div>
        <div style={{ fontSize: 13.5, color: '#8A9088', marginBottom: 20, maxWidth: 320 }}>
          Страница не смогла открыться. Попробуйте обновить — если повторится,
          пришлите текст ниже.
        </div>
        <button
          onClick={() => window.location.reload()}
          style={{
            padding: '12px 24px', borderRadius: 12, background: '#0E9F6E',
            color: '#fff', fontWeight: 700, fontSize: 14, border: 'none', marginBottom: 24,
          }}
        >
          Обновить страницу
        </button>
        <details style={{ maxWidth: '100%', width: 340 }}>
          <summary style={{ fontSize: 12, color: '#B8BDB6', cursor: 'pointer' }}>
            Техническая информация
          </summary>
          <pre style={{
            marginTop: 10, padding: 10, background: 'var(--card, #fff)', borderRadius: 10,
            fontSize: 10.5, color: '#1C2620', textAlign: 'left', overflowX: 'auto',
            whiteSpace: 'pre-wrap', wordBreak: 'break-word', border: '1px solid rgba(20,30,25,.08)',
          }}>
            {message}
            {'\n\n'}
            {stack}
          </pre>
        </details>
      </div>
    )
  }
}
