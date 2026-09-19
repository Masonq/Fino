import { useTranslation } from 'react-i18next'

/**
 * Подсказка: в описании нашёлся телефон или ник.
 *
 * Продавцу кажется, что так быстрее, а выходит наоборот: переписка
 * уходит мимо сайта, и вместе с ней уходит всё, ради чего сюда
 * приходят — история сделки, отзыв, возможность пожаловаться. Номер в
 * тексте к тому же не спрятать: он остаётся в поиске навсегда.
 *
 * Поэтому не запрещаем, а показываем, что нашли, и предлагаем убрать
 * одним нажатием. Запрет человек обходит пробелами и словами, а
 * объяснение — читает.
 */
const PHONE = /(?<![\w])(?:\+?\d[\d\s().-]{8,17}\d)(?![\w])/g
const CONTACT = /(@[a-zA-Z][a-zA-Z0-9_]{3,}|(?:https?:\/\/)?(?:t\.me|wa\.me|telegram\.me)\/\S+)/gi

export function findContacts(text) {
  const body = text || ''
  const found = [...body.matchAll(PHONE), ...body.matchAll(CONTACT)]
    .map((m) => m[0].trim())
  return [...new Set(found)].slice(0, 3)
}

export function stripContacts(text) {
  return (text || '')
    .replace(CONTACT, ' ')
    .replace(PHONE, ' ')
    .split('\n')
    .map((line) => line.replace(/\s{2,}/g, ' ').trim())
    .filter((line, i, all) => line || (i > 0 && all[i - 1]))
    .join('\n')
    .trim()
}

export default function ContactHint({ text, onFix }) {
  const { t } = useTranslation()
  const found = findContacts(text)
  if (!found.length) return null

  return (
    <div className="contact-hint">
      <div className="contact-hint-text">
        {t('post.contact_hint', { found: found.join(', ') })}
      </div>
      <button type="button" onClick={() => onFix(stripContacts(text))}>
        {t('post.contact_fix')}
      </button>
    </div>
  )
}
