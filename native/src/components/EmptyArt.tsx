/** Картинка пустого экрана — те же, что на сайте (frontend/public/empty): объёмный предмет без фона. */
import { Image } from 'expo-image'

const ART = {
  'blocked': require('../../assets/empty/blocked.webp'),
  'chats': require('../../assets/empty/chats.webp'),
  'favorites': require('../../assets/empty/favorites.webp'),
  'history': require('../../assets/empty/history.webp'),
  'my': require('../../assets/empty/my.webp'),
  'nothing-found': require('../../assets/empty/nothing-found.webp'),
  'notifications': require('../../assets/empty/notifications.webp'),
  'responses': require('../../assets/empty/responses.webp'),
  'reviews': require('../../assets/empty/reviews.webp'),
  'saved': require('../../assets/empty/saved.webp'),
  'shops': require('../../assets/empty/shops.webp'),
  'vitrina': require('../../assets/empty/vitrina.webp'),
} as const

export type EmptyArtName = keyof typeof ART

export default function EmptyArt({ name, size = 150 }: { name: EmptyArtName; size?: number }) {
  return <Image source={ART[name]} style={{ width: size, height: size, marginBottom: 4 }} contentFit="contain" transition={150} accessibilityElementsHidden />
}
