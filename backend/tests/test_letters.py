"""
Письма.

Письма свёрстаны — стили вписаны прямо в разметку: внешние почтовые
службы не грузят, а половина из них режет то, чего не понимает.

Разметку письма с кодом однажды убирали, решив, что из-за неё Apple
отклоняет письмо. Проверка это опровергла: отказ пришёл и на письмо из
шести цифр простым текстом. Дело в репутации домена — Apple прямо
пишет, что решение о фильтрации принимает по репутации адресов и
домена, а не по одному лишь содержимому. Разметку вернули.

Ссылок в письме с кодом при этом нет: код рядом с кликабельной ссылкой
— рисунок поддельного письма, и на него фильтры срабатывают у всех, не
только у Apple.
"""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.notify import (  # noqa: E402
    BODY, SUBJECT, _notification_letter, _send_email, _send_email_text,
    _send_via_resend,
)


def test_code_is_the_main_thing():
    """Код виден сразу, крупно: ради него человек и открыл письмо."""
    from app.core.notify import _code_letter

    letter = _code_letter("482915")
    assert "482915" in letter
    # Крупным кеглем, а не строкой в общем тексте.
    assert "font-size:34px" in letter or "font-size:32px" in letter


def test_code_is_in_the_text_too():
    """Простой текст тоже несёт код: часть людей читает почту без разметки."""
    text = BODY.format(code="482915")

    assert "482915" in text
    # Срок жизни кода: без него человек не понимает, торопиться ли.
    assert "15" in text


def test_no_links_at_all_in_code_letter():
    """В письме с кодом нет ни одной ссылки — даже на сам сайт.

    Прежняя проверка требовала обратного: «ссылки в письме должны
    быть», лишь бы не вели на вход. Ровно поэтому их когда-то и
    вернули, убрав однажды.

    А дело было именно в них: Apple молча выбрасывал письмо, где рядом с
    кодом стоят четыре ссылки на сайт и разделы. Код плюс ссылки —
    рисунок поддельного письма. Ни отказа, ни папки «спам», просто
    исчезало; выясняли перебором полдня.

    Оформление при этом осталось: рамка, крупный код, подпись.
    """
    import re

    from app.core.notify import BODY, _code_letter

    letter = _code_letter("482915")
    assert "482915" in letter
    assert "<table" in letter, "оформление должно остаться"
    assert not re.search(r"<a\b", letter), "ссылок быть не должно"
    assert "http" not in letter

    # И в текстовой версии тоже.
    assert "http" not in BODY.format(code="482915")


def test_code_letter_styles_are_inline():
    """Внешние стили почта не загрузит, и письмо приедет голым."""
    from app.core.notify import _code_letter

    letter = _code_letter("482915")
    assert "style=" in letter
    assert "<link" not in letter
    assert "<img" not in letter


def test_plain_text_is_always_sent():
    """Простой текст кладётся всегда, разметка — только если она есть."""
    source = inspect.getsource(_send_via_resend)

    assert '"text"' in source
    # Разметку через Resend больше не отправляем: он шлёт с нашего
    # домена, а у того репутация ниже — оформленное письмо от
    # малознакомого отправителя лишний повод для подозрений. Оформление
    # остаётся на основном пути, через Gmail.
    assert 'letter["html"] = html' not in source


def test_subject_has_no_code():
    """
    Код в самом письме, откуда его удобно скопировать. Дважды одно и то
    же выглядит небрежно.
    """
    assert "{code}" not in SUBJECT
    assert "—" not in SUBJECT               # к лишним знакам почта придирчива


def test_letter_has_a_reply_address():
    """
    Письмо, на которое некому ответить, почтовые службы считают
    рассылкой.
    """
    assert "reply_to" in inspect.getsource(_send_via_resend)


def test_notification_letter_keeps_its_markup():
    """Уведомления остаются свёрстанными: стили прямо в разметке —
    внешние почта не загрузит, картинок нет вовсе."""
    letter = _notification_letter("Новое сообщение", "Вам ответили по объявлению")

    assert "style=" in letter
    assert "<link" not in letter
    assert "<img" not in letter


# ── Запасная отправка ───────────────────────────────────────────────────────
def test_apple_goes_through_gmail_others_through_own_domain():
    """Ящики Apple — сразу через Gmail, остальные своим доменом.

    Пробовали иначе: сперва свой домен, Gmail запасным. Продержалось
    недолго — письма на iCloud снова перестали доходить. Apple то
    пропускает наши письма, то нет, и полагаться на это нельзя: человек
    с таким ящиком просто не может войти, а понять почему ему неоткуда.

    Репутация домена от этого на Apple не растёт, и отправитель с чужого
    адреса выглядит хуже собственного — но работающий вход важнее
    солидности. На всех остальных ящиках домен по-прежнему свой.
    """
    import app.core.notify as notify

    saved = (notify.settings.gmail_user, notify.settings.gmail_app_password,
             notify.settings.resend_api_key, notify._gmail_blocked_until,
             notify._send_via_resend, notify._send_via_gmail)
    calls = []
    try:
        notify.settings.gmail_user = "x@gmail.com"
        notify.settings.gmail_app_password = "y"
        notify.settings.resend_api_key = "ключ"
        notify._gmail_blocked_until = 0.0
        notify._send_via_gmail = lambda to, s, b, h=None: calls.append("gmail")

        notify._send_via_resend = lambda to, s, b, h=None: calls.append("свой домен")

        # Ящик Apple — через Gmail, не пробуя свой домен.
        notify._send_email_text("a@icloud.com", "Код", "1")
        # Для Apple теперь оба пути сразу.
        #
        # Письмо от службы то доходило, то нет — в 04:34 и 04:45
        # пришло, в 04:48 нет. Ни отказа, ни спама: Apple молча решает
        # по своему усмотрению, и предсказать это нельзя. У Gmail и
        # Resend разные отправители и разная репутация, так что хотя бы
        # одно письмо дойдёт. Человек получит два одинаковых кода — это
        # лучше, чем ни одного.
        assert calls == ["gmail", "свой домен"]

        # Все прочие — своим доменом, как и раньше.
        calls.clear()
        notify._send_email_text("b@gmail.com", "Код", "2")
        assert calls == ["свой домен"]
    finally:
        (notify.settings.gmail_user, notify.settings.gmail_app_password,
         notify.settings.resend_api_key, notify._gmail_blocked_until,
         notify._send_via_resend, notify._send_via_gmail) = saved


def test_gmail_letter_is_sent_from_google_address():
    """Отправитель в запасном пути — сам гугловский адрес.

    Подменять его своим нельзя: подпись не сойдётся с доменом, и письмо
    отклонят уже по этой причине.
    """
    from app.core.notify import _send_via_gmail

    source = inspect.getsource(_send_via_gmail)
    assert 'msg["From"] = f"PLONK <{user}>"' in source
    assert "smtp.gmail.com" in source
    # Письмо уходит таким же, как основным путём: и текстом, и разметкой.
    assert 'msg.add_alternative(html, subtype="html")' in source


def test_login_has_no_stale_warning():
    """Предупреждения про iCloud на странице входа больше нет.

    Оно стояло, пока Apple отклонял наши письма. После того как домену
    добавили запись SPF, отказ сменился с окончательного на временный, а
    затем письма пошли — код на iCloud дошёл. Предупреждение с этого
    момента вводит людей в заблуждение, поэтому убрано.

    Если Apple снова начнёт отклонять, вернуть его недолго — но вешать
    предупреждение «на всякий случай» нельзя: половина людей в Белграде
    с iPhone, и они прочитают его как «мне сюда нельзя».
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Login.jsx").read_text()

    assert "isAppleMail" not in page
    assert "icloud_blocked" not in page
    assert "onClick={sendCode}" in page


def test_gmail_is_not_retried_after_failure():
    """После неудачи запасной путь не пробуем полчаса.

    Хостер какое-то время закрывал исходящий почтовый порт, и соединение
    не отказывалось сразу, а молчало до истечения ожидания. Кнопка
    «отправляем…» висела серой все эти секунды — и так у каждого. Порт с
    тех пор открыли, но зависеть от этого нельзя: закроют снова.
    """
    import app.core.notify as notify

    saved = (notify.settings.gmail_user, notify.settings.gmail_app_password,
             notify.settings.resend_api_key, notify._gmail_blocked_until,
             notify._send_via_resend, notify._send_via_gmail)
    calls = {"gmail": 0}

    def fail_gmail(to, subject, body, html=None):
        calls["gmail"] += 1
        raise TimeoutError("порт закрыт")

    def refuse(*args, **kwargs):
        raise RuntimeError("Apple отклонил")

    try:
        notify.settings.gmail_user = "x@gmail.com"
        notify.settings.gmail_app_password = "y"
        notify.settings.resend_api_key = "ключ"
        notify._gmail_blocked_until = 0.0
        notify._send_via_gmail = fail_gmail
        notify._send_via_resend = refuse

        for i in range(3):
            try:
                notify._send_email_text(f"{i}@icloud.com", "Код", "123456")
            except Exception:                              # noqa: BLE001
                pass                                       # оба пути отказали

        # Пробуем один раз: дальше идём сразу основным путём, не заставляя
        # человека ждать те же секунды впустую.
        assert calls["gmail"] == 1
        # Ждём двенадцать секунд, а не пять.
        #
        # Пять казались разумными: человек стоит перед экраном и ждёт
        # код. Но разговор с почтовым сервером — рукопожатие, вход,
        # отправка — в них не укладывается, особенно из Парижа. Каждая
        # заминка считалась отказом, Gmail выключался, и письмо уходило
        # туда, откуда Apple его выбрасывает. Человек ждал пять секунд и
        # не получал ничего вовсе — это хуже, чем подождать двенадцать и
        # получить код.
        assert notify.GMAIL_TIMEOUT <= 15
    finally:
        (notify.settings.gmail_user, notify.settings.gmail_app_password,
         notify.settings.resend_api_key, notify._gmail_blocked_until,
         notify._send_via_resend, notify._send_via_gmail) = saved


def test_resend_countdown_runs_on_the_clock():
    """Отсчёт до повторной отправки считается от времени отправки.

    Раньше он тикал «минус секунда каждую секунду». Браузер
    притормаживает таймеры в свёрнутой вкладке и в фоне: человек уходил
    в почту за кодом, возвращался — а счётчик всё это время стоял и
    заставлял ждать заново, хотя минута давно прошла.

    Пересчёт нужен и при возвращении на страницу: ждать до ближайшего
    тика — та же пауза на ровном месте.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Login.jsx").read_text()

    assert "RESEND_SEC - Math.floor((Date.now() - sentAt) / 1000)" in page
    for event in ("visibilitychange", "pageshow", "focus"):
        assert f'addEventListener("{event}"' in page or f"'{event}'" in page, event
    # Прежний способ не должен вернуться.
    assert "setLeft((s) => s - 1)" not in page


def test_gmail_path_sends_the_same_letter():
    """Через запасной путь уходит такое же письмо, с разметкой.

    Он отправлял голый текст, и владельцы ящиков iCloud получали письмо
    хуже остальных — а причина отказов Apple не в оформлении: тот же
    отказ приходил и на письмо из шести цифр простым текстом.
    """
    import app.core.notify as notify

    sent = {}

    class FakeSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def starttls(self): pass
        def login(self, *a): pass
        def send_message(self, msg): sent["msg"] = msg

    saved_smtp = notify.smtplib.SMTP
    saved = (notify.settings.gmail_user, notify.settings.gmail_app_password)
    try:
        notify.smtplib.SMTP = FakeSMTP
        notify.settings.gmail_user = "plonk.noreply@gmail.com"
        notify.settings.gmail_app_password = "x"
        notify._send_via_gmail("a@icloud.com", "Код", "Ваш код: 482915",
                               notify._code_letter("482915"))

        kinds = [part.get_content_type() for part in sent["msg"].walk()]
        assert "text/plain" in kinds     # для тех, кто читает почту без разметки
        assert "text/html" in kinds      # и само письмо
    finally:
        notify.smtplib.SMTP = saved_smtp
        (notify.settings.gmail_user, notify.settings.gmail_app_password) = saved


def test_only_login_codes_go_to_email_for_now():
    """На почту временно уходят только коды входа.

    Apple начал отклонять наши письма (554 5.7.1 [HM07]). Проверили всё
    по отдельности — путь отправки, отправителя, разметку, ссылки,
    обратный адрес, тему: каждое письмо в отдельности доходит. Осталось
    общее: почтовые службы смотрят на отправителя целиком, а мы слали с
    одного адреса и коды, и уведомления, и ежедневную сводку. Письма,
    которые не открывают, тянут доверие вниз — а с ним и доставку кодов.

    Код важнее: без него человек не войдёт вообще. Уведомления идут в
    Telegram и push-сообщением, сводка выключена расписанием на сервере.

    Тест сторожит, чтобы отправку на почту не вернули незаметно: вернуть
    её надо осознанно, когда доставка кодов устоится.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "core" / "notifications.py").read_text()

    assert "EMAIL_NOTIFICATIONS_ON = False" in source
    assert "if EMAIL_NOTIFICATIONS_ON and (allow_email or force)" in source


# ── Посещаемость ────────────────────────────────────────────────────────────
def test_visitor_key_hides_the_person():
    """Ключ посетителя не хранит ни адреса, ни браузера.

    Считаем людей без cookies: ключ — отпечаток от адреса и браузера с
    солью, которая меняется каждый день. За один день человека узнать
    можно (значит, не посчитаем его десять раз), связать вчерашний заход
    с сегодняшним — уже нельзя, даже нам.
    """
    from app.models import visitor_key

    class Request:
        headers = {"user-agent": "Mozilla/5.0 iPhone", "x-real-ip": "1.2.3.4"}
        client = None

    key = visitor_key(Request())

    assert "1.2.3.4" not in key
    assert "iPhone" not in key
    assert len(key) == 64
    # Один и тот же человек в один день — один ключ.
    assert key == visitor_key(Request())


def test_logged_in_visitor_counted_once():
    """Вошедший считается по себе, а не по браузеру.

    Иначе один человек с телефона и с ноутбука дал бы двух посетителей,
    хотя мы точно знаем, что он один.
    """
    from app.models import visitor_key

    class Request:
        headers = {"user-agent": "A", "x-real-ip": "1.1.1.1"}
        client = None

    class Other:
        headers = {"user-agent": "B", "x-real-ip": "2.2.2.2"}
        client = None

    assert visitor_key(Request(), user_id="abc") == visitor_key(Other(), user_id="abc")


def test_category_names_come_from_the_database():
    """Разделы в статистике показываются названием, а не служебным именем.

    В списке всплывали строки вида «appliances», «pets-supplies»,
    «car-parts»: страница переводила разделы по служебному имени, а
    перевода для них не нашлось, и она показывала имя как есть. При этом
    название лежит в базе на всех трёх языках.

    Теперь оно приходит с ответом, и любой раздел — хоть новый, хоть
    заведённый вручную — показывается по-человечески.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "routers" / "admin_stats.py").read_text()
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "AdminStats.jsx").read_text()

    assert '"name": names.get(slug, {})' in source
    assert "c.name?.[i18n.language]" in page


# ── Скорость ответа продавца ────────────────────────────────────────────────
def test_reply_speed_counts_first_answer_only():
    """Считаем ожидание первого ответа, а не среднее по переписке.

    Люди ждут ответа быстро, и там, где он приходит скоро, чаще доходит
    до сделки: у OLX за скорость дают значок и он приносит вдвое больше
    обращений, у Etsy порог — ответ на 95% первых сообщений за сутки.

    Важно именно первое «да, актуально»: дальше разговор может тянуться
    днями по обоюдному согласию, и это уже не про отзывчивость.

    Медиана, а не среднее: один ответ через неделю не должен портить
    картину тому, кто обычно отвечает за десять минут.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "core" / "reply_speed.py").read_text()

    assert "median(waits)" in source
    assert "MIN_ANSWERS = 3" in source          # два ответа — случайность
    assert "MAX_WAIT" in source                 # неделю спустя это не ответ


def test_reply_speed_is_shown_as_a_range():
    """Показываем порядок, а не точные минуты.

    «Отвечает за 47 минут» звучит как обещание, которого продавец не
    давал. Человеку нужно понять: сегодня или через день.
    """
    from app.core.reply_speed import speed_label

    assert speed_label(5) == "minutes"
    assert speed_label(20) == "hour"
    assert speed_label(300) == "hours"
    assert speed_label(60 * 20) == "day"
    assert speed_label(60 * 50) == "days"


# ── Блокировка ──────────────────────────────────────────────────────────────
def test_blocked_user_is_not_recognised_anywhere():
    """Заблокированный не узнаётся ни лентой, ни ботом.

    Блокировка действовала наполовину: обязательный вход её ловил, а
    необязательный — через который работают лента, поиск и карточки
    объявлений — нет. Человек после блокировки продолжал листать сайт.
    В боте проверки не было вовсе: он входил, подавал объявления и
    получал уведомления как ни в чём не бывало.

    Раз заблокировали — значит везде, иначе это не блокировка, а
    полумера.

    Проверено вживую: до блокировки лента узнаёт человека, после — нет.
    """
    auth = (Path(__file__).resolve().parents[1] / "app" / "core" / "auth.py").read_text()
    bot = (Path(__file__).resolve().parents[1] / "app" / "bot" / "publisher.py").read_text()

    # В необязательном входе — тоже проверка.
    optional = auth.split("def get_current_user_optional")[1].split("\ndef ")[0]
    assert "if user.is_blocked:" in optional

    # В боте — одна проверка на все команды сразу: их много, и
    # добавлять в каждую значит рано или поздно пропустить новую.
    assert "@dp.update.outer_middleware()" in bot
    assert "User.is_blocked" in bot


def test_bot_says_the_account_is_blocked():
    """Бот прямо говорит о блокировке, но не спорит.

    Сперва я сделал так, что бот просто молчит. Это выглядит поломкой:
    человек не понимает, дошло ли сообщение, и пишет снова и снова.
    Честнее сказать, что произошло, и куда идти, если он считает, что
    вышла ошибка.

    Но один раз за час: отвечать «вы заблокированы» на каждое сообщение
    — это уже разговор, а разговаривать тут не о чем.
    """
    bot = (Path(__file__).resolve().parents[1] / "app" / "bot" / "publisher.py").read_text()

    assert "Аккаунт заблокирован за нарушение правил" in bot
    assert "_should_tell_blocked" in bot
    assert "TELL_BLOCKED_EVERY = 3600" in bot


def test_blocked_user_gets_a_working_way_to_object():
    """Заблокированному даём прямую ссылку, а не «напишите в поддержку».

    Сперва я написал «напишите в поддержку на сайте» — и отправил
    человека туда, куда он не попадёт: заблокированный видит сайт как
    гость, профиля у него нет, и найти страницу поддержки ему неоткуда.

    Теперь в сообщении прямая ссылка. Путь при этом настоящий, а не
    отписка: форма поддержки работает без входа, там есть поле для
    обратной связи — проверено, обращение от гостя попадает в очередь.
    Блокировка бывает и ошибочной, и человеку нужен способ возразить.
    """
    bot = (Path(__file__).resolve().parents[1] / "app" / "bot" / "publisher.py").read_text()
    support = (Path(__file__).resolve().parents[1]
               / "app" / "routers" / "support.py").read_text()

    assert "{site}/support" in bot
    # Обращение принимается и без входа.
    assert "user: User | None = Depends(optional_user)" in support


def test_bot_keeps_working_when_database_is_down():
    """Сбой базы не должен отключать бота для всех.

    Отказать каждому из-за недоступной базы хуже, чем на минуту
    пропустить одного заблокированного.
    """
    bot = (Path(__file__).resolve().parents[1] / "app" / "bot" / "publisher.py").read_text()

    guard = bot.split("async def block_banned")[1].split("\n@")[0]
    assert "except Exception" in guard
    assert "return await handler(event, data)" in guard


def test_telegram_contact_needs_a_signed_in_user():
    """Связаться с продавцом в Telegram может только вошедший.

    Прямая ссылка была открыта всем, и блокировка обходилась в один
    клик: заблокированный не мог написать через сайт, но спокойно писал
    тому же человеку в Telegram.

    Прятать кнопку мало — ник приходил в ответе сервера, и ссылку
    собирали руками. Теперь он отдаётся только вошедшему, а
    заблокированный для сервера тоже гость: одной проверки хватает на
    оба случая.

    Проверено: гостю ник не приходит, вошедшему приходит.
    """
    api = (Path(__file__).resolve().parents[1]
           / "app" / "routers" / "listings.py").read_text()
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "ListingDetail.jsx").read_text()

    assert '"external_author": listing.external_author if viewer else None' in api
    # На странице невошедшему предлагаем вход вместо ссылки.
    assert "{!user ? (" in page


# ── Опасные приёмы в переписке ──────────────────────────────────────────────
def test_scam_patterns_are_noticed():
    """Известные приёмы обмана в переписке помечаются.

    Переписка на любой площадке — главный канал злоупотреблений: там
    человека уводят из-под присмотра и там же выманивают деньги. Мы её
    никак не смотрели, а жалобы приходят уже после того, как всё
    случилось.

    Это не блокировка и не цензура: сообщение доходит всегда. Помечаем
    разговор, чтобы он всплыл в служебной очереди — дальше решает
    человек.
    """
    from app.core.chat_watch import ALARM, suspicion

    for text in (
        "Переведите предоплату на карту, потом привезу",
        "Скиньте код из смс для подтверждения",
        "Оформите доставку по ссылке https://plonk-delivery.ru",
        "Напишите мне в вотсап, там отдам дешевле",
    ):
        score, why = suspicion(text, first_message=True)
        assert score >= ALARM, text
        assert why


def test_normal_messages_are_left_alone():
    """Обычный разговор не помечается.

    «Давайте в вотсапе созвонимся» посреди разговора — обычное дело:
    договорились и перешли. Опасен именно увод в первом же сообщении,
    да ещё с обещанием скидки.
    """
    from app.core.chat_watch import ALARM, suspicion

    for text in (
        "Здравствуйте, ещё актуально? Могу подъехать завтра",
        "Да, актуально. Давайте в вотсапе созвонимся",
        "Вот ссылка на похожий товар https://plonk.rs/item",
        "Отдам за 3000, торг возможен",
    ):
        score, _ = suspicion(text, first_message=False)
        assert score < ALARM, text


def test_flagged_chats_have_their_own_screen():
    """Помеченные разговоры собраны в отдельный список.

    Раньше их было видно только в журнале действий, среди прочих
    записей — то есть практически никак. Разбирать такое надо быстро,
    пока человек не перевёл деньги.

    Показываем переписку целиком: решить, обман это или нет, можно
    только прочитав разговор. «Переведите предоплату» от людей,
    договорившихся о доставке в другой город, — обычное дело, а то же
    самое в первом сообщении незнакомцу — уже нет.
    """
    api = (Path(__file__).resolve().parents[1]
           / "app" / "routers" / "moderation.py").read_text()
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "AdminFlaggedChats.jsx").read_text()
    profile = (Path(__file__).resolve().parents[2]
               / "frontend" / "src" / "pages" / "Profile.jsx").read_text()

    assert '@router.get("/flagged-chats")' in api
    assert '"flagged_chats"' in api               # счётчик рядом с обращениями
    assert '"messages": [' in api                 # разговор целиком
    assert "chat.messages.map" in page
    assert 'to="/admin/flagged"' in profile


def test_cleared_flag_is_kept_not_erased():
    """Разобранная пометка не стирается, а помечается разобранной.

    Если тот же человек попадётся снова, полезно видеть, что это уже
    второй раз.
    """
    api = (Path(__file__).resolve().parents[1]
           / "app" / "routers" / "moderation.py").read_text()

    assert "chat.flag_cleared_at = utcnow()" in api
    assert "Chat.flag_cleared_at.is_(None)" in api


def test_visit_is_counted_once_per_session():
    """Обновление страницы не считается новым заходом.

    Раньше заход прибавлялся при каждой загрузке ленты, а она грузится
    при обновлении, возврате назад, смене города и языка — число
    выходило втрое-впятеро больше правды.

    Теперь новый заход считаем, только если человека не было полчаса:
    это общепринятая мера, тот же порядок используют счётчики
    посещаемости.

    Проверено вживую: пять обновлений подряд — один заход, возвращение
    через час — второй.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "models" / "visit_daily.py").read_text()

    assert "SESSION_GAP = timedelta(minutes=30)" in source
    assert "VisitDaily.last_hit_at < now - SESSION_GAP" in source
    # Людей по-прежнему считаем по строкам: один человек в день — одна
    # строка, сколько бы он ни обновлял.
    assert 'UniqueConstraint("day", "visitor_key"' in source


def test_own_and_bot_traffic_is_not_counted():
    """Свои заходы и боты в посещаемость не попадают.

    Первое, что советуют убирать во всех руководствах по статистике:
    пока людей мало, десяток заходов администратора за день перебивает
    настоящую картину, и по ней уже ничего не решишь. Боты — поисковики
    и проверялки — ходят по сайту постоянно и к посещаемости отношения
    не имеют.

    Проверено вживую: заход администратора и заход бота не записались,
    заход покупателя и гостя — записались. Из шести входов, пять из
    которых свои, в статистике остался один.
    """
    visits = (Path(__file__).resolve().parents[1]
              / "app" / "models" / "visit_daily.py").read_text()
    stats = (Path(__file__).resolve().parents[1]
             / "app" / "routers" / "admin_stats.py").read_text()

    assert "def is_bot(" in visits
    assert "_is_staff(db, user_id)" in visits
    # Пустой user-agent — тоже не человек: браузер всегда представляется.
    assert "return True" in visits.split("def is_bot")[1][:400]
    # Входы своих в статистику не идут.
    assert "User.role.notin_((UserRole.admin, UserRole.moderator))" in stats


def test_newcomers_and_returning_are_separated():
    """Видно, сколько людей пришло впервые, а сколько вернулось.

    Общее число посетителей само по себе мало что говорит. Новые
    показывают, работает ли реклама; вернувшиеся — стоит ли сайт того,
    чтобы к нему возвращаться. Для площадки объявлений второе важнее:
    разовый заход не делает площадку живой.
    """
    stats = (Path(__file__).resolve().parents[1]
             / "app" / "routers" / "admin_stats.py").read_text()
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "AdminStats.jsx").read_text()

    assert '"returning": returning_by_day.get(current, 0)' in stats
    assert '"newcomers"' in stats
    assert "stats.newcomers" in page


def test_new_columns_have_a_database_default():
    """У новых обязательных колонок есть значение по умолчанию в базе.

    Без него добавление колонки к таблице, где уже есть строки, падает:
    старым записям нечего подставить, а колонка объявлена обязательной.
    Ровно на этом споткнулся деплой — «column last_hit_at contains null
    values».

    Значение только в коде (default=) базе не видно: она узнаёт о нём
    лишь при вставке новых строк, а миграции идут мимо.
    """
    from app.models import VisitDaily

    column = VisitDaily.__table__.c["last_hit_at"]
    assert not column.nullable
    assert column.server_default is not None


def test_active_seller_badge_is_earned_not_bought():
    """Значок активного продавца даётся за поведение, а не за деньги.

    У площадок такой значок работает как множитель: не заменяет
    качество объявления, но при прочих равных решает выбор. Ключевое —
    его нельзя купить, иначе он перестаёт что-либо значить, а вместе с
    ним обесцениваются и остальные знаки на площадке.

    Условия: отвечать в среднем в течение дня, иметь отзывы и хотя бы
    три объявления, не иметь подтверждённых жалоб за полгода.

    Проверено вживую: после трёх быстрых ответов значок появился, после
    подтверждённой жалобы пропал.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "core" / "active_seller.py").read_text()

    assert "MAX_REPLY_MINUTES = 60 * 24" in source
    assert "MIN_REVIEWS" in source and "MIN_LISTINGS" in source
    # Считаем только жалобы, по которым приняли меры: просто поданная
    # ничего не доказывает, иначе значок оказался бы в руках любого
    # недовольного.
    assert "ReportStatus.action_taken" in source
    # Ни денег, ни продвижения в условиях нет.
    for word in ("promotion", "paid", "payment", "оплат"):
        assert word not in source.lower()


def test_saved_search_alerts_respect_the_person():
    """Уведомления по сохранённому поиску не превращаются в спам.

    Сохранять поиски мы умели, а сообщать по ним — нет: галочка
    «уведомлять» стояла в базе и ничего не делала. А это главная
    причина возвращаться на площадку: человек искал коляску, ничего не
    нашёл и ушёл; появится через два дня — вернётся сам.

    Правила приличия: не чаще раза в сутки на поиск, первым делом само
    объявление, ничего не нашлось — молчим.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "core" / "saved_search_alerts.py").read_text()

    assert "QUIET_PERIOD = timedelta(hours=20)" in source
    assert "if not items:" in source          # пустых сообщений не шлём
    assert "SHOW = 3" in source               # больше трёх — уже список
    # Ищем ровно тем запросом, что человек сохранил: он подписывался на
    # него, а не на нашу трактовку.
    assert "filters.get(\"q\")" in source


def test_saved_search_alerts_have_a_schedule():
    """Рассылка запускается по расписанию, а не руками."""
    timer = (Path(__file__).resolve().parents[2]
             / "deploy" / "plonk-saved-search.timer").read_text()

    assert "OnCalendar=*-*-* 0/3:00:00" in timer
    assert "Persistent=true" in timer


def test_price_drop_alerts_are_not_noisy():
    """Сообщаем о подешевевшем, но только когда есть о чём.

    Часть лучших сделок — не свежие объявления, а те, что повисели без
    покупателя и подешевели. Заметить это самому нельзя, разве что
    заходить в избранное каждый день.

    Пишем тем, у кого объявление в избранном: это прямой знак интереса.
    Просмотревшим не пишем — посмотреть можно и случайно.

    Молчим: о повышении цены (это не новость, а огорчение), о
    копеечных изменениях и о том, о чём уже сообщали.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "core" / "price_drop_alerts.py").read_text()

    assert 'MIN_DROP = Decimal("0.10")' in source
    assert "MIN_ABS" in source                  # и не меньше суммы в деньгах
    assert "if now >= was" in source            # о подорожании молчим
    assert "notified_price_drop" in source      # дважды об одном не пишем


def test_price_drop_ignores_currency_change():
    """Смена валюты не считается подорожанием.

    100 евро против 12 000 динар — не «подорожало», а другая единица.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "core" / "price_drop_alerts.py").read_text()

    assert 'last.get("currency") !=' in source


def test_nightly_does_the_work_by_itself():
    """Ночной уход делает то, что раньше требовало ручного запуска.

    Мы написали с десяток полезных скриптов, но каждый нужно было
    запускать руками — и половина так и не дошла до дела. Перевод
    работал сам и почти закончил (99 непереведённых из четырёх тысяч),
    разбор компьютеров запустили один раз и он сработал (95 → 28). А
    чистка не запускалась ни разу: 105 объявлений без фото, тысяча без
    города, две сотни кривых заголовков.

    Работает то, что работает само.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "core" / "nightly.py").read_text()

    assert "translate_pending" in source
    assert "from app.core.retitle import run as retitle" in source
    assert "fill_cities(db, apply=True)" in source


def test_nightly_deletes_only_the_obvious():
    """Ночью удаляется только заведомо мёртвое.

    Объявления без фото на доске не открывают — их удаляем. А перечни и
    объявления без города только считаем и показываем в отчёте: приметы
    ошибаются, я это проходил пять раз подряд, и решать по ним должен
    человек.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "core" / "nightly.py").read_text()

    assert 'label="без фото"' in source
    # Перечни только считаем — по ним решает человек.
    assert 'done["похоже на перечни"] = bundles' in source
    # А безнадёжные заголовки удаляются, но лишь со второй попытки в
    # разные ночи: с первого раза могла не ответить нейросеть.
    assert "HOPELESS_TRIES = 2" in source


def test_nightly_report_skips_zeros():
    """Отчёт не перечисляет то, чего не было.

    «Переведено: 0, удалено: 0» — не отчёт, а шум: человек перестанет
    его читать. Всё чисто — молчим вовсе.
    """
    from app.core.nightly import report

    assert report({"переведено": 0, "удалено без фото": 0}) == ""
    assert "переведено: 12" in report({"переведено": 12, "удалено без фото": 0})


def test_night_work_is_not_done_twice():
    """Ночные работы не делают одно и то же дважды.

    Перевод и уборка снимков были и в ночной учёбе классификатора, и в
    ночном уходе, который идёт получасом позже. Две работы спорили за
    одну квоту бесплатной нейросети: учёба выбирала её первой, а разбору
    заголовков уже ничего не оставалось — половина заголовков днём не
    чинилась именно поэтому.

    Разделение теперь простое: учёба учит классификатор, уход переводит
    и чинит.
    """
    learn = (Path(__file__).resolve().parents[2]
             / "tools" / "learn-cron.sh").read_text()

    assert "translate-missing.py" not in learn
    assert "clean-media.py" not in learn
    # Учёба осталась при своём.
    assert "train-categories.py" in learn


def test_failed_titles_are_remembered():
    """Заголовок, который не поддался, больше не пробуют без конца.

    Пометка о неудаче писалась, но не сохранялась: db.commit() стоял
    только в ветке успеха. Оттого одни и те же «Даром», «Коляски»,
    «Белград» всплывали в каждом запуске и съедали весь запас запросов к
    нейросети, не давая дойти до остальных.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "core" / "retitle.py").read_text()

    failed_branch = source.split("if not new_title or new_title == translation.title:")[1]
    failed_branch = failed_branch.split("continue")[0]
    assert "db.commit()" in failed_branch


def test_hopeless_listings_are_deleted_after_two_tries():
    """Объявления с непонятным заголовком удаляются, но не сразу.

    «Даром», «Коляски», «Белград» — человек не знает, что там, и не
    открывает. Из описания взять нечего, иначе заголовок бы починился.

    Два раза, а не один: с первого могла просто не ответить нейросеть —
    сегодня лимит кончился, завтра ответит. Выбрасывать живое
    объявление из-за этого нельзя.

    Объявления с перепиской или в избранном не трогаем никогда: там
    завязались люди, и плохой заголовок этого не отменяет.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "core" / "nightly.py").read_text()

    assert "HOPELESS_TRIES = 2" in source
    assert "count >= HOPELESS_TRIES" in source
    assert "select distinct listing_id from chats" in source


def test_gmail_failure_is_shared_between_processes():
    """Отметка о сбое Gmail видна всем процессам, а не одному.

    Это и была причина загадочного «то приходит, то нет». Процессов у
    нас несколько, память у каждого своя: один пометил Gmail
    недоступным, остальные об этом не знали. Письмо уходило то через
    Gmail, то мимо него — смотря какому процессу достался запрос.
    """
    import os
    import time

    from app.core import notify

    if os.path.exists(notify._GMAIL_FLAG):
        os.remove(notify._GMAIL_FLAG)
    try:
        assert not notify._gmail_failed_recently()
        notify._remember_gmail_failure()
        assert notify._gmail_failed_recently()
    finally:
        if os.path.exists(notify._GMAIL_FLAG):
            os.remove(notify._GMAIL_FLAG)


def test_apple_gets_the_code_by_both_routes():
    """Ящикам Apple код уходит двумя путями сразу.

    Письмо от службы то доходило, то нет: в 04:34 и 04:45 пришло, в
    04:48 нет. Ни отказа, ни папки «спам» — Apple молча решает по
    своему усмотрению, и предсказать это нельзя.

    Раньше мы выбирали один путь и надеялись. Теперь шлём обоими: у
    Gmail и Resend разные отправители и разная репутация, и хотя бы
    одно письмо дойдёт. Человек получит два одинаковых кода — это лучше,
    чем ни одного, а войти можно по любому из них.

    Отказываем только если не сработал ни один путь: тогда человек
    увидит честное сообщение, а не тишину.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "core" / "notify.py").read_text()

    # Берём ветку целиком, до отказа: внутри неё есть своя проверка
    # ключа Resend, и обрывать по ней нельзя — на этом проверка сама
    # себя и обманула.
    # Берём ветку выбора пути, а не проверку вида письма: условие
    # «if _is_apple(to)» теперь встречается дважды, и по первому
    # совпадению проверка ловила не то.
    block = source.split("delivered = False")[1].split("raise MailUndeliverable")[0]
    assert "_send_via_gmail" in block
    assert "_send_via_resend" in block
    assert "if delivered:" in block
    assert 'raise MailUndeliverable("apple_mail_unavailable")' in source


def test_gmail_gets_enough_time():
    """Gmail не считается упавшим из-за пары лишних секунд.

    Ждали четыре секунды, а разговор с почтовым сервером — рукопожатие,
    вход, отправка — редко в них укладывается, особенно из Парижа.
    Каждая заминка считалась отказом и выключала Gmail на полчаса: всё
    это время люди с iCloud оставались без кода.
    """
    from app.core.notify import GMAIL_RETRY_AFTER, GMAIL_TIMEOUT

    assert GMAIL_TIMEOUT >= 10
    assert GMAIL_RETRY_AFTER <= 300


def test_every_code_attempt_is_logged():
    """Каждая отправка кода попадает в журнал — и успех, и отказ.

    Когда коды перестали доходить, в журнале было пусто: причину
    искали вслепую, запрос за запросом, вместо того чтобы просто
    прочесть. Человек без кода не может войти вовсе, и такое нельзя
    оставлять невидимым.

    Адрес пишем не целиком: журнал читают несколько человек, а почта —
    личные данные.
    """
    from app.core.notify import _short

    assert _short("maxsim@icloud.com") == "max***@icloud.com"

    source = (Path(__file__).resolve().parents[1]
              / "app" / "core" / "notify.py").read_text()
    block = source.split("def send_code(")[1].split("\ndef ")[0]
    # Уровень «предупреждение» даже для успеха: служба на сервере пишет
    # в журнал только предупреждения и ошибки, обычные сообщения
    # глотает. Отправка кода должна быть видна всегда — человек без
    # кода не войдёт, а выяснять это вслепую мы уже пробовали.
    assert block.count("log.warning") >= 3


def test_person_is_told_why_the_code_did_not_come():
    """Человек видит причину и выход, а не «что-то пошло не так».

    Он пришёл регистрироваться: ждал код, не получил и ушёл. Сколько
    людей так и не зарегистрировалось из-за молчаливого сбоя, мы уже не
    узнаем, но повторять это нельзя.

    Теперь при недоступной почте он читает, что на iCloud письмо сейчас
    не доходит, и что войти можно через Telegram.
    """
    api = (Path(__file__).resolve().parents[1]
           / "app" / "routers" / "auth.py").read_text()
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Login.jsx").read_text()

    assert 'HTTPException(503, "apple_mail_unavailable")' in api
    assert 'HTTPException(503, "code_not_sent")' in api
    assert "apple_mail_unavailable: t('auth.err_apple_mail')" in page


def test_made_up_addresses_are_refused():
    """Выдуманный адрес не принимается.

    Раньше принималось что угодно: «wwendjsjsj@icloud», «просто текст».
    Человек не получал код, пробовал ещё раз и уходил, а мы тратили
    письмо и место в базе на адрес, которого нет.
    """
    from app.core.email_check import check

    for bad in ("wwendjsjsj@icloud", "просто текст", "a@b", "две..точки@mail.ru"):
        ok, why, _ = check(bad)
        assert not ok, bad
        assert why


def test_typos_are_suggested_not_refused():
    """Опечатку в домене подсказываем, а не отвергаем.

    «gmial.com» существует — такие домены скупают перекупщики. Человек
    почти наверняка ошибся, но решать должен он: у кого-то почта и
    правда на редком домене.
    """
    from app.core.email_check import check

    ok, why, hint = check("ivan@gmial.com")
    assert ok and not why
    assert hint == "ivan@gmail.com"


def test_real_addresses_pass():
    """Настоящие адреса проходят без помех."""
    from app.core.email_check import check

    for good in ("maxsim@icloud.com", "ana@gmail.com", "petar@yandex.ru"):
        ok, why, hint = check(good)
        assert ok and not why and not hint, good


def test_mail_server_is_not_probed():
    """Не стучимся на почтовый сервер, чтобы спросить про ящик.

    Такая проверка ненадёжна — крупные службы отвечают «да» на любой
    адрес, чтобы не выдавать своих людей, — и выглядит как поведение
    рассыльщика спама, за что можно попасть в чёрные списки.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "core" / "email_check.py").read_text()

    assert "smtplib" not in source
    assert "RCPT" not in source.upper()


def test_domain_check_is_out_of_the_login_path():
    """Проверка домена через DNS убрана из пути входа.

    Она дважды закрыла вход настоящему человеку —
    «email_domain_unknown» на живую почту — и не отсеяла ни одного
    выдуманного адреса. На сервере ответ DNS отличался от нашего, и
    предсказать это оказалось нельзя.

    Вреда больше, чем пользы: несуществующий адрес просто не получит
    письмо, а живой человек, которого не пустили, уходит навсегда.

    Вид адреса и опечатки проверяем по-прежнему — они работают
    одинаково везде.
    """
    from app.core.email_check import check

    # Живые адреса проходят.
    for good in ("maxsim@icloud.com", "ana@gmail.com", "petar@yandex.ru"):
        ok, why, _ = check(good)
        assert ok and not why, good

    # Явный мусор — нет.
    for bad in ("wwendjsjsj@icloud", "просто текст", "две..точки@mail.ru"):
        ok, why, _ = check(bad)
        assert not ok and why == "email_malformed", bad


def test_code_letter_has_no_links():
    """В письме с кодом нет ни одной ссылки.

    Ссылки отсюда уже убирали и потом вернули, решив, что дело не в
    них. Оказалось — в них: Apple молча выбрасывал письмо, где рядом с
    кодом стоят четыре ссылки на сайт и разделы. Код плюс ссылки —
    рисунок поддельного письма, и почтовая служба режет такое, не
    спрашивая и не кладя в спам.

    Проверяли перебором полдня: простые письма доходили все, оформленное
    со ссылками — ни одно.

    Оформление при этом осталось: рамка, крупный код, подпись. Кому
    нужно на сайт, тот откроет его сам — он и так у него открыт.
    """
    import re

    from app.core.notify import _code_letter

    html = _code_letter("123456")
    assert "123456" in html
    assert "<table" in html, "оформление должно остаться"
    assert not re.search(r"<a\b", html), "ссылок быть не должно"
    assert "http" not in html


def test_code_stands_on_its_own_line():
    """Код стоит отдельной строкой, первым, без слов вокруг.

    Почта на телефоне сама распознаёт такие цифры и предлагает вставить
    их одним нажатием — но только если строка состоит из кода и ничего
    больше. Когда он стоял внутри фразы «Ваш код подтверждения:
    123456», подсказка не появлялась, и человеку приходилось выделять
    цифры пальцем.

    Разметку для этого вернуть нельзя: из-за неё письмо не доходило до
    ящиков Apple. Простой текст с кодом на своей строке решает то же
    самое.
    """
    from app.core.notify import BODY

    first = BODY.format(code="483920").strip().splitlines()[0]
    assert first == "483920", "код должен быть первой строкой и один"


def test_resend_sends_plain_text_only():
    """Через Resend уходит только текст, без разметки.

    Он шлёт с нашего домена, а у того репутация ниже, чем у Gmail:
    почтовые службы смотрят на отправителя строже, и лишний повод для
    подозрений тут ни к чему. Оформленное письмо от малознакомого
    домена — как раз такой повод.

    Основной путь, Gmail, оформление сохраняет: там письмо доходит.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "core" / "notify.py").read_text()

    block = source.split("def _send_via_resend(")[1].split("\ndef ")[0]
    assert 'letter["html"]' not in block
    assert '"text":' in block


def test_code_is_easy_to_copy():
    """Код в письме берётся одним касанием.

    Кнопку «скопировать» в письме сделать нельзя: почта не выполняет
    код страниц, нажатия там не работают. Это ограничение самой почты,
    обойти его невозможно.

    Что работает вместо кнопки:

    user-select заставляет почтовые приложения выделять весь код
    целиком по одному касанию — вместо возни с ползунками выделения.
    Дальше остаётся только «Копировать».

    А код первой строкой текстовой версии заставляет телефон
    распознать его и предложить вставку прямо над клавиатурой — тогда
    копировать не нужно вовсе.
    """
    from app.core.notify import BODY, _code_letter

    letter = _code_letter("483920")
    assert "user-select:all" in letter
    # Без пробелов вокруг: иначе в буфер попадёт код с хвостом.
    assert ">483920</div>" in letter

    assert BODY.format(code="483920").splitlines()[0] == "483920"


def test_code_letter_says_nothing_extra():
    """В письме с кодом нет ничего, кроме кода и срока.

    Resend вернул прямой отказ: «Blocked due to content — the
    recipient\'s server doesn\'t allow this content». Первый честный
    ответ за весь день, до этого письма исчезали молча.

    Убрано то, что делало письмо похожим на рассылку. Предупреждение
    «если это были не вы» — стандартная фраза мошеннических писем, к
    ней придирчивы почтовые службы, а человеку она бесполезна: без кода
    в профиль всё равно никто не войдёт. И подпись «объявления в
    Белграде и по всей Сербии» с перечнем разделов — реклама, которой в
    письме с кодом делать нечего.
    """
    import re

    from app.core.notify import BODY, _code_letter

    plain = BODY.format(code="483920")
    assert "не вы" not in plain
    assert "Сербии" not in plain

    letter = re.sub(r"<[^>]+>", " ", _code_letter("483920"))
    assert "не вы" not in letter
    assert "Недвижимость" not in letter
    assert "483920" in letter
