import Svg, { Circle, Path } from 'react-native-svg'

import { colors } from '../theme'

/** Галочка у имени: official — команда PLONK («розетка»), verified — личность/компания подтверждены (круг). */
export default function VerifiedMark({ official, verified, size = 16 }: { official?: boolean; verified?: boolean; size?: number }) {
  if (!official && !verified) return null
  return official ? (
    <Svg width={size} height={size} viewBox="0 0 24 24" accessibilityLabel="PLONK">
      <Path fill={colors.primary} d="M12 1.6l2.4 1.8 3-.1.9 2.9 2.5 1.7-.9 2.9.9 2.9-2.5 1.7-.9 2.9-3-.1L12 22.4l-2.4-1.8-3 .1-.9-2.9-2.5-1.7.9-2.9-.9-2.9 2.5-1.7.9-2.9 3 .1z" />
      <Path d="m8 12.2 2.7 2.7L16.2 9.4" fill="none" stroke="#fff" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  ) : (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Circle cx={12} cy={12} r={10} fill={colors.primary} />
      <Path d="m7.8 12.3 2.8 2.8 5.6-5.8" fill="none" stroke="#fff" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  )
}
