import { useEffect, useState } from 'react'
import Avatar from '../components/Avatar'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'

/**
 * Приглашение друзей.
 *
 * Прежняя страница была честной, но немой: ссылка, кнопка и строка
 * мелким шрифтом. Человек не понимал главного — что он получит, когда
 * и за что, — и уходил, не отправив ссылку никому.
 *
 * Теперь по порядку, как читают: что это, сколько дают, что должен
 * сделать друг, сколько уже пришло. И только потом мелкие вопросы —
 * их разворачивает тот, кому действительно интересно, а место они
 * занимали бы у всех.
 */
// Столько же, сколько начисляет сервер (REFERRAL_BONUS). Два числа в
// двух местах разъезжаются при первой же правке, но тянуть его
// запросом ради одной цифры — дороже, чем польза.
const BONUS = 200

export default function InviteFriend() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [copied, setCopied] = useState(false)
  const [openQuestion, setOpenQuestion] = useState(null)

  useEffect(() => {
    api.myReferrals().then(setStats).catch(() => setStats(null))
  }, [])

  // Короткий код — первые 8 символов id, тот же приём, что уже
  // используется для ссылок на объявления: не весь UUID, а то ссылка
  // получалась на километр длиной.
  const link = user ? `${window.location.origin}/?ref=${user.id.slice(0, 8)}` : ''

  const share = async () => {
    if (navigator.share) {
      try { await navigator.share({ title: t('invite.share_title'), url: link }) } catch { /* закрыл меню сам — не ошибка */ }
      return
    }
    try {
      await navigator.clipboard.writeText(link)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* буфер недоступен — редкий случай */ }
  }

  const questions = ['who', 'what', 'when', 'spend']

  return (
    <div className="invite-page">
      <PageHeader title={t('invite.title')} />

      {/* Обещание — первым экраном и одной фразой: человек решает,
          читать ли дальше, именно здесь. */}
      <div className="invite-hero">
        <img src="/invite/hero.webp" alt="" />
        <h1>{t('invite.hero_title')}</h1>
        <p>{t('invite.hero_text', { count: BONUS })}</p>
      </div>

      {/* Что получит каждый — двумя карточками: это две разные выгоды,
          и складывать их в одну фразу значит заставить человека
          разбираться, кому что. */}
      <div className="invite-cards">
        <div className="invite-card">
          <img src="/invite/you.webp" alt="" />
          <div className="invite-card-text">
            <div className="invite-card-title">{t('invite.card_you')}</div>
            <div className="invite-card-sub">{t('invite.card_you_text', { count: BONUS })}</div>
          </div>
        </div>
        <div className="invite-card">
          <img src="/invite/friend.webp" alt="" />
          <div className="invite-card-text">
            <div className="invite-card-title">{t('invite.card_friend')}</div>
            <div className="invite-card-sub">{t('invite.card_friend_text', { count: BONUS })}</div>
          </div>
        </div>
      </div>

      {/* Что должно произойти — тремя шагами вместо абзаца мелким
          шрифтом: так видно, что условие одно и оно простое. */}
      <div className="invite-steps">
        <div className="invite-block-title">{t('invite.how_title')}</div>
        {[1, 2, 3].map((step) => (
          <div className="invite-step" key={step}>
            <span className="invite-step-num">{step}</span>
            <span>{t(`invite.step_${step}`)}</span>
          </div>
        ))}
      </div>

      {stats && stats.invited > 0 && (
        <>
          {/* Три цифры отвечают на разные вопросы: сколько ссылок
              разошлось, сколько людей дошли до объявления и сколько
              вышло денег. Одной цифрой это не сказать. */}
          <div className="invite-stats">
            <div>
              <strong>{stats.invited}</strong>
              <span>{t('invite.stat_invited')}</span>
            </div>
            <div>
              <strong>{stats.posted}</strong>
              <span>{t('invite.stat_posted')}</span>
            </div>
            <div>
              <strong>{stats.earned}</strong>
              <span>{t('invite.stat_earned')}</span>
            </div>
          </div>

          {/* Сами приглашённые. Без них цифры висят в воздухе: человек
              не понимает, кто дошёл, а кто застрял на полпути, и не
              знает, кому напомнить. */}
          {stats.people?.length > 0 && (
            <div className="invite-people">
              <div className="invite-block-title">{t('invite.people_title')}</div>
              {stats.people.map((person, i) => (
                <div className="invite-person" key={i}>
                  <Avatar url={person.avatar_url} name={person.name} size={38} />
                  <div className="invite-person-text">
                    <div className="invite-person-name">{person.name}</div>
                    <div className={`invite-person-state ${person.state}`}>
                      {t(`invite.state_${person.state}`, { amount: stats.bonus })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      <div className="invite-faq">
        {questions.map((key) => (
          <div className="invite-faq-item" key={key}>
            <button onClick={() => setOpenQuestion(openQuestion === key ? null : key)}>
              <span>{t(`invite.q_${key}`)}</span>
              <svg
                className={openQuestion === key ? 'open' : ''}
                viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"
              >
                <path d="m6 9 6 6 6-6" />
              </svg>
            </button>
            {openQuestion === key && <p>{t(`invite.a_${key}`, { count: BONUS })}</p>}
          </div>
        ))}
      </div>

      {/* Кнопка прижата к низу экрана: человек дочитал — и она уже
          здесь, а не где-то выше, куда надо возвращаться. */}
      <div className="invite-bottom">
        <div className="invite-link">{link}</div>
        <button className="form-save" onClick={share}>
          {copied ? t('invite.copied') : t('invite.share_btn')}
        </button>
      </div>
    </div>
  )
}
