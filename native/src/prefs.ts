import * as SecureStore from 'expo-secure-store'
import { Platform } from 'react-native'

/** Маленькие настройки на телефоне (выбранный город). В веб-превью — хранилище браузера. */
export const prefs = Platform.OS === 'web'
  ? {
      get: async (k: string) => globalThis.localStorage?.getItem(k) ?? null,
      set: async (k: string, v: string) => { globalThis.localStorage?.setItem(k, v) },
    }
  : {
      get: (k: string) => SecureStore.getItemAsync(k).catch(() => null),
      set: (k: string, v: string) => SecureStore.setItemAsync(k, v).catch(() => {}),
    }
