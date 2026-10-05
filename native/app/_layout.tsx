// PLONK 2.0: Onest — один шрифт для кириллицы и латиницы (у Plus Jakarta Sans кириллицы не было)
import {
  Onest_400Regular, Onest_500Medium, Onest_600SemiBold, Onest_700Bold, Onest_800ExtraBold, useFonts,
} from '@expo-google-fonts/onest'
import { Stack } from 'expo-router'
import * as SplashScreen from 'expo-splash-screen'
import { StatusBar } from 'expo-status-bar'
import * as Updates from 'expo-updates'
import { useEffect } from 'react'
import { AppState, Platform } from 'react-native'
import { SafeAreaProvider } from 'react-native-safe-area-context'

import { AuthProvider } from '../src/auth'
import CrashGuard from '../src/components/Crash'
import { ChatsProvider } from '../src/chats'
import { FavoritesProvider } from '../src/favorites'
import { LangProvider } from '../src/i18n'
import { NetProvider } from '../src/net'
import OfflineBanner from '../src/components/OfflineBanner'

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

// Заставка держится, пока не загрузятся шрифты сайта — без «прыжка» текста с системного шрифта на фирменный
SplashScreen.preventAutoHideAsync().catch(() => {})

export default function RootLayout() {
  useUpdatesOnResume()
  const [fontsReady, fontsError] = useFonts({
    Onest_400Regular, Onest_500Medium, Onest_600SemiBold, Onest_700Bold, Onest_800ExtraBold,
  })
  useEffect(() => { if (fontsReady || fontsError) SplashScreen.hideAsync().catch(() => {}) }, [fontsReady, fontsError])
  // Шрифты не загрузились — показываем системными, а не висим на заставке
  if (!fontsReady && !fontsError) return null
  return (
    <CrashGuard>
    <NetProvider>
    <SafeAreaProvider>
      <AuthProvider>
      <FavoritesProvider>
      <ChatsProvider>
      <StatusBar style="dark" />
      <LangProvider>{(lang) => (
      <Stack key={lang} screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg }, animation: 'slide_from_right' }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="listing/[id]" />
        <Stack.Screen name="chat/[id]" />
        <Stack.Screen name="seller/[id]" />
        <Stack.Screen name="notifications" />
        <Stack.Screen name="saved" />
        <Stack.Screen name="my" />
        <Stack.Screen name="history" />
        <Stack.Screen name="profile-edit" />
        <Stack.Screen name="invite" />
        <Stack.Screen name="blocked" />
        <Stack.Screen name="c/[slug]" />
        <Stack.Screen name="categories" />
        <Stack.Screen name="legal/[doc]" />
        <Stack.Screen name="stats/[id]" />
        <Stack.Screen name="volunteer" />
        <Stack.Screen name="reviews" />
        <Stack.Screen name="support/index" />
        <Stack.Screen name="support/[id]" />
        <Stack.Screen name="edit/[id]" />
        <Stack.Screen name="login" options={{ presentation: 'modal', animation: 'slide_from_bottom' }} />
      </Stack>
      )}</LangProvider>
      <OfflineBanner />
      </ChatsProvider>
      </FavoritesProvider>
      </AuthProvider>
    </SafeAreaProvider>
    </NetProvider>
    </CrashGuard>
  )
}
