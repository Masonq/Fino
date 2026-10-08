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
const ICONS = {"answer": "<path d=\"M20.5 12a8 8 0 0 1-8.5 8 9 9 0 0 1-3.4-.7L4 20.5l1.3-3.9A8 8 0 1 1 20.5 12Z\" />", "moderate": "<path d=\"M12 3 4 6.5v5c0 4.6 3.4 8.4 8 9.5 4.6-1.1 8-4.9 8-9.5v-5z\" /><path d=\"m9 12 2 2 4-4\" />", "rules": "<path d=\"M20.8 4.6a5 5 0 0 0-7 0L12 6.4l-1.8-1.8a5 5 0 0 0-7 7L12 20.5l8.8-8.9a5 5 0 0 0 0-7Z\" />"}

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

      {/* PLONK 2.0: вступление карточкой со свечением и три пункта цветными плитками со значками
          (было — текст и маркированный список с оранжевыми точками) */}
      <div className="vol-hero">
        <span className="vol-hero-kicker">{t('volunteer.hero_kicker')}</span>
        <p className="vol-hero-text">{t('volunteer.lead')}</p>
      </div>
      <div className="vol-tiles">
        {[['answer', '#E3ECFA'], ['moderate', '#E2F1E6'], ['rules', '#FAE5EE']].map(([key, bg]) => (
          <div key={key} className="vol-tile" style={{ background: bg }}>
            <span className="vol-tile-icon"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" dangerouslySetInnerHTML={{ __html: ICONS[key] }} /></span>
            <div className="vol-tile-title">{t(`volunteer.what_${key}`)}</div>
            <div className="vol-tile-text">{t(`volunteer.what_${key}_text`)}</div>
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
