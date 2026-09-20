import { api } from '../api/client'

// applicationServerKey должен быть Uint8Array, а с сервера ключ приходит
// текстом (base64url без паддинга, как его и генерирует VAPID) —
// стандартное преобразование одного в другое.
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = window.atob(base64)
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)))
}

export function pushSupported() {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

// iOS даёт доступ к Push API только сайту, добавленному на главный
// экран и открытому оттуда (отдельным «приложением», без адресной
// строки Safari) — в обычной вкладке PushManager нет физически,
// ни один сайт это не обходит. Отличаем этот случай от настоящего
// «браузер/ОС слишком старая»: тут есть понятное действие (добавить
// на главный экран), там — нет.

export function pushPermission() {
  return pushSupported() ? Notification.permission : 'unsupported'
}

// Уже подписан ли ЭТОТ браузер — не путать с «включены ли пуши у
// аккаунта вообще»: у человека может быть подписка с телефона, а
// спрашиваем мы состояние именно этого устройства.
export async function isPushSubscribed() {
  if (!pushSupported()) return false
  const reg = await navigator.serviceWorker.getRegistration('/sw.js')
  if (!reg) return false
  const sub = await reg.pushManager.getSubscription()
  return !!sub
}

export async function enablePush() {
  if (!pushSupported()) throw new Error('unsupported')

  const permission = await Notification.requestPermission()
  if (permission !== 'granted') throw new Error('denied')

  const reg = await navigator.serviceWorker.register('/sw.js')
  await navigator.serviceWorker.ready

  const { key } = await api.vapidPublicKey()
  if (!key) throw new Error('no_key')

  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(key),
  })
  const json = sub.toJSON()
  await api.pushSubscribe({
    endpoint: json.endpoint,
    p256dh: json.keys.p256dh,
    auth: json.keys.auth,
  })
  return true
}

export async function disablePush() {
  if (!pushSupported()) return
  const reg = await navigator.serviceWorker.getRegistration('/sw.js')
  if (!reg) return
  const sub = await reg.pushManager.getSubscription()
  if (!sub) return
  const endpoint = sub.endpoint
  await sub.unsubscribe()
  try { await api.pushUnsubscribe(endpoint) } catch { /* браузер уже отписан — на сервере само отвалится по 410 при следующей попытке */ }
}
