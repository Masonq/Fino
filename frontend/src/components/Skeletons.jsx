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

export function CategorySkeletons({ count = 8 }) {
  return Array.from({ length: count }).map((_, i) => (
    <div className="cat-skeleton" key={i}>
      <div className="sk-cat-line" />
      <div className="sk-cat-glyph" />
    </div>
  ))
}
