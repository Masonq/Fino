import { Ionicons } from '@expo/vector-icons'
import { Tabs } from 'expo-router'
import { type ColorValue, StyleSheet, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { colors } from '../../src/theme'

type IconName = keyof typeof Ionicons.glyphMap

// Размеры — как у нижнего меню сайта (.nav-item): иконки 27, подписи 11,5 полужирные (активная — жирная),
// «Разместить» — оранжевый круг 34 с плюсом 20 и мягкой тенью.
const ICON = 27
const LABEL = 11.5
// Высота меню, как у сайта: 10 сверху + иконка 27 + 4 + подпись ≈ 14 + 7 снизу. Стандартные 49 точек малы — подписи
// под крупными иконками обрезались.
const BAR = 64

const icon = (on: IconName, off: IconName) => function TabIcon({ color, focused }: { color: ColorValue; focused: boolean }) {
  return <Ionicons name={focused ? on : off} size={ICON} color={color as string} />
}

export default function TabsLayout() {
  const insets = useSafeAreaInsets()
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
      tabBarLabel: ({ color, focused, children }) => (
        <Text numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.82} allowFontScaling={false}
          style={{ color, fontSize: LABEL, lineHeight: 14, fontWeight: focused || children === 'Разместить' ? '700' : '600', marginTop: 3, flexShrink: 0 }}>{children}</Text>
      ),
      sceneStyle: { backgroundColor: colors.bg },
    }}>
      <Tabs.Screen name="index" options={{ title: 'Главная', tabBarIcon: icon('home', 'home-outline') }} />
      <Tabs.Screen name="favorites" options={{ title: 'Избранное', tabBarIcon: icon('heart', 'heart-outline') }} />
      <Tabs.Screen name="post" options={{
        title: 'Разместить',
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.inkSoft,
        tabBarIcon: () => (
          <View style={styles.post}><Ionicons name="add" size={20} color="#fff" /></View>
        ),
      }} />
      <Tabs.Screen name="chats" options={{ title: 'Сообщения', tabBarIcon: icon('chatbubble', 'chatbubble-outline') }} />
      <Tabs.Screen name="profile" options={{ title: 'Профиль', tabBarIcon: icon('person', 'person-outline') }} />
    </Tabs>
  )
}

const styles = StyleSheet.create({
  post: {
    width: 34, height: 34, borderRadius: 17, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center',
    shadowColor: colors.accent, shadowOpacity: 0.35, shadowRadius: 6, shadowOffset: { width: 0, height: 4 }, elevation: 4,
  },
})
