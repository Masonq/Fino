import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

/**
 * Подвал — до сих пор его не было вовсе: правовые документы,
 * поддержка и правила существовали (/terms, /privacy, /rules,
 * /support), но попасть на них можно было только зная адрес наизусть
 * или через профиль. Плюс на десктопе страница просто обрывалась
 * снизу без всякого завершения.
 *
 * На мобильном скрыт: там снизу экрана прибито своё меню (BottomNav),
 * и подвал под ним оказался бы недосягаемым — см. styles.css.
 */
export default function Footer() {
  const { t } = useTranslation()
  const year = new Date().getFullYear()

  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="footer-col">
          <div className="footer-brand">PLONK</div>
          <p className="footer-about">{t('footer.about')}</p>
        </div>

        <div className="footer-col">
          <div className="footer-title">{t('footer.sec_marketplace')}</div>
          <Link to="/categories">{t('footer.categories')}</Link>
          <Link to="/post">{t('footer.post_ad')}</Link>
          <Link to="/search">{t('footer.search')}</Link>
        </div>

        <div className="footer-col">
          <div className="footer-title">{t('footer.sec_help')}</div>
          <Link to="/support">{t('footer.support')}</Link>
          <Link to="/rules">{t('footer.rules')}</Link>
        </div>

        <div className="footer-col">
          <div className="footer-title">{t('footer.sec_legal')}</div>
          <Link to="/terms">{t('footer.terms')}</Link>
          <Link to="/privacy">{t('footer.privacy')}</Link>
        </div>
      </div>

      <div className="site-footer-bottom">
        <span>© {year} PLONK</span>
        <span className="footer-sep">·</span>
        <span>{t('footer.made_in')}</span>
      </div>
    </footer>
  )
}
