import Icon, { Star } from '../../src/components/Icon'
import { tr } from '../../src/i18n'
import { Tabs } from 'expo-router'
import { type ColorValue, StyleSheet, Text, View } from 'react-native'
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

export default function TabsLayout() {
  const insets = useSafeAreaInsets()
  const { unread } = useChats()
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarActiveTintColor: colors.primaryDeep,
      tabBarInactiveTintColor: colors.muted,
      tabBarStyle: {
        backgroundColor: colors.surface, borderTopColor: colors.border,
        height: BAR + insets.bottom, paddingTop: 8, paddingBottom: Math.max(insets.bottom, 6),
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
      <Tabs.Screen name="favorites" options={{ title: tr('Избранное'), tabBarIcon: icon('heart') }} />
      <Tabs.Screen name="post" options={{
        title: tr('Разместить'),
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.inkSoft,
        tabBarIcon: () => (
          <View style={styles.post}><Icon name="plus" size={20} color="#fff" /></View>
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
    width: 34, height: 34, borderRadius: 17, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center',
    shadowColor: colors.accent, shadowOpacity: 0.35, shadowRadius: 6, shadowOffset: { width: 0, height: 4 }, elevation: 4,
  },
})
