import React from 'react'
import { Composition } from 'remotion'
import { Promo } from './Promo'
import { PromoReal } from './PromoReal'
import { PromoV4 } from './PromoV4'

export const Root: React.FC = () => (
  <>
    <Composition id="PromoV4" component={PromoV4} durationInFrames={480} fps={30} width={1080} height={1920} />
    <Composition id="PromoReal" component={PromoReal} durationInFrames={720} fps={30} width={1080} height={1920} />
    <Composition id="Promo" component={Promo} durationInFrames={735} fps={30} width={1080} height={1920} />
  </>
)
