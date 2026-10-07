/** Мягкие цвета разделов — те же, что на сайте (frontend/src/utils/tints.js): главная, размещение, разделы. */
import { isDark } from './theme'

const LIGHT: Record<string, string> = {
  'real-estate': '#E2F1E6', auto: '#E3ECFA', services: '#FCEADB', jobs: '#F3EBDB', electronics: '#EAE7FA', fashion: '#FAE5EE',
  'home-garden': '#ECF0DD', 'hobby-sport': '#DDF0F3', kids: '#FFF0D2', pets: '#F1E8DE', beauty: '#F7E4F1', business: '#E5EAF0',
}

/** В тёмной теме — те же оттенки, приглушённые (как на сайте) */
const DARK: Record<string, string> = {
  'real-estate': '#2A3D32', auto: '#2A3446', services: '#45362C', jobs: '#403A2E', electronics: '#363349', fashion: '#45313B',
  'home-garden': '#363C2C', 'hobby-sport': '#2B3D40', kids: '#46402A', pets: '#403830', beauty: '#45303F', business: '#323843',
}
export const TINTS: Record<string, string> = isDark ? DARK : LIGHT
