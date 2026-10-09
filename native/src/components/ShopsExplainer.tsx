import type React from 'react'
import { router } from 'expo-router'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import Svg, { Circle, Path, Rect } from 'react-native-svg'

import { tr } from '../i18n'
import { colors, font } from '../theme'
import Icon from './Icon'

const G = colors.primary, GS = colors.primarySoft, GD = colors.primaryDeep, O = colors.accent, INK = colors.ink

/** Телефон с роликом: вещь в кадре и кнопка «играть». */
const ArtShoot = () => (
  <Svg width={84} height={84} viewBox="0 0 84 84">
    <Rect x={22} y={6} width={40} height={72} rx={9} fill={INK} />
    <Rect x={25} y={12} width={34} height={60} rx={6} fill="#2B3A31" />
    <Rect x={30} y={44} width={24} height={12} rx={3} fill={O} />
    <Rect x={28} y={40} width={6} height={16} rx={2.5} fill="#E5522A" />
    <Rect x={50} y={40} width={6} height={16} rx={2.5} fill="#E5522A" />
    <Circle cx={42} cy={28} r={8} fill="rgba(255,255,255,0.92)" />
    <Path d="M40 24.5v7l5.5-3.5z" fill={INK} />
    <Circle cx={66} cy={18} r={7} fill="#FF3B5C" />
    <Path d="M66 21.5l-3.2-3.1a1.9 1.9 0 0 1 2.7-2.7l.5.5.5-.5a1.9 1.9 0 0 1 2.7 2.7z" fill="#fff" />
  </Svg>
)

/** Карточка объявления всплывает поверх ролика. */
const ArtAttach = () => (
  <Svg width={84} height={84} viewBox="0 0 84 84">
    <Rect x={14} y={6} width={40} height={72} rx={9} fill={INK} />
    <Rect x={17} y={12} width={34} height={60} rx={6} fill="#2B3A31" />
    <Rect x={30} y={44} width={48} height={22} rx={6} fill="#fff" stroke={GS} strokeWidth={2} />
    <Rect x={34} y={48} width={14} height={14} rx={3} fill={GS} />
    <Rect x={51} y={49} width={22} height={4} rx={2} fill={INK} />
    <Rect x={51} y={56} width={14} height={4} rx={2} fill={G} />
    <Circle cx={70} cy={30} r={9} fill={G} />
    <Path d="M70 25.5v9M65.5 30h9" stroke="#fff" strokeWidth={2.4} strokeLinecap="round" />
  </Svg>
)

/** Покупатель пишет продавцу прямо из ролика. */
const ArtChat = () => (
  <Svg width={84} height={84} viewBox="0 0 84 84">
    <Rect x={6} y={12} width={52} height={30} rx={10} fill={GS} />
    <Path d="M14 42l-2 10 10-10z" fill={GS} />
    <Rect x={14} y={21} width={30} height={4} rx={2} fill={GD} />
    <Rect x={14} y={29} width={20} height={4} rx={2} fill={GD} opacity={0.6} />
    <Rect x={28} y={44} width={50} height={28} rx={10} fill={G} />
    <Path d="M70 72l2 9-10-9z" fill={G} />
    <Rect x={36} y={53} width={28} height={4} rx={2} fill="#fff" />
    <Rect x={36} y={61} width={18} height={4} rx={2} fill="#fff" opacity={0.75} />
  </Svg>
)

/** Витрина: навес магазина и сетка товаров. */
const ArtStore = () => (
  <Svg width={84} height={84} viewBox="0 0 84 84">
    <Rect x={10} y={30} width={64} height={46} rx={6} fill="#fff" stroke={GS} strokeWidth={2} />
    <Path d="M8 30l6-16h56l6 16z" fill={G} />
    <Path d="M8 30h17v3a8.5 8.5 0 0 1-17 0zM25 30h17v3a8.5 8.5 0 0 1-17 0zM42 30h17v3a8.5 8.5 0 0 1-17 0zM59 30h17v3a8.5 8.5 0 0 1-17 0z" fill={GD} />
    <Rect x={17} y={46} width={14} height={14} rx={3} fill={GS} />
    <Rect x={35} y={46} width={14} height={14} rx={3} fill="#FFEDE6" />
    <Rect x={53} y={46} width={14} height={14} rx={3} fill={GS} />
    <Rect x={17} y={63} width={14} height={6} rx={2} fill={INK} opacity={0.15} />
    <Rect x={35} y={63} width={14} height={6} rx={2} fill={INK} opacity={0.15} />
    <Rect x={53} y={63} width={14} height={6} rx={2} fill={INK} opacity={0.15} />
  </Svg>
)

/** Автор: камера и звезда. */
const ArtCreator = () => (
  <Svg width={84} height={84} viewBox="0 0 84 84">
    <Rect x={10} y={26} width={46} height={36} rx={8} fill={INK} />
    <Path d="M56 38l16-9v30l-16-9z" fill={INK} />
    <Circle cx={33} cy={44} r={10} fill="#2B3A31" />
    <Circle cx={33} cy={44} r={5} fill={G} />
    <Path d="M66 8l3 6.2 6.8 1-4.9 4.8 1.2 6.8L66 23.6l-6.1 3.2 1.2-6.8-4.9-4.8 6.8-1z" fill="#F5B83D" />
  </Svg>
)

const STEPS: [() => React.ReactElement, string, string][] = [
  [ArtShoot, 'Снимите вещь в деле', 'Вертикальное видео до минуты: диван разложили, куртку надели, приставку включили'],
  [ArtAttach, 'Прикрепите объявления', 'До пяти — каждое всплывает карточкой с ценой в нужную секунду ролика'],
  [ArtChat, 'Покупатели пишут сразу из видео', 'Кнопка «Написать» на карточке открывает чат с вами — без поиска объявления'],
]

/**
 * Что такое шопсы и витрина — на экране «Новый шопс», пока видео не выбрано:
 * три шага с картинками, зачем это продавцу, чем витрина отличается и как стать автором.
 */
export default function ShopsExplainer() {
  return (
    <View style={{ marginTop: 22 }}>
      <Text style={s.h2}>{tr('Что такое шопсы')}</Text>
      <Text style={s.lead}>{tr('Короткие видео с вашими объявлениями. Их смотрят во вкладке «Шопсы» и на главной — как в TikTok, только каждую вещь можно сразу купить')}</Text>
      {STEPS.map(([Art, title, text], i) => (
        <View key={title} style={s.step}>
          <View style={s.art}><Art /></View>
          <View style={{ flex: 1 }}>
            <Text style={s.stepN}>{i + 1}</Text>
            <Text style={s.stepTitle}>{tr(title)}</Text>
            <Text style={s.stepText}>{tr(text)}</Text>
          </View>
        </View>
      ))}

      <Text style={[s.h2, { marginTop: 18 }]}>{tr('Зачем это продавцу')}</Text>
      {[
        'Видео продаёт лучше фото: вещь видно со всех сторон и в деле',
        'Шопс показывается всем во вкладке «Шопсы» 30 дней',
        'Видно, сколько посмотрели, досмотрели, лайкнули и написали вам',
      ].map((t) => (
        <View key={t} style={s.bullet}><Icon name="check" size={18} color={G} /><Text style={s.bulletText}>{tr(t)}</Text></View>
      ))}

      <Pressable style={[s.card, { marginTop: 18 }]} onPress={() => router.push('/vitrina' as never)} accessibilityRole="link">
        <View style={s.art}><ArtStore /></View>
        <View style={{ flex: 1 }}>
          <Text style={s.stepTitle}>{tr('А витрина — это ваш магазин')}</Text>
          <Text style={s.stepText}>{tr('Все ваши объявления на одной странице со своей ссылкой: подборки, подписчики, «Поделиться». Шопсы автора показываются там вкладкой «Видео»')}</Text>
          <Text style={s.link}>{tr('Моя витрина')} ›</Text>
        </View>
      </Pressable>

      <Pressable style={s.card} onPress={() => router.push('/shops/mine?tab=creator' as never)} accessibilityRole="link">
        <View style={s.art}><ArtCreator /></View>
        <View style={{ flex: 1 }}>
          <Text style={s.stepTitle}>{tr('Ведёте блог?')}</Text>
          <Text style={s.stepText}>{tr('Станьте автором: прикрепляйте к роликам любые объявления PLONK и берите заказы продавцов на шопсы')}</Text>
          <Text style={s.link}>{tr('Стать автором')} ›</Text>
        </View>
      </Pressable>
    </View>
  )
}

const s = StyleSheet.create({
  h2: { fontFamily: font[800], fontSize: 19, color: colors.ink, marginBottom: 6 },
  lead: { fontFamily: font[500], fontSize: 15, lineHeight: 21, color: colors.inkSoft, marginBottom: 12 },
  step: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingVertical: 10 },
  art: { width: 84, height: 84, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 0, alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  stepN: { alignSelf: 'flex-start', minWidth: 22, height: 22, paddingHorizontal: 6, borderRadius: 11, overflow: 'hidden', backgroundColor: colors.primarySoft, color: colors.primaryDeep, fontFamily: font[800], fontSize: 12, lineHeight: 22, textAlign: 'center', marginBottom: 4 },
  stepTitle: { fontFamily: font[700], fontSize: 16, color: colors.ink },
  stepText: { marginTop: 3, fontFamily: font[500], fontSize: 14, lineHeight: 19, color: colors.inkSoft },
  bullet: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, paddingVertical: 5 },
  bulletText: { flex: 1, fontFamily: font[500], fontSize: 15, lineHeight: 20, color: colors.ink },
  card: { flexDirection: 'row', alignItems: 'center', gap: 14, padding: 12, marginTop: 10, borderRadius: 18, backgroundColor: colors.surface, borderWidth: 0 },
  link: { marginTop: 6, fontFamily: font[700], fontSize: 14, color: colors.primaryDeep },
})
