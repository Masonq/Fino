import { useEffect, useState } from 'react'
import { api } from '../api/client'

// Цифры в шапке главной: всего объявлений, за сутки, даром.
//
// Держим последнее значение в памяти модуля, чтобы при возврате на
// главную шапка не мигала прочерками до ответа сервера — показывается
// прошлое число, а свежее подъезжает следом. Обновляется раз в минуту,
// пока вкладка на виду: сервер всё равно отдаёт то же самое чаще.
let last = { city: null, data: null }

export default function usePulse(city) {
  const [data, setData] = useState(() => (last.city === city ? last.data : null))

  useEffect(() => {
    let alive = true
    const load = () => {
      if (document.hidden) return
      api.getPulse(city).then((d) => {
        if (!alive) return
        last = { city, data: d }
        setData(d)
      }).catch(() => {})
    }
    if (last.city === city && last.data) setData(last.data)
    load()
    const timer = setInterval(load, 60_000)
    document.addEventListener('visibilitychange', load)
    return () => { alive = false; clearInterval(timer); document.removeEventListener('visibilitychange', load) }
  }, [city])

  return data
}
