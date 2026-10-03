import * as Haptics from 'expo-haptics'
import { Platform } from 'react-native'

/** Лёгкий отклик на нажатия — как в хороших приложениях iPhone. В веб-превью — ничего. */
const on = Platform.OS !== 'web'
export const tap = () => { if (on) Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {}) }
export const select = () => { if (on) Haptics.selectionAsync().catch(() => {}) }
export const success = () => { if (on) Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {}) }
export const warn = () => { if (on) Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning).catch(() => {}) }
