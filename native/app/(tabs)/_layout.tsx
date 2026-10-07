import { select } from '../../src/haptics'
import Icon, { Star } from '../../src/components/Icon'
import { tr } from '../../src/i18n'
import { Tabs } from 'expo-router'
import { NativeTabs } from 'expo-router/unstable-native-tabs'
import { type ColorValue, Platform, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { useChats } from '../../src/chats'
import { colors, font } from '../../src/theme'


// Размеры — как у нижнего меню сайта (.nav-item): иконки 27, подписи 11,5 полужирные (активная — жирная),
// «Разместить» — оранжевый круг 34 с плюсом 20 и мягкой тенью.
const ICON = 27
const LABEL = 11.5
// Высота меню, как у сайта: 10 сверху + иконка 27 + 4 + подпись ≈ 14 + 7 снизу. Стандартные 49 точек малы — подписи
// под крупными иконками обрезались.
const BAR = 64

// Значки — как BottomNav сайта: контурные, у активного меняется только цвет линии
const icon = (name: string) => function TabIcon({ color }: { color: ColorValue; focused: boolean }) {
  return <Icon name={name} size={ICON} color={color as string} />
}

/**
 * PLONK 2.0, iOS: родная панель вкладок — на iOS 26 с «жидким стеклом», сворачивается при прокрутке вниз;
 * значки — SF Symbols, у выбранной вкладки — залитый вариант. На Android — своя парящая панель ниже.
 */
function IosTabs() {
  const { unread } = useChats()
  return (
    <NativeTabs tintColor={colors.primary} minimizeBehavior="onScrollDown">
      <NativeTabs.Trigger name="index">
        <NativeTabs.Trigger.Icon sf={{ default: 'house', selected: 'house.fill' }} />
        <NativeTabs.Trigger.Label>{tr('Главная')}</NativeTabs.Trigger.Label>
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="shops">
        <NativeTabs.Trigger.Icon sf={{ default: 'play.rectangle', selected: 'play.rectangle.fill' }} />
        <NativeTabs.Trigger.Label>{tr('Шопсы')}</NativeTabs.Trigger.Label>
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="post">
        <NativeTabs.Trigger.Icon sf={{ default: 'plus.circle', selected: 'plus.circle.fill' }} />
        <NativeTabs.Trigger.Label>{tr('Разместить')}</NativeTabs.Trigger.Label>
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="chats">
        <NativeTabs.Trigger.Icon sf={{ default: 'bubble.left', selected: 'bubble.left.fill' }} />
        <NativeTabs.Trigger.Label>{tr('Сообщения')}</NativeTabs.Trigger.Label>
        {unread > 0 && <NativeTabs.Trigger.Badge>{unread > 99 ? '99+' : String(unread)}</NativeTabs.Trigger.Badge>}
      </NativeTabs.Trigger>
      <NativeTabs.Trigger name="profile">
        <NativeTabs.Trigger.Icon sf={{ default: 'person', selected: 'person.fill' }} />
        <NativeTabs.Trigger.Label>{tr('Профиль')}</NativeTabs.Trigger.Label>
      </NativeTabs.Trigger>
    </NativeTabs>
  )
}

export default function TabsLayout() {
  if (Platform.OS === 'ios') return <IosTabs />
  return <JsTabs />
}

function JsTabs() {
  const insets = useSafeAreaInsets()
  const { unread } = useChats()
  return (
    <Tabs screenListeners={{ tabPress: () => select() }}
      screenOptions={{
      headerShown: false,
      tabBarActiveTintColor: colors.ink,
      tabBarInactiveTintColor: colors.muted,
      // PLONK 2.0: меню — парящая плашка со скруглением, как на сайте (без линии сверху, с мягкой тенью)
      tabBarStyle: {
        backgroundColor: colors.surface, borderTopWidth: 0, borderRadius: 28,
        marginHorizontal: 12, marginBottom: Math.max(insets.bottom - 6, 8), height: BAR, paddingTop: 8, paddingBottom: 8,
        shadowColor: '#0F1512', shadowOpacity: 0.12, shadowRadius: 18, shadowOffset: { width: 0, height: 8 }, elevation: 10,
      },
      tabBarItemStyle: { paddingHorizontal: 0 },
      // Иконка не должна растягиваться и отбирать место у подписи (раньше подпись сжималась до 4 точек)
      tabBarIconStyle: { height: ICON + 2, flexGrow: 0, flexShrink: 0 },
      tabBarAllowFontScaling: false,
      // На самых узких экранах подпись чуть уменьшится, но не обрежется
      // Подпись — как .nav-item сайта: 11,5 / 600, активная 700; длинную («Разместить») слегка ужимаем, а не режем
      tabBarLabel: ({ color, focused, children }) => (
        <Text numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.82} allowFontScaling={false}
          style={{ color, fontSize: LABEL, lineHeight: 14, fontFamily: focused ? font[700] : font[600], marginTop: 3, maxWidth: '100%' }}>{children}</Text>
      ),
      sceneStyle: { backgroundColor: colors.bg },
    }}>
      <Tabs.Screen name="index" options={{ title: tr('Главная'), tabBarIcon: icon('home') }} />
      {/* «Шопсы» — вкладкой, как в TikTok: тёмное меню под тёмной лентой. «Избранное» — сердечко на главной и в профиле */}
      <Tabs.Screen name="shops" options={{
        title: tr('Шопсы'), tabBarIcon: icon('shops'),
        tabBarActiveTintColor: '#fff', tabBarInactiveTintColor: 'rgba(255,255,255,0.6)',
        tabBarStyle: { backgroundColor: '#000', borderTopColor: 'rgba(255,255,255,0.12)', height: BAR + insets.bottom, paddingTop: 8, paddingBottom: Math.max(insets.bottom, 6) },
        sceneStyle: { backgroundColor: '#000' },
      }} />
      <Tabs.Screen name="post" options={{
        title: tr('Разместить'),
        tabBarActiveTintColor: colors.ink,
        tabBarInactiveTintColor: colors.inkSoft,
        tabBarIcon: () => (
          <View style={styles.post}><Icon name="plus" size={22} color={colors.onInverse} /></View>
        ),
      }} />
      <Tabs.Screen name="chats" options={{
        title: tr('Сообщения'), tabBarIcon: icon('chat'),
        tabBarBadge: unread > 0 ? (unread > 99 ? '99+' : unread) : undefined,
        tabBarBadgeStyle: { backgroundColor: colors.accent, color: '#fff', fontSize: 11, fontFamily: font[800] },
      }} />
      <Tabs.Screen name="profile" options={{ title: tr('Профиль'), tabBarIcon: icon('user') }} />
    </Tabs>
  )
}

const styles = StyleSheet.create({
  post: {
    width: 40, height: 40, marginTop: -8, borderRadius: 14, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center',
    shadowColor: colors.ink, shadowOpacity: 0.28, shadowRadius: 8, shadowOffset: { width: 0, height: 5 }, elevation: 5,
  },
})
