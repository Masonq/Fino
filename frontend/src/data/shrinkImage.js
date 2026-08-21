/**
 * Уменьшает фотографию перед отправкой.
 *
 * Снимок с телефона весит 5–10 МБ, а показываем мы его максимум в 1600
 * точек. На мобильном интернете десять таких снимков — несколько минут
 * ожидания и лишний трафик. Уменьшаем прямо на устройстве: качество для
 * объявления не страдает, а отправка ускоряется в разы.
 */
const MAX_DIM = 1800     // с запасом относительно серверных 1600
const QUALITY = 0.86
const SKIP_UNDER = 600 * 1024   // мелкие не трогаем

export async function shrinkImage(file) {
  // не изображение или уже маленькое — отправляем как есть
  if (!file.type.startsWith('image/') || file.size < SKIP_UNDER) return file
  // эти форматы браузер может не уметь пересобирать
  if (file.type === 'image/gif' || file.type === 'image/svg+xml') return file

  try {
    const bitmap = await createImageBitmap(file)
    const { width, height } = bitmap

    const scale = Math.min(1, MAX_DIM / Math.max(width, height))
    if (scale === 1 && file.size < 2 * 1024 * 1024) {
      bitmap.close?.()
      return file
    }

    const canvas = document.createElement('canvas')
    canvas.width = Math.round(width * scale)
    canvas.height = Math.round(height * scale)

    const ctx = canvas.getContext('2d')
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    bitmap.close?.()

    const blob = await new Promise((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', QUALITY),
    )
    if (!blob || blob.size >= file.size) return file   // не помогло — не портим

    return new File([blob], file.name.replace(/\.\w+$/, '.jpg'), {
      type: 'image/jpeg',
      lastModified: Date.now(),
    })
  } catch {
    // старый браузер или необычный формат — пусть сервер разбирается
    return file
  }
}
