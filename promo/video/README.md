# Промо-ролик PLONK для сторис и TikTok (Remotion)

Основной — композиция `PromoV4` (`src/PromoV4.tsx`): 16 с, 1080×1920, 30 к/с, без голоса.
Собран по рекомендациям TikTok для рекламы: зацепка с движением и суть продукта в первые 3 с, длина 9–16 с,
текст 5–10 слов в секунду и только в безопасной зоне (сверху ~220 px, снизу ~380 px, справа ~150 px),
монтаж в долю музыки (90 BPM: доля = 20 кадров), «врезка» на кнопку, переход-совпадение (фото → экран телефона),
плитки, собирающиеся в сетку, призыв в конце. Настоящие объявления — `public/real` (собирает `tools/promo-assets.py`).

Собрать: `npm i`, `npx remotion render src/index.ts PromoV4 out/v4.mp4 --codec=h264 --crf=18`,
звук — `python3 mix4.py` (lo-fi 90 BPM и звуки интерфейса синтезом, без чужих сэмплов), свести:
`ffmpeg -i out/v4.mp4 -i out/mix4.wav -map 0:v -map 1:a -c:v libx264 -crf 21 -c:a aac -b:a 192k -shortest -movflags +faststart out/v4-web.mp4`.
Готовый ролик — `frontend/public/promo/plonk-promo.mp4` → https://plonk.rs/promo/dl/plonk-promo.mp4 (скачать).

`PromoReal` — прежняя длинная версия (24 с), `mix.py` — её звук.
