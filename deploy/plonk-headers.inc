# Заголовки безопасности PLONK. Подключаются include'ом в каждый location,
# где есть свой add_header: в nginx add_header внутри location отменяет
# все add_header уровня server, и без include защитные заголовки пропадали
# бы ровно на тех адресах, где они нужнее всего.
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "frame-ancestors 'self'" always;
add_header Permissions-Policy "camera=(self), microphone=(self), geolocation=(self), payment=()" always;
