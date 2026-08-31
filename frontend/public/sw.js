// Service worker только ради Web Push — никакого офлайн-кэширования
// страниц тут нет и не должно быть: сайт живой, объявления меняются
// поминутно, кэшировать HTML/данные значило бы показывать устаревшее.
// Единственная задача — принять пуш, пока сайт закрыт, и показать
// системное уведомление.

self.addEventListener('push', (event) => {
  let data = { title: 'PLONK', body: '', link: '/' }
  try {
    if (event.data) data = { ...data, ...event.data.json() }
  } catch { /* пришло не JSON — покажем как есть с заголовком по умолчанию */ }

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      data: { link: data.link || '/' },
    })
  )
})

// Тап по уведомлению — открыть сайт на нужной странице, а если вкладка
// с ним уже открыта где-то — переиспользовать её, а не плодить новую.
self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const link = event.notification.data?.link || '/'

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const client of list) {
        if ('focus' in client) {
          client.navigate(link)
          return client.focus()
        }
      }
      return self.clients.openWindow(link)
    })
  )
})
