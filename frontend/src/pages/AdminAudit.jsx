import { intlLocale } from '../utils/time'
import { useCallback, useEffect, useRef, useState } from 'react'
import { keepValue, readValue, useKeepPlace } from '../utils/keepPlace'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import { AuditRowSkeletons } from '../components/Skeletons'

const FILTERS = [
  { key: '', label: 'audit.all' },
  { key: 'user', label: 'audit.about_people' },
  { key: 'listing', label: 'audit.about_listings' },
]

// Служебные записи (ночные скрипты, перенос из чатов, переписывание
// заголовков) идут без сотрудника: за сутки их сотни против десятка
// решений человека, и в общем списке решения в них тонут. Показываем
// людей, служебное — отдельной вкладкой.
const KINDS = ['staff', 'system']

// Час и минута важнее даты: смотрят журнал обычно сразу после события.
function when(iso, locale) {
  if (!iso) return ''
  const date = new Date(iso)
  const today = new Date()
  const sameDay = date.toDateString() === today.toDateString()
  return sameDay
    ? date.toLocaleTimeString(intlLocale(locale), { hour: '2-digit', minute: '2-digit' })
    : date.toLocaleString(intlLocale(locale), {
      day: '2-digit', month: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
}

// Время без даты: дата написана один раз над днём.
function timeOnly(iso, lang) {
  try {
    return new Date(iso).toLocaleTimeString(intlLocale(lang || 'ru'), { hour: '2-digit', minute: '2-digit' })
  } catch { return '' }
}

// Записи по дням: «Сегодня», «Вчера», дальше числом. Человек ищет в
// журнале «что было вчера», а не «что было восемнадцатого».
function groupByDay(items, lang) {
  const days = new Map()
  const today = new Date().toDateString()
  const yesterday = new Date(Date.now() - 86400000).toDateString()

  for (const row of items) {
    const date = new Date(row.created_at)
    const key = date.toDateString()
    const title = key === today ? 'Сегодня'
      : key === yesterday ? 'Вчера'
        : date.toLocaleDateString(intlLocale(lang || 'ru'), { day: 'numeric', month: 'long' })
    if (!days.has(title)) days.set(title, [])
    days.get(title).push(row)
  }
  return [...days.entries()]
}

export default function AdminAudit() {
  // Возвращаемся туда, где человек оставил список.
  useKeepPlace('admin-audit')
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  // Отбор держится между заходами: модератор выбирает «служебные,
  // по объявлениям», уходит в карточку и, вернувшись, получал заново
  // «сотрудники, все» — и выставлял то же самое каждый раз.
  const [filter, setFilter] = useState(() => readValue('audit-filter', ''))
  const [actor, setActor] = useState(() => readValue('audit-actor', ''))
  const [actors, setActors] = useState([])
  const [actorsLoaded, setActorsLoaded] = useState(false)      // пока не пришёл ответ, место под сводку по людям держим
  const [loaded, setLoaded] = useState(false)
  const [denied, setDenied] = useState(false)
  const [kind, setKind] = useState(() => readValue('audit-kind', 'staff'))

  // Запоминаем выбор ПОСЛЕ того, как все состояния объявлены: иначе
  // эффект ссылается на kind, объявленный ниже, и страница падает с
  // «Cannot access before initialization».
  useEffect(() => { keepValue('audit-kind', kind) }, [kind])
  useEffect(() => { keepValue('audit-filter', filter) }, [filter])
  useEffect(() => { keepValue('audit-actor', actor) }, [actor])

  const load = useCallback(() => {
    // Проверено: items.map ниже рендерится вообще без условия на
    // loaded, а loaded никогда не сбрасывался обратно в false при
    // смене filter/actor — при смене фильтра скелетон не показывался
    // вовсе, сразу оставались старые, уже неверные по фильтру строки
    // до прихода новых. Сбрасываем оба явно.
    setLoaded(false)
    setItems([])
    const params = { days: 30, limit: 100, actor_kind: kind }
    if (filter) params.action = filter
    if (actor.trim()) params.actor = actor.trim()

    api.adminAudit(params)
      .then((res) => { setItems(res.items || []); setTotal(res.total || 0); setDenied(false) })
      .catch((e) => { if (e.status === 403) setDenied(true) })
      .finally(() => setLoaded(true))
  }, [filter, actor, kind])

  // Одна загрузка вместо двух — та же правка, что и на странице
  // «Пользователи» (там замерил: три запроса списка на один заход, и
  // скелет показывался заново после каждого). Загрузку запускали два
  // эффекта: один по готовности авторизации, второй по паузе после
  // ввода в поле «кто» — при первом открытии срабатывали оба.
  //
  // Следим за userId, а не за объектом пользователя: контекст обновляет
  // его не один раз за загрузку, и каждая новая ссылка перезапускала
  // эффект. Пауза нужна только печати — на первом заходе и при смене
  // фильтра ждать нечего.
  const userId = user?.id
  const lastActor = useRef(null)
  useEffect(() => {
    if (authLoading) return
    if (!userId) { navigate('/login', { replace: true }); return }
    const typing = lastActor.current !== null && lastActor.current !== actor
    lastActor.current = actor
    const id = setTimeout(load, typing ? 350 : 0)
    return () => clearTimeout(id)
  }, [authLoading, userId, load, navigate, actor])

  // Сводка не зависит ни от фильтров, ни от строки поиска — грузим её
  // один раз, а не вместе с каждой перезагрузкой списка.
  useEffect(() => {
    if (authLoading || !userId) return
    api.adminAuditActors(7).then((r) => setActors(r.items || [])).catch(() => {}).finally(() => setActorsLoaded(true))
  }, [authLoading, userId])

  if (denied) {
    return (
      <div className="page">
        <PageHeader title={t('audit.title')} />
        <p className="empty">{t('admin.no_access')}</p>
      </div>
    )
  }

  return (
    <div className="page admin-audit">
      <PageHeader
        title={t('audit.title')}
        subtitle={loaded ? t('audit.found', { count: total }) : null}
      />

      {/* Поиск и отборы одной полосой. Раньше это были три ряда
          подряд: голое поле без рамки, ряд вкладок и ряд фишек — они
          занимали треть экрана, и до самого журнала приходилось
          прокручивать. */}
      <div className="admin-bar">
        <div className="search-field admin-bar-search">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
          <input
            value={actor}
            onChange={(e) => setActor(e.target.value)}
            placeholder={t('audit.who')}
          />
          {actor && (
            <button className="search-clear" onClick={() => setActor('')} aria-label={t('actions.clear')}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          )}
        </div>

        <div className="admin-chips">
          {KINDS.map((k) => (
            <button key={k} className={kind === k ? 'chip chip-active' : 'chip'} onClick={() => setKind(k)}>
              {t(`audit.kind_${k}`)}
            </button>
          ))}
          <span className="admin-chips-sep" />
          {FILTERS.map((f) => (
            <button
              key={f.key || 'all'}
              className={`chip ${filter === f.key ? 'chip-active' : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {t(f.label)}
            </button>
          ))}
        </div>
      </div>

      {/* Кто что решил — построчный журнал при нескольких модераторах
          уже не читают. Сначала сводка по людям, нажатие на строку
          показывает журнал только этого человека. */}
      {/* Сводка по людям — одной полосой постоянной высоты (прокручивается вбок). Раньше это был столбик строк, который
          приходил вместе с данными и раздвигал страницу на свою высоту: журнал под ним прыгал вниз. */}
      {(actors.length > 0 || !actorsLoaded) && (
        <div className="audit-actors" aria-busy={!actorsLoaded}>
          {!actorsLoaded && <><span className="sk-block audit-actor-sk" aria-hidden="true" /><span className="sk-block audit-actor-sk" aria-hidden="true" /></>}
          {actors.map((row) => (
            <button
              key={row.id}
              className={`audit-actor${actor === row.name ? ' active' : ''}`}
              onClick={() => setActor(actor === row.name ? '' : row.name)}
            >
              <span className="audit-actor-name">{row.name}</span>
              <span className="audit-actor-nums">
                <span className="ok">+{row.approved}</span>
                <span className="no">−{row.rejected}</span>
                {row.blocked > 0 && <span className="blk">⌀{row.blocked}</span>}
                <span className="all">{row.total}</span>
              </span>
            </button>
          ))}
        </div>
      )}

      {!loaded && <div className="audit-list"><AuditRowSkeletons count={6} /></div>}
      {loaded && !items.length && <p className="empty">{t('audit.empty')}</p>}

      {/* Записи сгруппированы по дням, а время стоит слева столбцом.
          Раньше каждая запись была карточкой с датой в углу и именем
          сотрудника под действием — при десятке записей подряд от
          одного человека это десять одинаковых строк «Maksim
          Kolesnikov» и десять раз «18.09». Читать приходилось не
          журнал, а повторы.

          Теперь дата стоит один раз над днём, имя — только когда оно
          меняется, а взгляд идёт по колонке времени сверху вниз, как
          в любом журнале. */}
      <div className="audit-days">
        {groupByDay(items, i18n.language).map(([day, rows]) => (
          <div className="audit-day" key={day}>
            <div className="audit-day-title">{day}</div>
            {rows.map((row, index) => {
              const to = row.target_type === 'listing' ? `/go/${row.target_id}`
                : row.target_type === 'user' ? `/admin/users/${row.target_id}` : null
              const Row = to ? Link : 'div'
              const who = row.actor_id ? row.actor : t('audit.by_system')
              // Имя показываем, только когда оно сменилось: подряд
              // идущие решения одного человека и так его.
              const sameAsPrev = index > 0 && (rows[index - 1].actor || '') === (row.actor || '')
              return (
                <Row key={row.id} className={`audit-line tone-${actionTone(row.action)}`} {...(to ? { to } : {})}>
                  {/* лента событий: значок действия в цветном круге на вертикальной линии времени */}
                  <span className="audit-ico" aria-hidden="true"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d={actionIcon(row.action)} /></svg></span>
                  <span className="audit-at">{timeOnly(row.created_at, i18n.language)}</span>
                  <span className="audit-body">
                    <span className="audit-what">
                      {t(`audit.act.${row.action}`, row.action)}
                      {row.details?.about ? <b> {row.details.about}</b> : null}
                    </span>
                    {(row.reason || !sameAsPrev) && (
                      <span className="audit-sub">
                        {!sameAsPrev && <span className="audit-who">{who}</span>}
                        {row.reason && <span className="audit-why">{row.reason}</span>}
                      </span>
                    )}
                  </span>
                  {to && (
                    <svg className="audit-go" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
                  )}
                </Row>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

/** Цвет события в ленте: зелёный — одобрил/подтвердил, красный — отклонил/заблокировал/удалил, синий — перенёс/изменил, серый — прочее. */
function actionTone(a = '') {
  if (/approve|unblock|verify$|answer|payments_on|renew|flag_cleared/.test(a)) return 'ok'
  if (/reject|block|delete|suspicious|unverify|payments_off|failed/.test(a)) return 'bad'
  if (/move|role|retitle|reset_name|return/.test(a)) return 'edit'
  return 'info'
}
function actionIcon(a = '') {
  const tone = actionTone(a)
  if (/move|return/.test(a)) return 'M5 12h14M13 6l6 6-6 6'
  if (/payments/.test(a)) return 'M2 7h20v10H2zM2 11h20'
  if (/role|reset_name|retitle/.test(a)) return 'M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z'
  if (/ticket|answer|chat/.test(a)) return 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'
  if (tone === 'ok') return 'm5 12 5 5 9-10'
  if (tone === 'bad') return 'M6 6l12 12M18 6 6 18'
  return 'M12 8v4M12 16h.01M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z'
}
