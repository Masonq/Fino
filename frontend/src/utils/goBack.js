/**
 * «Назад» внутри сайта: если человек пришёл сюда по прямой ссылке (из Telegram, из поиска), истории внутри сайта
 * нет — navigate(-1) уводил со страницы в пустоту (белый экран или чужой сайт). Тогда ведём в осмысленное место.
 * window.history.state.idx — номер шага внутри сайта, его ставит React Router.
 */
export function goBack(navigate, fallback = '/') {
  if (window.history.state?.idx > 0) navigate(-1)
  else navigate(fallback, { replace: true })
}
