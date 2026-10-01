/*
 * Подтверждение действия — шторкой снизу, а не window.confirm.
 *
 *   if (!(await confirmSheet({ title: t('my.confirm_delete'), confirm: t('confirm.delete'), danger: true }))) return
 *
 * Почему не window.confirm: в приложении с главного экрана iPhone и во встроенных браузерах (Telegram, Instagram)
 * системные окна бывают подавлены и молча отвечают «нет» — кнопка «Удалить» тогда просто ничего не делала.
 * Рисует шторку components/ConfirmHost.jsx (подключён в App). Если его на странице нет — честно падаем обратно на
 * системное окно, чтобы вопрос не повис без ответа.
 */
export function confirmSheet({ title, text = '', confirm = '', cancel = '', danger = false }) {
  if (!window.__plonkConfirmReady) return Promise.resolve(window.confirm(title))
  return new Promise((resolve) => {
    window.dispatchEvent(new CustomEvent('plonk:confirm', { detail: { title, text, confirm, cancel, danger, resolve } }))
  })
}
