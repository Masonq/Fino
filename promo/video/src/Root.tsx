import React from 'react'
import { Composition } from 'remotion'
import { Promo } from './Promo'

export const Root: React.FC = () => (
  <Composition id="Promo" component={Promo} durationInFrames={735} fps={30} width={1080} height={1920} />
)
