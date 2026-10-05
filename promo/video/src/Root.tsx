import React from 'react'
import { Composition } from 'remotion'
import { Promo } from './Promo'
import { PromoReal } from './PromoReal'

export const Root: React.FC = () => (
  <>
    <Composition id="PromoReal" component={PromoReal} durationInFrames={760} fps={30} width={1080} height={1920} />
    <Composition id="Promo" component={Promo} durationInFrames={735} fps={30} width={1080} height={1920} />
  </>
)
