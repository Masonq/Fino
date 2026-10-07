import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PageHeader from '../components/PageHeader'

const ROLES = ['support', 'moderation', 'both']
const LANGS = ['ru', 'sr', 'en']
const HOURS = ['1–3', '3–7', '7+']

/*
 * Волонтёрство — как в телеграм-чатах: в поддержке отвечают свои же
 * люди. Страница объясняет, что делает команда, и принимает короткую
 * анкету. Принятому владелец выдаёт роль модератора.
 */
export default function Volunteer() {
  const { t } = useTranslation()
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()

  const [mine, setMine] = useState(null)
  // пока не знаем, в команде ли человек и подавал ли заявку, — не показываем ни анкету, ни «спасибо»:
  // раньше сначала рисовалась анкета, а через полсекунды её сменяло «Вы уже в команде» (мелькание на записи)
  const [known, setKnown] = useState(false)
  const [isTeam, setIsTeam] = useState(false)
  const [role, setRole] = useState('support')
  const [langs, setLangs] = useState(['ru'])
  const [hours, setHours] = useState('1–3')
  const [about, setAbout] = useState('')
  const [agreed, setAgreed] = useState(false)      // обязательная галочка про конфиденциальность
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) { if (!authLoading) setKnown(true); return }
    api.volunteerMine()
      .then((res) => { setMine(res.application); setIsTeam(!!res.is_team) })
      .catch(() => {})
      .finally(() => setKnown(true))
  }, [user, authLoading])

  const toggleLang = (code) => setLangs((prev) => (
    prev.includes(code) ? (prev.length > 1 ? prev.filter((l) => l !== code) : prev) : [...prev, code]
  ))

  const send = async () => {
    if (!user) { navigate('/login?returnTo=%2Fvolunteer'); return }
    if (about.trim().length < 20) { setError(t('volunteer.too_short')); return }
    if (!agreed) { setError(t('volunteer.consent_needed')); return }
    setSending(true); setError('')
    try {
      const res = await api.volunteerApply({
        role, languages: langs, hours_per_week: hours, about: about.trim(), accept_confidentiality: true,
      })
      setMine(res.application)
    } catch (e) {
      setError(e.status === 409 ? t('volunteer.already') : t('support.failed'))
    } finally { setSending(false) }
  }

  const pending = mine?.status === 'new'
  const decided = mine && mine.status !== 'new'

  return (
    <div className="page volunteer">
      <PageHeader title={t('volunteer.title')} />

      <p className="page-lead">{t('volunteer.lead')}</p>

      {/* Что делает команда — три коротких пункта, чтобы человек
          понимал, на что подписывается, до анкеты. */}
      <div className="volunteer-what">
        {['answer', 'moderate', 'rules'].map((key) => (
          <div key={key} className="volunteer-what-row">
            <span className="volunteer-what-mark" />
            <div>
              <div className="volunteer-what-title">{t(`volunteer.what_${key}`)}</div>
              <div className="volunteer-what-text">{t(`volunteer.what_${key}_text`)}</div>
            </div>
          </div>
        ))}
      </div>

      {!known && <div className="sk-block" style={{ height: 220, borderRadius: 24, marginTop: 12 }} aria-hidden="true" />}

      {known && isTeam && (
        <div className="volunteer-state is-ok">{t('volunteer.in_team')}</div>
      )}

      {known && !isTeam && pending && (
        <div className="volunteer-state">{t('volunteer.pending')}</div>
      )}

      {/* Заявка подана до появления галочки: без подтверждения её принять нельзя. */}
      {known && !isTeam && pending && !mine.confidentiality_accepted && (
        <div className="form-card volunteer-consent-card">
          <label className="post-checkbox volunteer-consent">
            <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
            <span>{t('volunteer.consent')} <Link to="/terms">{t('volunteer.consent_link')}</Link></span>
          </label>
          <button className="form-save" disabled={!agreed || sending}
            onClick={async () => {
              setSending(true); setError('')
              try { const res = await api.volunteerConsent(); setMine(res.application) } catch { setError(t('support.failed')) } finally { setSending(false) }
            }}>
            {t('volunteer.consent_confirm')}
          </button>
        </div>
      )}

      {!isTeam && decided && (
        <div className={`volunteer-state ${mine.status === 'accepted' ? 'is-ok' : ''}`}>
          {t(`volunteer.decided_${mine.status}`)}
          {mine.note && <div className="volunteer-note">{mine.note}</div>}
        </div>
      )}

      {known && !isTeam && !pending && !authLoading && (
        <>
          <div className="form-card">
            <div className="field-row">
              <span className="field-label">{t('volunteer.role_label')}</span>
              <div className="field-chips">
                {ROLES.map((key) => (
                  <button key={key} className={`chip ${role === key ? 'chip-active' : ''}`} onClick={() => setRole(key)}>
                    {t(`volunteer.role.${key}`)}
                  </button>
                ))}
              </div>
            </div>
            <div className="field-row">
              <span className="field-label">{t('volunteer.langs_label')}</span>
              <div className="field-chips">
                {LANGS.map((code) => (
                  <button key={code} className={`chip ${langs.includes(code) ? 'chip-active' : ''}`} onClick={() => toggleLang(code)}>
                    {t(`volunteer.lang.${code}`)}
                  </button>
                ))}
              </div>
            </div>
            <div className="field-row">
              <span className="field-label">{t('volunteer.hours_label')}</span>
              <div className="field-chips">
                {HOURS.map((h) => (
                  <button key={h} className={`chip ${hours === h ? 'chip-active' : ''}`} onClick={() => setHours(h)}>
                    {h} {t('volunteer.hours_unit')}
                  </button>
                ))}
              </div>
            </div>
            <label className="field-row">
              <span className="field-label">{t('volunteer.about_label')}</span>
              <textarea
                className="field-input field-textarea"
                value={about}
                onChange={(e) => setAbout(e.target.value)}
                placeholder={t('volunteer.about')}
                rows={5}
              />
            </label>
          </div>

          <label className="post-checkbox volunteer-consent">
            <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
            <span>{t('volunteer.consent')} <Link to="/terms">{t('volunteer.consent_link')}</Link></span>
          </label>

          {error && <p className="form-error">{error}</p>}

          <button className="form-save" disabled={sending} onClick={send}>
            {user ? t('volunteer.send') : t('volunteer.login_to_send')}
          </button>
        </>
      )}
    </div>
  )
}
