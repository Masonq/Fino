import { showIsland } from '../utils/island'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { api, getToken } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'

const TOPICS = ['listing', 'account', 'payment', 'abuse', 'other']

export default function Support() {
  const { t } = useTranslation()
  const { user, loading: authLoading } = useAuth()
  // Пока проверяется вход, ждём то, что подсказывает токен: есть токен — человек, скорее всего, войдёт, поле не нужно;
  // нет токена — гость, поле нужно. Иначе поле показывалось всем, а у вошедших пропадало, и «Отправить» прыгала на 62.
  const expectUser = Boolean(user) || (authLoading && Boolean(getToken()))

  const [topic, setTopic] = useState('other')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [contact, setContact] = useState('')
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)
  const [mine, setMine] = useState([])
  const [reply, setReply] = useState({})

  useEffect(() => {
    if (!user) return
    api.supportMine().then((res) => setMine(res.items || [])).catch(() => {})
  }, [user, sent])

  const send = async () => {
    if (subject.trim().length < 3 || body.trim().length < 5) return
    setSending(true)
    try {
      await api.supportCreate({
        topic,
        subject: subject.trim(),
        body: body.trim(),
        contact: contact.trim() || undefined,
      })
      setSubject(''); setBody(''); setSent(true)
    } catch (e) {
      showIsland({ text: e.status === 429 ? t('support.too_many') : t('support.failed'), kind: 'warn' })
    } finally { setSending(false) }
  }

  const answer = async (id) => {
    const text = (reply[id] || '').trim()
    if (!text) return
    try {
      await api.supportReply(id, text)
      setReply((prev) => ({ ...prev, [id]: '' }))
      const res = await api.supportMine()
      setMine(res.items || [])
    } catch { showIsland({ text: t('support.failed'), kind: 'warn' }) }
  }

  return (
    <div className="page support">
      <PageHeader title={t('support.title')} kicker={t('support.kicker')} />

      {/* PLONK 2.0: вступление карточкой и быстрые ответы — многое решается без обращения */}
      <div className="sup-hero">
        <span className="sup-hero-icon" aria-hidden="true"><svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20.5 12a8 8 0 0 1-8.5 8 9 9 0 0 1-3.4-.7L4 20.5l1.3-3.9A8 8 0 1 1 20.5 12Z" /><path d="M8.5 11h.01M12 11h.01M15.5 11h.01" /></svg></span>
        <div><b>{t('support.hero_title')}</b><span>{t('support.hero_text')}</span></div>
      </div>
      <div className="sup-quick">
        <Link to="/rules" className="sup-q" style={{ background: '#E3ECFA' }}><b>{t('support.q_rules')}</b><span>{t('support.q_rules_hint')}</span></Link>
        <Link to="/vodic" className="sup-q" style={{ background: '#E2F1E6' }}><b>{t('support.q_guides')}</b><span>{t('support.q_guides_hint')}</span></Link>
      </div>

      {sent && <p className="support-sent">{t('support.sent')}</p>}

      {/* Та же карточка со строками, что и в «Моих данных»: тема,
          заголовок, текст — одно обращение, а не три отдельных поля,
          расставленных по экрану. */}
      <div className="form-card">
        <div className="field-row">
          <span className="field-label">{t('support.topic_label')}</span>
          <div className="field-chips">
            {TOPICS.map((key) => (
              <button
                key={key}
                className={`chip ${topic === key ? 'chip-active' : ''}`}
                onClick={() => setTopic(key)}
              >
                {t(`support.topic.${key}`)}
              </button>
            ))}
          </div>
        </div>

        <label className="field-row">
          <span className="field-label">{t('support.subject_label')}</span>
          <input
            className="field-input"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder={t('support.subject')}
          />
        </label>

        <label className="field-row">
          <span className="field-label">{t('support.body_label')}</span>
          <textarea
            className="field-input field-textarea"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder={t('support.body')}
            rows={5}
          />
        </label>

        {/* Не вошедшего спрашиваем, куда ответить: без обратного адреса
            обращение бесполезно обеим сторонам. */}
        {!expectUser && (
          <label className="field-row">
            <span className="field-label">{t('support.contact_label')}</span>
            <input
              className="field-input"
              value={contact}
              onChange={(e) => setContact(e.target.value)}
              placeholder={t('support.contact')}
            />
          </label>
        )}
      </div>

      <button className="form-save" disabled={sending} onClick={send}>
        {t('support.send')}
      </button>

      {!!mine.length && (
        <div className="support-mine">
          <div className="stats-block-title">{t('support.mine')}</div>
          {mine.map((ticket) => (
            <div key={ticket.id} className="support-ticket">
              <div className="audit-head">
                <span className="audit-action">{ticket.subject}</span>
                <span className={`tag ${ticket.status === 'answered' ? '' : 'tag-muted'}`}>
                  {t(`support.status.${ticket.status}`)}
                </span>
              </div>
              <div className="support-thread">
                {(ticket.messages || []).map((m) => (
                  <div
                    key={m.id}
                    className={`support-msg ${m.from_staff ? 'from-staff' : ''}`}
                  >
                    {m.body}
                  </div>
                ))}
              </div>
              {ticket.status !== 'closed' && (
                <div className="support-reply">
                  <input
                    value={reply[ticket.id] || ''}
                    onChange={(e) => setReply((p) => ({ ...p, [ticket.id]: e.target.value }))}
                    placeholder={t('support.your_reply')}
                  />
                  <button onClick={() => answer(ticket.id)}>{t('support.send')}</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
