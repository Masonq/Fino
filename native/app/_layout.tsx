import { Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import * as Updates from 'expo-updates'
import { useEffect } from 'react'
import { AppState } from 'react-native'
import { SafeAreaProvider } from 'react-native-safe-area-context'

import { AuthProvider } from '../src/auth'
import { ChatsProvider } from '../src/chats'
import { FavoritesProvider } from '../src/favorites'

import { colors } from '../src/theme'

/**
 * Обновления приходят сами (expo-updates, сервер plonk.rs): при запуске приложение проверяет новую версию и
 * применяет её при следующем открытии. А если приложение пролежало в фоне дольше 10 минут — проверяем при
 * возвращении и, если есть новое, перезапускаемся сразу: незачем ждать следующего холодного запуска.
 */
function useUpdatesOnResume() {
  useEffect(() => {
    if (__DEV__ || !Updates.isEnabled) return undefined
    let leftAt = 0
    const sub = AppState.addEventListener('change', async (state) => {
      if (state === 'background') { leftAt = Date.now(); return }
      if (state !== 'active' || !leftAt || Date.now() - leftAt < 10 * 60 * 1000) return
      leftAt = 0
      try {
        const check = await Updates.checkForUpdateAsync()
        if (!check.isAvailable) return
        await Updates.fetchUpdateAsync()
        await Updates.reloadAsync()
      } catch {
        // нет сети или сервер недоступен — попробуем при следующем возвращении
      }
    })
    return () => sub.remove()
  }, [])
}

export default function RootLayout() {
  useUpdatesOnResume()
  return (
    <SafeAreaProvider>
      <AuthProvider>
      <FavoritesProvider>
      <ChatsProvider>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg }, animation: 'slide_from_right' }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="listing/[id]" />
        <Stack.Screen name="chat/[id]" />
        <Stack.Screen name="login" options={{ presentation: 'modal', animation: 'slide_from_bottom' }} />
      </Stack>
      </ChatsProvider>
      </FavoritesProvider>
      </AuthProvider>
    </SafeAreaProvider>
  )
}
