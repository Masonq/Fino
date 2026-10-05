import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const G = '#0E9F6E', GS = '#E4F6EE', GD = '#0B5C42', O = '#FF6A3D', INK = '#1C2620'

const ArtShoot = () => (
  <svg width="84" height="84" viewBox="0 0 84 84" aria-hidden="true">
    <rect x="22" y="6" width="40" height="72" rx="9" fill={INK} /><rect x="25" y="12" width="34" height="60" rx="6" fill="#2B3A31" />
    <rect x="30" y="44" width="24" height="12" rx="3" fill={O} /><rect x="28" y="40" width="6" height="16" rx="2.5" fill="#E5522A" /><rect x="50" y="40" width="6" height="16" rx="2.5" fill="#E5522A" />
    <circle cx="42" cy="28" r="8" fill="rgba(255,255,255,.92)" /><path d="M40 24.5v7l5.5-3.5z" fill={INK} />
    <circle cx="66" cy="18" r="7" fill="#FF3B5C" /><path d="M66 21.5l-3.2-3.1a1.9 1.9 0 0 1 2.7-2.7l.5.5.5-.5a1.9 1.9 0 0 1 2.7 2.7z" fill="#fff" />
  </svg>
)
const ArtAttach = () => (
  <svg width="84" height="84" viewBox="0 0 84 84" aria-hidden="true">
    <rect x="14" y="6" width="40" height="72" rx="9" fill={INK} /><rect x="17" y="12" width="34" height="60" rx="6" fill="#2B3A31" />
    <rect x="30" y="44" width="48" height="22" rx="6" fill="#fff" stroke={GS} strokeWidth="2" /><rect x="34" y="48" width="14" height="14" rx="3" fill={GS} />
    <rect x="51" y="49" width="22" height="4" rx="2" fill={INK} /><rect x="51" y="56" width="14" height="4" rx="2" fill={G} />
    <circle cx="70" cy="30" r="9" fill={G} /><path d="M70 25.5v9M65.5 30h9" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" />
  </svg>
)
const ArtChat = () => (
  <svg width="84" height="84" viewBox="0 0 84 84" aria-hidden="true">
    <rect x="6" y="12" width="52" height="30" rx="10" fill={GS} /><path d="M14 42l-2 10 10-10z" fill={GS} />
    <rect x="14" y="21" width="30" height="4" rx="2" fill={GD} /><rect x="14" y="29" width="20" height="4" rx="2" fill={GD} opacity=".6" />
    <rect x="28" y="44" width="50" height="28" rx="10" fill={G} /><path d="M70 72l2 9-10-9z" fill={G} />
    <rect x="36" y="53" width="28" height="4" rx="2" fill="#fff" /><rect x="36" y="61" width="18" height="4" rx="2" fill="#fff" opacity=".75" />
  </svg>
)
const ArtStore = () => (
  <svg width="84" height="84" viewBox="0 0 84 84" aria-hidden="true">
    <rect x="10" y="30" width="64" height="46" rx="6" fill="#fff" stroke={GS} strokeWidth="2" /><path d="M8 30l6-16h56l6 16z" fill={G} />
    <path d="M8 30h17v3a8.5 8.5 0 0 1-17 0zM25 30h17v3a8.5 8.5 0 0 1-17 0zM42 30h17v3a8.5 8.5 0 0 1-17 0zM59 30h17v3a8.5 8.5 0 0 1-17 0z" fill={GD} />
    <rect x="17" y="46" width="14" height="14" rx="3" fill={GS} /><rect x="35" y="46" width="14" height="14" rx="3" fill="#FFEDE6" /><rect x="53" y="46" width="14" height="14" rx="3" fill={GS} />
    <rect x="17" y="63" width="14" height="6" rx="2" fill={INK} opacity=".15" /><rect x="35" y="63" width="14" height="6" rx="2" fill={INK} opacity=".15" /><rect x="53" y="63" width="14" height="6" rx="2" fill={INK} opacity=".15" />
  </svg>
)
const ArtCreator = () => (
  <svg width="84" height="84" viewBox="0 0 84 84" aria-hidden="true">
    <rect x="10" y="26" width="46" height="36" rx="8" fill={INK} /><path d="M56 38l16-9v30l-16-9z" fill={INK} />
    <circle cx="33" cy="44" r="10" fill="#2B3A31" /><circle cx="33" cy="44" r="5" fill={G} />
    <path d="M66 8l3 6.2 6.8 1-4.9 4.8 1.2 6.8L66 23.6l-6.1 3.2 1.2-6.8-4.9-4.8 6.8-1z" fill="#F5B83D" />
  </svg>
)

const STEPS = [[ArtShoot, 'step1'], [ArtAttach, 'step2'], [ArtChat, 'step3']]

/** Что такое шопсы и витрина — на странице «Новый шопс», пока видео не выбрано (как в приложении). */
export default function ShopsExplainer() {
  const { t } = useTranslation()
  return (
    <div className="shx">
      <h2 className="shx-h2">{t('shx.title')}</h2>
      <p className="shx-lead">{t('shx.lead')}</p>
      {STEPS.map(([Art, k], i) => (
        <div key={k} className="shx-step">
          <div className="shx-art"><Art /></div>
          <div className="shx-text"><span className="shx-n">{i + 1}</span><div className="shx-title">{t(`shx.${k}_t`)}</div><div className="shx-desc">{t(`shx.${k}_d`)}</div></div>
        </div>
      ))}
      <h2 className="shx-h2 shx-gap">{t('shx.why')}</h2>
      {['why1', 'why2', 'why3'].map((k) => (
        <div key={k} className="shx-bullet">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke={G} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
          <span>{t(`shx.${k}`)}</span>
        </div>
      ))}
      <Link className="shx-card shx-gap" to="/vitrina">
        <div className="shx-art"><ArtStore /></div>
        <div className="shx-text"><div className="shx-title">{t('shx.store_t')}</div><div className="shx-desc">{t('shx.store_d')}</div><span className="shx-link">{t('sf.my')} ›</span></div>
      </Link>
      <Link className="shx-card" to="/shops/mine?tab=creator">
        <div className="shx-art"><ArtCreator /></div>
        <div className="shx-text"><div className="shx-title">{t('shx.creator_t')}</div><div className="shx-desc">{t('shx.creator_d')}</div><span className="shx-link">{t('shx.creator_go')} ›</span></div>
      </Link>
    </div>
  )
}
