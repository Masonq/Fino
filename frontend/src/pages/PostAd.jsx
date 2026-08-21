import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

const STEPS = ['category', 'attributes', 'details', 'contact']

export default function PostAd() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()

  const [step, setStep] = useState(0)
  const [categories, setCategories] = useState([])
  const [category, setCategory] = useState(null)
  const [schema, setSchema] = useState([])
  const [attrs, setAttrs] = useState({})

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('')
  const [currency, setCurrency] = useState('EUR')
  const [negotiable, setNegotiable] = useState(false)
  const [city, setCity] = useState('')
  const [photoUrl, setPhotoUrl] = useState('')

  const [phone, setPhone] = useState('')
  const [displayName, setDisplayName] = useState('')

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [done, setDone] = useState(false)

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => setCategories([]))
  }, [])

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [step])

  const pickCategory = async (cat) => {
    setCategory(cat)
    try {
      const res = await api.getCategorySchema(cat.slug)
      setSchema(res.attribute_schema || [])
      setAttrs({})
    } catch {
      setSchema([])
    }
    setStep(1)
  }

  const setAttr = (key, value) => setAttrs((prev) => ({ ...prev, [key]: value }))

  const requiredAttrsFilled = schema
    .filter((f) => f.required)
    .every((f) => attrs[f.key] !== undefined && attrs[f.key] !== '')

  const handleSubmit = async () => {
    setError(null)
    setSubmitting(true)
    try {
      let ownerId = localStorage.getItem('fino_user_id')
      if (!ownerId) {
        const user = await api.quickIdentify(phone, displayName)
        ownerId = user.id
        localStorage.setItem('fino_user_id', ownerId)
      }

      await api.createListing({
        category_id: category.id,
        source_language: i18n.language,
        price: price ? Number(price) : null,
        currency,
        price_negotiable: negotiable,
        attributes: attrs,
        city,
        translations: [{ language: i18n.language, title, description }],
      }, ownerId)

      setDone(true)
    } catch (e) {
      setError('Не удалось опубликовать. Проверьте подключение и попробуйте снова.')
    } finally {
      setSubmitting(false)
    }
  }

  if (done) {
    return (
      <div className="post-ad-page post-success">
        <div className="seal" style={{ width: 56, height: 56, margin: '0 auto 16px' }}>
          <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.4"><path d="M20 6 9 17l-5-5" /></svg>
        </div>
        <h2>Объявление отправлено на модерацию</h2>
        <p className="empty-hint">Обычно проверка занимает немного времени. Оно появится в ленте, как только пройдёт модерацию.</p>
        <button className="post-submit-btn" onClick={() => navigate('/')}>На главную</button>
      </div>
    )
  }

  return (
    <div className="post-ad-page">
      <div className="post-steps">
        {STEPS.map((s, i) => (
          <div key={s} className={i <= step ? 'post-step-dot active' : 'post-step-dot'} />
        ))}
      </div>

      {step === 0 && (
        <>
          <h2>{t('listing.select_category')}</h2>
          <div className="post-cat-grid">
            {categories.map((cat) => (
              <button key={cat.id} className="post-cat-item" onClick={() => pickCategory(cat)}>
                <div className="post-cat-photo">
                  {cat.image_url && <img src={cat.image_url} alt="" />}
                </div>
                <span>{cat.name?.[i18n.language] || cat.name?.ru}</span>
              </button>
            ))}
          </div>
        </>
      )}

      {step === 1 && category && (
        <>
          <button className="post-back" onClick={() => setStep(0)}>← {category.name?.[i18n.language] || category.name?.ru}</button>
          <h2>Параметры</h2>
          {schema.length === 0 && <p className="empty-hint">У этой категории пока нет доп. параметров — переходите дальше.</p>}
          <div className="post-fields">
            {schema.map((field) => (
              <div key={field.key} className="post-field">
                <label>{field.label?.[i18n.language] || field.label?.ru || field.key}{field.required && ' *'}</label>
                {field.type === 'text' && (
                  <input type="text" value={attrs[field.key] || ''} onChange={(e) => setAttr(field.key, e.target.value)} />
                )}
                {field.type === 'number' && (
                  <input type="number" value={attrs[field.key] || ''} onChange={(e) => setAttr(field.key, e.target.value)} />
                )}
                {field.type === 'boolean' && (
                  <label className="post-checkbox">
                    <input type="checkbox" checked={!!attrs[field.key]} onChange={(e) => setAttr(field.key, e.target.checked)} />
                    {field.label?.[i18n.language] || field.label?.ru}
                  </label>
                )}
                {field.type === 'select' && (
                  <select value={attrs[field.key] || ''} onChange={(e) => setAttr(field.key, e.target.value)}>
                    <option value="" disabled>—</option>
                    {field.options?.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label?.[i18n.language] || opt.label?.ru}</option>
                    ))}
                  </select>
                )}
              </div>
            ))}
          </div>
          <button className="post-submit-btn" disabled={!requiredAttrsFilled} onClick={() => setStep(2)}>Далее</button>
        </>
      )}

      {step === 2 && (
        <>
          <button className="post-back" onClick={() => setStep(1)}>← Назад</button>
          <h2>Описание и фото</h2>
          <div className="post-fields">
            <div className="post-field">
              <label>{t('listing.title')} *</label>
              <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Например: 2-комнатная квартира с балконом" />
            </div>
            <div className="post-field">
              <label>{t('listing.description')}</label>
              <textarea rows="4" value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div className="post-field">
              <label>Ссылка на фото (загрузка файлов появится позже)</label>
              <input type="text" value={photoUrl} onChange={(e) => setPhotoUrl(e.target.value)} placeholder="https://..." />
            </div>
            <div className="post-field-row">
              <div className="post-field">
                <label>{t('listing.price')}</label>
                <input type="number" value={price} onChange={(e) => setPrice(e.target.value)} />
              </div>
              <div className="post-field" style={{ maxWidth: 90 }}>
                <label>Валюта</label>
                <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
                  <option value="EUR">EUR</option>
                  <option value="RSD">RSD</option>
                </select>
              </div>
            </div>
            <label className="post-checkbox">
              <input type="checkbox" checked={negotiable} onChange={(e) => setNegotiable(e.target.checked)} />
              {t('listing.negotiable')}
            </label>
            <div className="post-field">
              <label>{t('listing.city')}</label>
              <input type="text" value={city} onChange={(e) => setCity(e.target.value)} placeholder="Београд, Врачар" />
            </div>
          </div>
          <button className="post-submit-btn" disabled={!title} onClick={() => setStep(3)}>Далее</button>
        </>
      )}

      {step === 3 && (
        <>
          <button className="post-back" onClick={() => setStep(2)}>← Назад</button>
          <h2>Контакт</h2>
          {localStorage.getItem('fino_user_id') ? (
            <p className="empty-hint">Вы уже публиковали объявление с этого устройства — используем тот же профиль.</p>
          ) : (
            <div className="post-fields">
              <div className="post-field">
                <label>Телефон</label>
                <input type="tel" inputMode="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+381 6..." />
              </div>
              <div className="post-field">
                <label>Имя</label>
                <input type="text" autoComplete="name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Как к вам обращаться" />
              </div>
            </div>
          )}
          {error && <p className="post-error">{error}</p>}
          <button
            className="post-submit-btn"
            disabled={submitting || (!localStorage.getItem('fino_user_id') && (!phone || !displayName))}
            onClick={handleSubmit}
          >
            {submitting ? '...' : t('listing.publish')}
          </button>
        </>
      )}
    </div>
  )
}
