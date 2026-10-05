# Промо-ролик PLONK для сторис и TikTok (Remotion)

1080×1920, 30 к/с, 25 с. Композиция `PromoReal` (`src/PromoReal.tsx`) — на настоящих объявлениях из `public/real`
(их собирает `tools/promo-assets.py` на сервере). Общие элементы (цвета, шрифт, телефон, меню) — `src/ui.tsx`.

Собрать заново: `npm i`, `npm run render`, звук — `python3 sfx.py` (синтез, без чужих сэмплов), затем свести: `ffmpeg -i out/plonk-promo.mp4 -i out/sfx.wav -map 0:v -map 1:a -c:v libx264 -crf 21 -c:a aac -shortest -movflags +faststart out/plonk-promo-web.mp4`.
Кадр рассчитан на безопасные зоны TikTok/Reels: сверху ~220 px, снизу ~380 px, справа ~150 px — важное туда не ставить. Готовый ролик — `frontend/public/promo/plonk-promo.mp4`
→ https://plonk.rs/promo/plonk-promo.mp4, обложка — `plonk-promo-cover.jpg`.
