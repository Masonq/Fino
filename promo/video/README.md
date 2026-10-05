# Промо-ролик PLONK для сторис и TikTok (Remotion)

1080×1920, 30 к/с, 25 с. Композиция `PromoReal` (`src/PromoReal.tsx`) — на настоящих объявлениях из `public/real`
(их собирает `tools/promo-assets.py` на сервере). Общие элементы (цвета, шрифт, телефон, меню) — `src/ui.tsx`.

Собрать заново: `npm i`, `npm run render`; звук — `python3 mix.py` (lo-fi саундтрек 90 BPM синтезом, голос из `voice/`,
звуки интерфейса; музыка приглушается под голосом), затем свести:
`ffmpeg -i out/plonk-promo.mp4 -i out/mix.wav -map 0:v -map 1:a -c:v libx264 -crf 21 -c:a aac -b:a 192k -shortest -movflags +faststart out/plonk-promo-web.mp4`.

Голос — Piper, модель `ru_RU-sova200-medium` (женский, Apache-2.0; ещё в `voice/`: terra5871, kat580, luka; зеркало github.com/Rotem12/piper-russian-voices). Другой голос: `VOICE=terra5871 python3 mix.py`.
`echo "текст" | python3 -m piper -m ru_RU-dmitri-medium.onnx -f voice/sova200_l1.wav --length-scale 0.92`.
Склейки стоят на долях: 20 кадров = доля при 90 BPM, такт = 80 кадров.
Кадр рассчитан на безопасные зоны TikTok/Reels: сверху ~220 px, снизу ~380 px, справа ~150 px — важное туда не ставить.
