import { Platform } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

/** iOS: родная панель вкладок полупрозрачная и лежит поверх экрана — низ списков приподнимаем над ней. */
export function useTabInset() {
  const insets = useSafeAreaInsets()
  return Platform.OS === 'ios' ? insets.bottom + 56 : 0
}
