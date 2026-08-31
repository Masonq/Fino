export function CardSkeleton({ large = false }) {
  return (
    <div className={large ? 'card-skeleton l-card' : 'card-skeleton'}>
      <div className="sk-photo" />
      <div className="sk-line title" />
      <div className="sk-line price" />
      {/* Настоящая карточка (ListingCard.jsx) рисует .s-attrs — площадь/
          комнаты/год и т.п. — почти у всех объявлений, где эти атрибуты
          заполнены. Скелетон был короче на одну строку: настоящая
          карточка при подгрузке оказывалась выше него, и всё, что ниже
          в сетке, дёргалось вниз. */}
      <div className="sk-line attrs" />
      <div className="sk-line meta" />
    </div>
  )
}

export function CardSkeletons({ count = 4, large = false }) {
  return Array.from({ length: count }).map((_, i) => <CardSkeleton key={i} large={large} />)
}

export function CategorySkeletons({ count = 8 }) {
  return Array.from({ length: count }).map((_, i) => (
    <div className="cat-skeleton" key={i}>
      <div className="sk-cat-line" />
      <div className="sk-cat-glyph" />
    </div>
  ))
}

// Строка с превью-фото слева — «Мои объявления»: тот же my-row/my-thumb/
// my-title/my-price/my-meta, что и у настоящей строки, чтобы при подмене
// список не подрагивал.
export function ListRowSkeleton() {
  return (
    <div className="my-row skeleton">
      <div className="my-main">
        <div className="sk-block my-thumb" />
        <div className="my-body">
          <div className="sk-block sk-line" style={{ height: 13, width: '85%' }} />
          <div className="sk-block sk-line" style={{ height: 13, width: '55%', marginTop: 5 }} />
          <div className="sk-block sk-line" style={{ height: 15.5, width: 70, marginTop: 8 }} />
          <div className="sk-block sk-line" style={{ height: 11.5, width: 90, marginTop: 5 }} />
        </div>
      </div>
    </div>
  )
}

export function ListRowSkeletons({ count = 4 }) {
  return Array.from({ length: count }).map((_, i) => <ListRowSkeleton key={i} />)
}

// Строка без фото — «Сохранённые поиски»: название, описание, ряд
// действий (переключатель + удалить), как в saved-row настоящем.
export function SavedRowSkeleton() {
  return (
    <div className="saved-row skeleton">
      <div className="sk-block sk-line" style={{ height: 14, width: '60%' }} />
      <div className="sk-block sk-line" style={{ height: 12.5, width: '40%', marginTop: 6 }} />
      <div className="saved-actions">
        <div className="sk-block sk-line" style={{ height: 12.5, width: 80 }} />
        <div className="sk-block sk-line" style={{ height: 12.5, width: 50 }} />
      </div>
    </div>
  )
}

export function SavedRowSkeletons({ count = 3 }) {
  return Array.from({ length: count }).map((_, i) => <SavedRowSkeleton key={i} />)
}

// Карточка очереди модерации: полоса фото 112×112 + тело — mod-title/
// mod-price/mod-desc (4 строки)/mod-meta, как у настоящей карточки.
export function ModCardSkeleton() {
  return (
    <div className="mod-card skeleton">
      <div className="mod-photos">
        <div className="sk-block" style={{ width: 112, height: 112, flexShrink: 0 }} />
      </div>
      <div className="mod-body">
        <div className="sk-block sk-line" style={{ height: 11, width: 90, marginBottom: 6 }} />
        <div className="sk-block sk-line" style={{ height: 14.5, width: '75%' }} />
        <div className="sk-block sk-line" style={{ height: 16, width: 70, marginTop: 6 }} />
        <div className="sk-block sk-line" style={{ height: 12.5, width: '100%', marginTop: 9 }} />
        <div className="sk-block sk-line" style={{ height: 12.5, width: '95%', marginTop: 5 }} />
        <div className="sk-block sk-line" style={{ height: 12.5, width: '60%', marginTop: 5 }} />
        <div className="sk-block sk-line" style={{ height: 11.5, width: 110, marginTop: 9 }} />
      </div>
    </div>
  )
}

export function ModCardSkeletons({ count = 3 }) {
  return Array.from({ length: count }).map((_, i) => <ModCardSkeleton key={i} />)
}

// Строка в списке админки (пользователи/жалобы/поддержка) — просто
// имя+тег и строка помельче под ним, без фото.
export function AdminRowSkeleton() {
  return (
    <div className="admin-row skeleton">
      <div className="admin-row-main">
        <div className="sk-block sk-line" style={{ height: 15, width: '50%' }} />
        <div className="sk-block sk-line" style={{ height: 13, width: '70%', marginTop: 6 }} />
      </div>
    </div>
  )
}

export function AdminRowSkeletons({ count = 6 }) {
  return Array.from({ length: count }).map((_, i) => <AdminRowSkeleton key={i} />)
}

// Строка в журнале действий — action+время в одной строке, meta под ней.
export function AuditRowSkeleton() {
  return (
    <div className="audit-row skeleton">
      <div className="audit-head">
        <div className="sk-block sk-line" style={{ height: 14, width: 130 }} />
        <div className="sk-block sk-line" style={{ height: 12, width: 46 }} />
      </div>
      <div className="sk-block sk-line" style={{ height: 13, width: '55%', marginTop: 5 }} />
    </div>
  )
}

export function AuditRowSkeletons({ count = 6 }) {
  return Array.from({ length: count }).map((_, i) => <AuditRowSkeleton key={i} />)
}

// Карточки-показатели в статистике: цифра+подпись, шесть штук сеткой
// 2×3 — та же сетка, что у настоящих stats-cards.
export function StatsCardsSkeleton() {
  return (
    <div className="stats-cards">
      {Array.from({ length: 6 }).map((_, i) => (
        <div className="stats-card" key={i}>
          <div className="sk-block sk-line" style={{ height: 24, width: 40 }} />
          <div className="sk-block sk-line" style={{ height: 13, width: '70%', marginTop: 6 }} />
        </div>
      ))}
    </div>
  )
}

// Строка «показатель: число» в блоке качества/разделов/источников.
function StatsRowSkeleton() {
  return (
    <div className="stats-row">
      <div className="sk-block sk-line" style={{ height: 14, width: '55%' }} />
      <div className="sk-block sk-line" style={{ height: 14, width: 36 }} />
    </div>
  )
}

// Вся страница статистики целиком: карточки, столбики графика по дням
// (тот же stats-bars, что и у настоящего) и три блока строк — те же
// контейнеры (stats-block/stats-rows), что настоящая страница
// собирает вокруг данных.
export function AdminStatsSkeleton() {
  const bars = [40, 65, 30, 80, 55, 70, 45, 60, 35, 75, 50, 90, 42, 58]
  return (
    <>
      <StatsCardsSkeleton />
      <div className="stats-block">
        <div className="sk-block sk-line" style={{ height: 14, width: 100, marginBottom: 10 }} />
        <div className="stats-bars">
          {bars.map((h, i) => (
            <div className="stats-bar" key={i}>
              <div className="stats-bar-track">
                <div className="sk-block" style={{ width: '100%', height: `${h}%`, borderRadius: '4px 4px 0 0' }} />
              </div>
            </div>
          ))}
        </div>
      </div>
      {[4, 5, 4].map((rows, block) => (
        <div className="stats-block" key={block}>
          <div className="sk-block sk-line" style={{ height: 14, width: 90, marginBottom: 10 }} />
          <div className="stats-rows">
            {Array.from({ length: rows }).map((_, i) => <StatsRowSkeleton key={i} />)}
          </div>
        </div>
      ))}
    </>
  )
}

// Шапка профиля — круглый аватар + имя + контакт, дальше пункты меню.
export function ProfileSkeleton({ showStaff = false }) {
  return (
    <>
      <div className="profile-head-card">
        <div className="profile-head">
          <div className="sk-block" style={{ width: 66, height: 66, borderRadius: '50%', flexShrink: 0 }} />
          <div className="profile-info" style={{ flex: 1 }}>
            {/* Реальные строки — не просто высота шрифта, а высота
                строки целиком (с междустрочным интервалом): 17px
                шрифт занимает на экране заметно больше 17px. Раньше
                блоки были ровно по font-size — из-за этого, плюс
                недостающей четвёртой строки (у email И phone разные
                условия в коде, оба могут быть заполнены одновременно —
                частый случай), настоящая шапка была на 148px выше
                своего скелетона — измерено по кадрам записи экрана,
                не на глаз. Резервируем сразу 4 строки (имя + два
                контакта + рейтинг), с запасом по высоте и отступам —
                лучше скелетон будет чуть выше настоящей карточки для
                тех, у кого заполнен только email ИЛИ только phone
                (редкая небольшая просадка), чем ниже для частого
                случая «оба контакта заполнены» (какой был здесь). */}
            <div className="sk-block sk-line" style={{ height: 24, width: '60%' }} />
            <div className="sk-block sk-line" style={{ height: 18, width: '75%', marginTop: 6 }} />
            <div className="sk-block sk-line" style={{ height: 18, width: '40%', marginTop: 6 }} />
            <div className="sk-block sk-line" style={{ height: 18, width: '45%', marginTop: 6 }} />
          </div>
        </div>
        {/* .profile-edit-btn — не показан условно, есть всегда. */}
        <div className="sk-block sk-line" style={{ height: 44, margin: 0 }} />
      </div>
      {/* BalanceCard — отдельный компонент под карточкой профиля, тоже
          рендерится всегда (значение баланса грузится своим запросом
          внутри него, но сама карточка — сразу). */}
      <div className="balance-card">
        <div className="balance-row">
          <div>
            <div className="sk-block sk-line" style={{ height: 12, width: 60 }} />
            <div className="sk-block sk-line" style={{ height: 19, width: 90, marginTop: 5 }} />
          </div>
          <div className="sk-block sk-line" style={{ height: 38, width: 110 }} />
        </div>
      </div>
      {/* Настоящее меню — четыре подписанные группы (Объявления x2,
          Активность x1, Настройки x2, Информация x4), не единый список.
          Раньше скелетон рисовал плоские 7 строк без заголовков секций —
          и по числу строк (7 вместо 9), и по структуре (без
          .profile-section-title, у которого свой отступ) настоящее меню
          оказывалось заметно длиннее скелетона. */}
      {[2, 1, 2, 4].map((rows, group) => (
        <div key={group}>
          <div className="profile-section-title">
            <div className="sk-block sk-line" style={{ height: 10, width: 70 }} />
          </div>
          <div className="profile-menu">
            {Array.from({ length: rows }).map((_, i) => (
              <div className="profile-row" key={i}>
                <div className="sk-block" style={{ width: 32, height: 32, borderRadius: 10, flexShrink: 0 }} />
                <div className="sk-block sk-line" style={{ height: 14.5, width: 120 }} />
              </div>
            ))}
          </div>
        </div>
      ))}
      {/* Пятая группа — только у модераторов/админов (условие в
          Profile.jsx: user.role === 'moderator' || 'admin'). В момент
          показа скелетона user ещё не загружен, роль неоткуда взять
          напрямую — но AuthContext помнит роль с прошлого раза
          (lastKnownRole), и для тех, кто уже открывал профиль будучи
          модератором/админом, скелетон теперь резервирует и её. Для
          обычного пользователя lastKnownRole не совпадёт — эта секция
          просто не рендерится, как и раньше. */}
      {showStaff && (
        <div>
          <div className="profile-section-title">
            <div className="sk-block sk-line" style={{ height: 10, width: 70 }} />
          </div>
          <div className="profile-menu">
            {Array.from({ length: 5 }).map((_, i) => (
              <div className="profile-row" key={i}>
                <div className="sk-block" style={{ width: 32, height: 32, borderRadius: 10, flexShrink: 0 }} />
                <div className="sk-block sk-line" style={{ height: 14.5, width: 120 }} />
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

// Переписка, пока не пришёл первый ответ сервера — чередующиеся
// пузыри своя/чужая сторона, как в живом чате.
export function ChatSkeleton() {
  const widths = [62, 74, 48, 82, 58]
  return (
    <>
      {widths.map((w, i) => (
        <div key={i} className={i % 2 ? 'chat-bubble mine skeleton' : 'chat-bubble skeleton'}>
          <div className="sk-block sk-line" style={{ height: 14, width: `${w}%` }} />
        </div>
      ))}
    </>
  )
}

// Форма правки объявления: заголовок, описание, цена+город в ряд,
// чекбокс, кнопки — те же post-field/post-field-row/edit-actions, что
// у настоящей формы.
export function EditFormSkeleton() {
  return (
    <div className="post-fields edit-fields">
      <div className="post-field">
        <div className="sk-block sk-line" style={{ height: 12, width: 70 }} />
        <div className="sk-block sk-line" style={{ height: 45, marginTop: 6 }} />
      </div>
      <div className="post-field">
        <div className="sk-block sk-line" style={{ height: 12, width: 100 }} />
        <div className="sk-block sk-line" style={{ height: 110, marginTop: 6 }} />
      </div>
      <div className="post-field-row">
        <div className="post-field">
          <div className="sk-block sk-line" style={{ height: 12, width: 50 }} />
          <div className="sk-block sk-line" style={{ height: 45, marginTop: 6 }} />
        </div>
        <div className="post-field">
          <div className="sk-block sk-line" style={{ height: 12, width: 40 }} />
          <div className="sk-block sk-line" style={{ height: 45, marginTop: 6 }} />
        </div>
      </div>
      <div className="sk-block sk-line" style={{ height: 19, width: 160 }} />
      <div className="edit-actions">
        <div className="sk-block sk-line" style={{ height: 51 }} />
        <div className="sk-block sk-line" style={{ height: 51 }} />
      </div>
    </div>
  )
}

// Блок отзывов продавца (SellerReviews) — заголовок+рейтинг, и три
// строки отзыва (автор+звёзды, текст в две строки) — reviews-head/
// review-row/review-top/review-text, как у настоящего блока.
export function ReviewsSkeleton() {
  return (
    <div className="reviews-block">
      <div className="reviews-head">
        <div>
          <div className="sk-block sk-line" style={{ height: 15, width: 90 }} />
          <div className="sk-block sk-line" style={{ height: 15, width: 130, marginTop: 6 }} />
        </div>
      </div>
      <div className="reviews-list">
        {Array.from({ length: 3 }).map((_, i) => (
          <div className="review-row" key={i}>
            <div className="sk-block sk-line" style={{ height: 13, width: 120 }} />
            <div className="sk-block sk-line" style={{ height: 13, width: '95%', marginTop: 7 }} />
            <div className="sk-block sk-line" style={{ height: 13, width: '70%', marginTop: 5 }} />
          </div>
        ))}
      </div>
    </div>
  )
}

