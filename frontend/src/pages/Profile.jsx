import { sinceMonth } from '../utils/time'
import { useEffect, useState } from 'react'
import { keepValue, readValue } from '../utils/keepPlace'
import { formatPrice } from '../utils/money'
import Avatar from '../components/Avatar'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'
import PhoneReminder from '../components/PhoneReminder'
import { ProfileSkeleton } from '../components/Skeletons'
import NotificationBell from '../components/NotificationBell'
import LanguageSwitcher from '../components/LanguageSwitcher'
import BalanceCard from '../components/BalanceCard'
import useStickyColumn from '../hooks/useStickyColumn'
import { api } from '../api/client'

/**
 * Почта в карточке — с точкой переноса перед «собакой».
 *
 * Адрес вроде maxsim_kolesnikov@icloud.com для браузера одно длинное
 * слово: переносить его негде, и он уезжал за правый край карточки.
 * Разрешить перенос в любом месте мало — тогда строка рвётся посреди
 * домена («…@icloud.c / om»). <wbr> подсказывает единственное
 * осмысленное место разрыва: имя на одной строке, домен на другой.
 * Ломается только когда не помещается, короткий адрес остаётся в
 * строку как был.
 */
function ContactEmail({ value }) {
  const at = value.indexOf('@')
  if (at < 1) return value
  return <>{value.slice(0, at)}<wbr />{value.slice(at)}</>
}

// «1 240», а не «1240» — тысячи с тонким пробелом.
const fmt = (n) => (n ?? 0).toLocaleString('ru-RU').replace(/\u00a0/g, '\u2009')

export default function Profile() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, loading, lastKnownRole, signOut } = useAuth()
  // Липкая боковая колонка — тот же хук, что и на лендинге раздела
  // (src/hooks/useStickyColumn.js): аватар с балансом остаются на
  // месте, пока справа прокручивается список пунктов, а у нижнего края
  // колонки блок останавливается и уезжает вверх вместе с ней.
  // Вызываем до ранних возвратов ниже — порядок хуков должен быть
  // одинаковым при любом состоянии загрузки.
  const sidebar = useStickyColumn(28, Boolean(user))

  // Сколько ждёт разбора — числом прямо в служебном разделе, чтобы
  // из профиля было видно, что там есть работа, и не приходилось
  // заходить в каждую очередь наугад.
  const isStaff = user?.role === 'moderator' || user?.role === 'admin'
  // Цифры и бейджи храним между заходами: без этого при каждом
  // возврате на профиль они на секунду пропадали и появлялись заново,
  // а строка «что требует внимания» успевала мигнуть.
  const [stats, setStats] = useState(() => readValue('profile-stats', null))
  useEffect(() => {
    if (!user) return
    api.myStats()
      .then((res) => { setStats(res); keepValue('profile-stats', res) })
      .catch(() => setStats({ listings: 0, views: 0, favorites: 0 }))
  // Намеренно: зависим от user?.id, а не от всего объекта: он пересобирается при каждом обновлении профиля, и запрос уходил бы снова и снова.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id])

  // Подборка «может быть интересно» — внизу профиля. Запрашиваем здесь,
  // до любых ранних возвратов: хук нельзя вызывать после них, иначе
  // порядок хуков между отрисовками меняется.
  useEffect(() => {
    if (!user) return
    api.forYou(i18n.language).then((r) => setForYou(r.items || [])).catch(() => {})
  // Намеренно: зависим от user?.id, а не от всего объекта: он пересобирается при каждом обновлении профиля, и запрос уходил бы снова и снова.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id, i18n.language])

  const [queues, setQueues] = useState(() => readValue('profile-queues', null))
  // Подборка «может быть интересно» — внизу профиля: человек сюда
  // заходит между делом, и уходить ни с чем ему незачем.
  const [forYou, setForYou] = useState([])
  useEffect(() => {
    if (!isStaff) { setQueues(null); return }
    let alive = true
    api.modCounters()
      .then((res) => { if (alive) { setQueues(res); keepValue('profile-queues', res) } })
      .catch(() => {})
    return () => { alive = false }
  }, [isStaff])

  if (loading) {
    return (
      <div className="fav-page profile-page">
        <PageHeader title={t('nav.profile')} back={false} />
        <ProfileSkeleton showStaff={lastKnownRole === 'moderator' || lastKnownRole === 'admin'} />
      </div>
    )
  }

  if (!user) {
    return (
      <div className="fav-page profile-page">
        <PageHeader title={t('nav.profile')} back={false} />
        <div className="fav-empty">
          <div className="fav-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" />
            </svg>
          </div>
          <p>{t('auth.subtitle')}</p>
          <button className="fav-cta" onClick={() => navigate('/login?returnTo=%2Fprofile')}>
            {t('common.login')}
          </button>

          {/* Под кнопкой входа — ничего: ни промо, ни рассказа о
              сервисе. Обещание чего бы то ни было рядом с формой входа
              Safari уже дважды принял за фишинг, а объяснять, куда
              человек попал, лучше письмом от команды — оно приходит
              сразу после регистрации. */}
        </div>
      </div>
    )
  }

  // «Здесь с сентября 2026» — короткая строка доверия: сколько человек
  // на площадке. У новичка она честно короткая, и это тоже сигнал.
  const memberSince = user?.created_at
    ? t('profile.member_since', {
      date: sinceMonth(user.created_at, i18n.language),
    })
    : null

  // Собираем в том порядке, в каком с этим стоит разбираться:
  // отклонённое чинить прямо сейчас, ответ поддержки прочитать,
  // истекающее продлить, а про то, что «на проверке», достаточно
  // знать, что оно не потерялось.
  const attention = [
    stats?.listings_rejected > 0 && { key: 'rejected', count: stats.listings_rejected, to: '/my?tab=rejected' },
    stats?.support_answered > 0 && { key: 'support', count: stats.support_answered, to: '/support' },
    stats?.listings_expiring > 0 && { key: 'expiring', count: stats.listings_expiring, to: '/my' },
    stats?.listings_pending > 0 && { key: 'pending', count: stats.listings_pending, to: '/my?tab=pending' },
  ].filter(Boolean)

  const initial = ((user.company_name || user.display_name) || '?').trim().charAt(0).toUpperCase()
  const isCompany = user.role === 'seller_business'

  return (
    <div className="fav-page profile-page">
      <PageHeader title={t('nav.profile')} back={false}>
        <NotificationBell />
      </PageHeader>

      {/* Перенесено с главной — тут логичнее: человек уже смотрит на
          свои данные, поле для ввода телефона в один шаг отсюда, а
          не через отдельный переход. */}
      <PhoneReminder user={user} />

      {/* .profile-layout — display:contents на мобильном (не меняет
          поток вовсе, дети ведут себя как будто обёртки нет), на
          десктопе — сетка: слева аватар и баланс постоянно на месте,
          справа весь остальной контент, шире и с уже готовой сеткой
          пунктов в .profile-menu (была сделана раньше в сессии, но
          терялась в узкой 600px странице). */}
      <div className="profile-layout">
        <div
          ref={sidebar.ref}
          className={`profile-sidebar${sidebar.className}`}
          style={sidebar.style}
        >
          {/* Шапка карточкой, как у Avito в «Управлении профилем»:
              аватар, имя, а под ним то, по чему покупатель судит о
              продавце — сколько он здесь, частное лицо или компания,
              рейтинг. Раньше это висело прямо на фоне страницы и
              читалось как случайный набор строк.

              Тут же кнопка проверки личности: непроверенному она
              говорит, что делать, проверенному — показывает отметку,
              которую видят покупатели. */}
          <div className="profile-card">
            <Link className="profile-card-edit" to="/profile/edit" aria-label={t('edit_profile.edit')}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
            </Link>

            <Avatar
              src={user.avatar_url}
              name={initial}
              className={isCompany ? 'profile-avatar is-company' : 'profile-avatar'}
            />

            {/* Имя, строка о продавце и кнопка проверки — колонкой
                справа от аватара. Раньше всё это стояло столбиком под
                ним, и карточка занимала пол-экрана ради трёх строк. */}
            <div className="profile-card-body">
              <div className="profile-card-name">{user.company_name || user.display_name}</div>
              <div className="profile-card-meta">
                {memberSince && <span>{memberSince}</span>}
                <span>{isCompany ? t('seller.company_badge') : t('profile.person')}</span>
                <span>
                  {user.rating_count
                    ? t('edit_profile.rating', { value: user.rating_avg, count: user.rating_count })
                    : t('edit_profile.no_rating')}
                </span>
              </div>

              {user.document_verified ? (
                <div className="profile-verified">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M20 6 9 17l-5-5" /></svg>
                  {t('verify.verified')}
                </div>
              ) : (
                <Link className="profile-verify-btn" to="/profile/edit">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M12 2.5 4.5 5.5v6c0 5 3.2 8 7.5 10 4.3-2 7.5-5 7.5-10v-6L12 2.5Z" /><path d="m9 12 2 2 4-4" /></svg>
                  {t('profile.verify_cta')}
                </Link>
              )}
            </div>
          </div>

          {/* Что требует внимания.
              Объявление на проверке, отклонённое, скоро снимут,
              ответ поддержки — всё это уже есть в базе, но человек
              узнаёт о нём, только если сам откроет нужный экран.
              Строка появляется, лишь когда есть о чём сказать: висеть
              каждый день ей незачем. */}
          {attention.length > 0 && (
            <div className="profile-attention">
              {attention.map((item) => (
                <Link key={item.key} to={item.to} className="attention-row">
                  <span className="attention-dot" aria-hidden="true" />
                  <span>{t(`profile.att_${item.key}`, { count: item.count })}</span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
                </Link>
              ))}
            </div>
          )}

          {/* Три цифры о своих объявлениях — то, ради чего продавец
              заходит в профиль: живо ли, смотрят ли, сохраняют ли. Пока
              не ответил сервер — прочерки того же размера, чтобы блок
              не прыгал. */}
          <div className="profile-stats">
            <Link to="/my" className="profile-stat is-link">
              <b>{stats ? stats.listings : '–'}</b>
              <span>{t('profile.stat_listings', { count: stats?.listings ?? 0 })}</span>
            </Link>
            <div className="profile-stat">
              <b>{stats ? fmt(stats.views) : '–'}</b>
              <span>{t('profile.stat_views', { count: stats?.views ?? 0 })}</span>
            </div>
            <div className="profile-stat">
              <b>{stats ? fmt(stats.favorites) : '–'}</b>
              <span>{t('profile.stat_favorites')}</span>
            </div>
          </div>

          <BalanceCard />
        </div>

        <div className="profile-main">
      {/* Раньше все десять пунктов шли одним плоским списком без единой
          зацепки, что где искать, — теперь три смысловые группы, у
          каждого пункта своя иконка вместо одинаковой стрелочки.
          «Разместить», «Избранное», «Сообщения» отсюда убраны — они
          уже есть в нижнем меню на каждом экране, дублировать незачем. */}
      {/* Два раздела вместо шести.
          Было: «Объявления» с одной строкой, «Общение» с одной строкой,
          «Настройки», «Мы в Telegram» с двумя ссылками и «Информация» с
          четырьмя документами. Заголовок над единственной строкой не
          помогает найти её быстрее, а мешает: экран из заголовков
          читается как список разделов, хотя это список действий.

          Документы и ссылки на Telegram ушли в подвал мелким текстом —
          их открывают раз в жизни, и место наравне с тем, чем
          пользуются каждый день, им ни к чему. */}
      <div className="profile-menu">
        {/* Приглашение друзей — обычной строкой списка, а не отдельной
            карточкой. Карточка висела сама по себе между балансом и
            списком и читалась как чужая вставка; при этом ведёт она
            туда же, куда и остальные строки, — на страницу. */}
        <Link className="profile-row" to="/profile/invite">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></svg>
          </span>
          {t('invite.card_title')}
          <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>

        {/* Ждут вашего отзыва. Приглашения живут в переписках, и без
            этой строки человек о них не узнаёт — а отзывы и есть то, на
            чём держится доверие к продавцам. Строки нет, когда ждать
            некому: пустой пункт со счётчиком «0» только мозолит глаз. */}
        {stats?.reviews_waiting > 0 && (
          <Link className="profile-row" to="/reviews/waiting">
            <span className="profile-row-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6-5.4-2.8-5.4 2.8 1-6L3.2 9.4l6.1-.9L12 3Z" /></svg>
            </span>
            {t('reviews.waiting_title')}
            <span className="profile-row-count accent">{stats.reviews_waiting}</span>
            <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
          </Link>
        )}
        <Link className="profile-row" to="/saved">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m20 20-4.35-4.35" /></svg>
          </span>
          {t('saved.title')}
          <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
        <Link className="profile-row" to="/history">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></svg>
          </span>
          {t('history.title')}
          <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
        <Link className="profile-row" to="/support">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="12" cy="12" r="9" /><path d="M12 16v.01M12 13c0-1.8 2-1.8 2-3.5A2 2 0 0 0 12 7.5 2 2 0 0 0 10 9.5" /></svg>
          </span>
          {t('support.title')}
          <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
        <Link className="profile-row" to="/volunteer">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M12 21s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 11c0 5.6-7 10-7 10Z" /></svg>
          </span>
          {t('volunteer.title')}
          <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
      </div>

      {forYou.length > 0 && (
        <div className="for-you">
          <div className="for-you-title">{t('profile.for_you')}</div>
          <div className="for-you-row">
            {forYou.map((l) => (
              <Link key={l.id} to={l.path} className="for-you-card">
                <div className="for-you-photo">
                  {l.cover_photo ? <img src={l.cover_photo} alt="" loading="lazy" />
                    : <div className="photo-placeholder" />}
                </div>
                {(l.is_free || l.price != null) && (
                  <div className="for-you-price">
                    {l.is_free ? t('detail.free') : formatPrice(l.price, l.currency, i18n.language)}
                  </div>
                )}
                {/* Без цены заголовок и есть главное в карточке — иначе
                    под фотографией висела пустая строка, а название
                    читалось как подпись к ней. */}
                <div className={l.price == null && !l.is_free ? 'for-you-name strong' : 'for-you-name'}>
                  {l.title}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="profile-section-title">{t('profile.sec_settings')}</div>
      <div className="profile-menu">
        <div className="profile-row profile-row-static">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.5 2.5 4 5.7 4 9s-1.5 6.5-4 9c-2.5-2.5-4-5.7-4-9s1.5-6.5 4-9Z" /></svg>
          </span>
          {t('profile.language')}
          <LanguageSwitcher variant="light" />
        </div>
        <Link className="profile-row" to="/profile/blocked">
          <span className="profile-row-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><circle cx="12" cy="12" r="9" /><path d="m5.5 5.5 13 13" /></svg>
          </span>
          {t('blocked.title')}
          <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
        </Link>
      </div>

      {/* Разделы для сотрудников. Раньше в модерацию заходили по адресу,
          который надо было помнить наизусть. */}
      {(user.role === 'moderator' || user.role === 'admin') && (
        <>
          <div className="profile-section-title">{t('admin.staff')}</div>
          <div className="profile-menu">
            <Link className="profile-row" to="/moderation">
              <span className="profile-row-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><path d="M20 6 9 17l-5-5" /></svg>
              </span>
              {t('admin.moderation')}
              {queues?.moderation > 0 && (
                <span className="profile-row-count">{queues.moderation}</span>
              )}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
            {/* Разговоры с приметами обмана. Со счётчиком, как у
                обращений: разбирать их надо быстро, пока человек не
                перевёл деньги. */}
            <Link className="profile-row" to="/admin/flagged">
              <span className="profile-row-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M10.3 3.9 1.8 18.2A2 2 0 0 0 3.5 21h17a2 2 0 0 0 1.7-2.8L13.7 3.9a2 2 0 0 0-3.4 0Z" /><path d="M12 9.5v4.5" /><path d="M12 17.5h.01" /></svg>
              </span>
              {t('flagged.title')}
              {queues?.flagged_chats > 0 && (
                <span className="profile-row-count">{queues.flagged_chats}</span>
              )}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
            {/* Тревоги — первым пунктом: это то, ради чего сотрудник
                заходит в служебный раздел, а не список людей. */}
            <Link className="profile-row" to="/admin/alerts">
              <span className="profile-row-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3 2 20h20L12 3Z" /><path d="M12 10v4M12 17.2v.1" /></svg>
              </span>
              {t('admin.alerts')}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
            <Link className="profile-row" to="/admin/users">
              <span className="profile-row-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="9" cy="8" r="3.2" /><path d="M2.5 20c0-3.4 2.9-5.8 6.5-5.8s6.5 2.4 6.5 5.8" /><circle cx="17.5" cy="8.5" r="2.6" /><path d="M17.5 14c2.6 0 4.5 1.8 4.5 4.4" /></svg>
              </span>
              {t('admin.title')}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
            <Link className="profile-row" to="/admin/stats">
              <span className="profile-row-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><path d="M4 20V10M12 20V4M20 20v-7" /></svg>
              </span>
              {t('stats.title')}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
            <Link className="profile-row" to="/admin/audit">
              <span className="profile-row-icon">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 4v4h4" /><path d="M12 8v4l3 2" /></svg>
              </span>
              {t('audit.title')}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
            {/* Ночные работы. Они идут сами, и без этой страницы
                поломку замечаешь через день — по пустой ленте или по
                письму, которое кто-то не получил. */}
            <Link className="profile-row" to="/admin/jobs">
              <span className="profile-row-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
              </span>
              {t('jobs.title')}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
            <Link className="profile-row" to="/admin/support">
              <span className="profile-row-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M3 13h4l2 3h6l2-3h4" /><path d="M5 5h14l3 8v5a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-5L5 5Z" /></svg>
              </span>
              {t('support.queue')}
              {queues?.support > 0 && (
                <span className="profile-row-count">{queues.support}</span>
              )}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
            <Link className="profile-row" to="/admin/team-chats">
              <span className="profile-row-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H9l-5 4z" /><path d="M8 9h8M8 12.5h5" /></svg>
              </span>
              {t('team_inbox.title')}
              {queues?.team_chats > 0 && (
                <span className="profile-row-count">{queues.team_chats}</span>
              )}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
            <Link className="profile-row" to="/admin/volunteers">
              <span className="profile-row-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0" /><path d="M16 11h6M19 8v6" /></svg>
              </span>
              {t('volunteer.queue')}
              {queues?.volunteers > 0 && (
                <span className="profile-row-count">{queues.volunteers}</span>
              )}
              <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
            </Link>
            {user.role === 'admin' && (
              <Link className="profile-row" to="/admin/settings">
                <span className="profile-row-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M4 7h9M17 7h3M4 17h3M11 17h9" /><circle cx="15" cy="7" r="2" /><circle cx="9" cy="17" r="2" /></svg>
                </span>
                {t('settings.title')}
                <svg className="profile-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m9 6 6 6-6 6" /></svg>
              </Link>
            )}
          </div>
        </>
      )}

      <button
        className="profile-logout"
        onClick={() => { signOut(); navigate('/') }}
      >
        {t('auth.logout')}
      </button>

      {/* Подвал: то, что открывают раз в жизни — правила, условия,
          ссылки на наш чат и бота. Ссылки на Telegram внешние, поэтому
          обычные <a>: Link увёл бы внутрь приложения по
          несуществующему адресу. */}
      <div className="profile-footer">
        <div className="profile-footer-links">
          <a href="https://t.me/Baraholka_Plonk" target="_blank" rel="noopener noreferrer">{t('profile.f_chat')}</a>
          <a href="https://t.me/Baraholka_plonk_bot" target="_blank" rel="noopener noreferrer">{t('profile.f_bot')}</a>
        </div>
        <div className="profile-footer-links">
          <Link to="/rules">{t('profile.f_rules')}</Link>
          <Link to="/terms">{t('profile.f_terms')}</Link>
          <Link to="/privacy">{t('profile.f_privacy')}</Link>
        </div>
        <div className="profile-footer-brand">plonk.rs</div>
      </div>
        </div>
      </div>
    </div>
  )
}
