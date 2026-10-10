import { tr } from '../i18n'
import { Ionicons } from '@expo/vector-icons'
import * as Linking from 'expo-linking'
import { StyleSheet, Text, View } from 'react-native'
import Pressable from './Pressable'
import { SafeAreaView } from 'react-native-safe-area-context'

import { SITE } from '../config'
import { colors, font } from '../theme'

type IconName = keyof typeof Ionicons.glyphMap

/** Раздел, который в приложении появится на следующих этапах: честно говорим об этом и ведём на сайт. */
export default function OnSite({ icon, title, text, path }: { icon: IconName; title: string; text: string; path: string }) {
  return (
    <SafeAreaView style={styles.page} edges={['top']}>
      <View style={styles.box}>
        <View style={styles.circle}><Ionicons name={icon} size={30} color={colors.primaryDeep} /></View>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.text}>{text}</Text>
        <Pressable style={styles.btn} onPress={() => Linking.openURL(`${SITE}${path}`)} accessibilityRole="link">
          <Text style={styles.btnText}>{tr('Открыть на сайте')}</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  box: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 10 },
  circle: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center', marginBottom: 4 },
  title: { fontSize: 20, fontFamily: font[800], color: colors.ink, textAlign: 'center' },
  text: { fontFamily: font[400], fontSize: 15, lineHeight: 21, color: colors.inkSoft, textAlign: 'center' },
  btn: { marginTop: 10, height: 48, paddingHorizontal: 22, borderRadius: 14, backgroundColor: colors.inverse, alignItems: 'center', justifyContent: 'center' },
  btnText: { color: colors.onInverse, fontSize: 15.5, fontFamily: font[800] },
})
