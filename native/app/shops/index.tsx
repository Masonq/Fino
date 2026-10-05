import { useLocalSearchParams } from 'expo-router'

import ShopsFeedView from '../../src/components/ShopsFeedView'

/** Лента шопсов, открытая с конкретного ролика (из полосы на главной, витрины или ссылки). */
export default function ShopsScreen() {
  const { start } = useLocalSearchParams<{ start?: string }>()
  return <ShopsFeedView start={start} />
}
