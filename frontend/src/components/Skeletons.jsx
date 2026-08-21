export function CardSkeleton() {
  return (
    <div className="card-skeleton">
      <div className="sk-photo" />
      <div className="sk-line title" />
      <div className="sk-line price" />
      <div className="sk-line meta" />
    </div>
  )
}

export function CardSkeletons({ count = 4 }) {
  return Array.from({ length: count }).map((_, i) => <CardSkeleton key={i} />)
}

// ширины подобраны под реальные названия категорий, чтобы при подмене ряд не перестраивался
const CAT_SKELETON_WIDTHS = [96, 128, 112, 152, 104, 120, 140, 100, 116, 132]

export function CategorySkeletons({ count = 8, offset = 0 }) {
  return Array.from({ length: count }).map((_, i) => (
    <div
      className="cat-skeleton"
      key={i}
      style={{ width: CAT_SKELETON_WIDTHS[(i + offset) % CAT_SKELETON_WIDTHS.length] }}
    >
      <div className="sk-cat-line" />
      <div className="sk-cat-glyph" />
    </div>
  ))
}
