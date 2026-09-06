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


def test_no_login_link_in_code_letter():
    """В письме нет ссылки, по которой «подтверждают вход».

    Ссылки в письме есть — на сайт, на разделы, на нашу почту. А вот
    ссылки вида «нажмите, чтобы войти» нет и быть не должно: именно она
    делает письмо похожим на поддельное и приучает человека нажимать на
    такие ссылки в почте, а завтра ему пришлют такую же от чужого
    имени. Код вводят руками.

    Простой текст письма остаётся вовсе без ссылок: там их нечем
    оформить, и голый адрес среди цифр читается плохо.
    """
    from app.core.notify import _code_letter

    letter = _code_letter("482915")

    assert "http://" not in BODY.format(code="482915")
    assert "https://" not in BODY.format(code="482915")
    # Ссылки ведут на сайт и на почту — и никуда больше.
    import re
    targets = re.findall(r'href="([^"]+)"', letter)
    assert targets, "ссылки в письме должны быть"
    for target in targets:
        assert target.startswith(("https://plonk.rs", "mailto:")), target
    # Никаких одноразовых входов по ссылке.
    for word in ("token", "login?", "verify?", "confirm"):
        assert word not in letter


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
    assert 'letter["html"] = html' in source


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
        assert calls == ["gmail"]

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
        assert notify.GMAIL_TIMEOUT <= 5  # ждать дольше нельзя: это живой запрос
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
