import { Ionicons } from '@expo/vector-icons'
import { Tabs } from 'expo-router'
import { type ColorValue, StyleSheet, Text, useWindowDimensions, View } from 'react-native'

import { colors } from '../../src/theme'

type IconName = keyof typeof Ionicons.glyphMap

const icon = (on: IconName, off: IconName) => function TabIcon({ color, focused }: { color: ColorValue; focused: boolean }) {
  return <Ionicons name={focused ? on : off} size={24} color={color as string} />
}

export default function TabsLayout() {
  // На узких экранах (до 360 точек) пять подписей помещаются только чуть меньшим шрифтом
  const { width } = useWindowDimensions()
  const labelSize = width < 340 ? 9 : width < 380 ? 10 : 10.5
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarActiveTintColor: colors.primaryDeep,
      tabBarInactiveTintColor: colors.muted,
      // Пять подписей должны помещаться целиком и на узком экране: без внутренних отступов у пунктов и чуть мельче
      tabBarLabelStyle: { fontSize: labelSize, fontWeight: '700', marginHorizontal: 0 },
      tabBarItemStyle: { paddingHorizontal: 0 },
      tabBarAllowFontScaling: false,
      // Страховка: если подпись не влезает (крупный системный шрифт, узкий экран) — телефон слегка уменьшит её, а не обрежет
      tabBarLabel: ({ color, children }) => (
        <Text numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.8} allowFontScaling={false}
          style={{ color, fontSize: labelSize, fontWeight: '700' }}>{children}</Text>
      ),
      tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
      sceneStyle: { backgroundColor: colors.bg },
    }}>
      <Tabs.Screen name="index" options={{ title: 'Главная', tabBarIcon: icon('home', 'home-outline') }} />
      <Tabs.Screen name="favorites" options={{ title: 'Избранное', tabBarIcon: icon('heart', 'heart-outline') }} />
      <Tabs.Screen name="post" options={{
        title: 'Разместить',
        tabBarIcon: () => (
          <View style={styles.post}><Ionicons name="add" size={24} color="#fff" /></View>
        ),
      }} />
      <Tabs.Screen name="chats" options={{ title: 'Сообщения', tabBarIcon: icon('chatbubble', 'chatbubble-outline') }} />
      <Tabs.Screen name="profile" options={{ title: 'Профиль', tabBarIcon: icon('person', 'person-outline') }} />
    </Tabs>
  )
}

const styles = StyleSheet.create({
  post: { width: 34, height: 34, borderRadius: 17, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center' },
})
