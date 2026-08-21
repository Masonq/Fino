// Иконки категорий по slug. Вместо фото — чёткие SVG на любом экране, без внешних запросов.
const S = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.9, strokeLinecap: 'round', strokeLinejoin: 'round' }

export const CATEGORY_ICONS = {
  'real-estate': (
    <svg viewBox="0 0 24 24" {...S}><path d="M3 10.5 12 3l9 7.5" /><path d="M5.5 9.8V20h13V9.8" /><path d="M9.8 20v-5.4h4.4V20" /></svg>
  ),
  auto: (
    <svg viewBox="0 0 24 24" {...S}><path d="M5 16.5h14l-1.4-5.6a2.2 2.2 0 0 0-2.1-1.6H8.5a2.2 2.2 0 0 0-2.1 1.6L5 16.5Z" /><path d="M4.5 16.5V19h2.6v-2.5M16.9 16.5V19h2.6v-2.5" /><circle cx="8" cy="16.5" r="1.1" /><circle cx="16" cy="16.5" r="1.1" /></svg>
  ),
  services: (
    <svg viewBox="0 0 24 24" {...S}><path d="M14.6 6.4a3.4 3.4 0 0 0 4.6 4.4l-7.7 7.7a2 2 0 0 1-2.8-2.8l7.7-7.7a3.4 3.4 0 0 0-1.8-1.6Z" /><path d="m6.5 5.5 3 3" /></svg>
  ),
  jobs: (
    <svg viewBox="0 0 24 24" {...S}><rect x="3.2" y="7.5" width="17.6" height="12.5" rx="2.2" /><path d="M8.5 7.5V5.8a1.8 1.8 0 0 1 1.8-1.8h3.4a1.8 1.8 0 0 1 1.8 1.8v1.7" /><path d="M3.2 12.5h17.6" /></svg>
  ),
  electronics: (
    <svg viewBox="0 0 24 24" {...S}><rect x="6.5" y="2.8" width="11" height="18.4" rx="2.4" /><path d="M10.5 5.6h3" /><path d="M11 18.4h2" /></svg>
  ),
  fashion: (
    <svg viewBox="0 0 24 24" {...S}><path d="M9 3.5 6 5.2 4.2 9l2.6 1.4V20h10.4v-9.6L19.8 9 18 5.2 15 3.5" /><path d="M9 3.5a3 3 0 0 0 6 0" /></svg>
  ),
  'home-garden': (
    <svg viewBox="0 0 24 24" {...S}><path d="M4 11.5V17a1.6 1.6 0 0 0 1.6 1.6h12.8A1.6 1.6 0 0 0 20 17v-5.5" /><path d="M4 11.5a2.4 2.4 0 0 1 2.4-2.4h.4V7.5a1.6 1.6 0 0 1 1.6-1.6h7.2a1.6 1.6 0 0 1 1.6 1.6v1.6h.4a2.4 2.4 0 0 1 2.4 2.4" /><path d="M6 18.6V20M18 18.6V20" /></svg>
  ),
  'hobby-sport': (
    <svg viewBox="0 0 24 24" {...S}><circle cx="12" cy="12" r="8.6" /><path d="M12 3.4c2.6 2.3 3.6 5.6 3.6 8.6s-1 6.3-3.6 8.6c-2.6-2.3-3.6-5.6-3.6-8.6s1-6.3 3.6-8.6Z" /><path d="M3.6 12h16.8" /></svg>
  ),
  kids: (
    <svg viewBox="0 0 24 24" {...S}><circle cx="12" cy="8.2" r="3.6" /><path d="M6.5 20.4c0-3 2.5-5.4 5.5-5.4s5.5 2.4 5.5 5.4" /><path d="M8.8 6.2 7 4.4M15.2 6.2 17 4.4" /></svg>
  ),
  pets: (
    <svg viewBox="0 0 24 24" {...S}><ellipse cx="12" cy="16" rx="4" ry="3.4" /><ellipse cx="6.6" cy="11" rx="2" ry="2.6" /><ellipse cx="17.4" cy="11" rx="2" ry="2.6" /><ellipse cx="9.4" cy="6.6" rx="1.8" ry="2.4" /><ellipse cx="14.6" cy="6.6" rx="1.8" ry="2.4" /></svg>
  ),
  beauty: (
    <svg viewBox="0 0 24 24" {...S}><path d="M9.5 3.5h5l.8 5.2a3.4 3.4 0 0 1-.9 2.8l-.6.6v8.4H10v-8.4l-.6-.6a3.4 3.4 0 0 1-.9-2.8L9.5 3.5Z" /><path d="M9 9.4h6" /></svg>
  ),
  business: (
    <svg viewBox="0 0 24 24" {...S}><path d="M4 20V9.5l6-3.4v3.4l6-3.4V20" /><path d="M16 20V4.2l4 2V20" /><path d="M3 20h18" /><path d="M7 13.5v2.2M12 13.5v2.2" /></svg>
  ),
}

export const FALLBACK_ICON = (
  <svg viewBox="0 0 24 24" {...S}><rect x="3.5" y="3.5" width="7" height="7" rx="1.6" /><rect x="13.5" y="3.5" width="7" height="7" rx="1.6" /><rect x="3.5" y="13.5" width="7" height="7" rx="1.6" /><rect x="13.5" y="13.5" width="7" height="7" rx="1.6" /></svg>
)
