"""
Уведомления о событиях: новое сообщение, приглашение оставить отзыв,
решение модерации.

Отправляем только тем, кто дал канал связи: у кого привязан Telegram —
туда, иначе на почту. Молчим, если человек прямо сейчас в приложении:
он и так всё видит, а дублирующее уведомление раздражает.
"""
import logging
from datetime import timedelta
from urllib import parse, request as urlrequest

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import User
from app.core.clock import utcnow

log = logging.getLogger(__name__)

# Если человек заходил только что — он в приложении, уведомление не нужно
ACTIVE_WINDOW = timedelta(minutes=3)

# Не больше одного уведомления о сообщениях за этот срок: при живой
# переписке иначе прилетит уведомление на каждую реплику
MESSAGE_COOLDOWN = timedelta(minutes=15)


def _send_telegram(chat_id: str, text: str) -> bool:
    token = getattr(settings, "telegram_bot_token", None)
    if not token:
        log.info("Telegram не настроен. Уведомление для %s: %s", chat_id, text)
        return False
    try:
        data = parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }).encode()
        urlrequest.urlopen(
            urlrequest.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data),
            timeout=10,
        )
        return True
    except Exception as exc:
        log.warning("Не доставлено в Telegram %s: %s", chat_id, exc)
        return False


def notify(db: Session, user_id, text: str, force: bool = False,
           allow_email: bool = False, subject: str | None = None,
           link: str | None = None, kind: str | None = None) -> bool:
    """
    Отправляет уведомление, если человек не в приложении прямо сейчас.

    force        — важное, отправляем даже активному (решение модерации).
    allow_email  — можно на почту, если Telegram не привязан. Включаем там,
                   где человек сам попросил уведомления: подписка на поиск,
                   решение по объявлению. Для каждого сообщения в переписке
                   почту не используем — письмо на каждую реплику уведёт
                   нас в спам, и перестанут доходить даже коды входа.
    link         — путь на сайте, куда ведёт уведомление в колокольчике.

    В колокольчик на сайте кладём всегда, даже если человек сейчас в
    приложении и внешнюю отправку пропускаем — это отдельный, не
    зависящий от Telegram/почты след события: человек без привязанного
    канала связи раньше не видел уведомлений вообще нигде.
    """
    from app.models import Notification

    user = db.query(User).get(user_id)
    if not user:
        return False

    db.add(Notification(user_id=user_id, text=_strip_tags(text), link=link))
    db.commit()

    # Человек выключил этот вид уведомлений (Профиль → Уведомления): в колокольчике оставляем, а в Telegram,
    # на почту и пушем не шлём. Важное (решения модерации, force) — всегда.
    if kind and not force and (user.notify_prefs or {}).get(kind) is False:
        return False

    if not force and user.last_seen_at:
        if utcnow() - user.last_seen_at < ACTIVE_WINDOW:
            return False   # он в приложении, увидит сам

    # Push — независимый канал, шлём его всегда вместе с любым другим:
    # человек мог разрешить пуши в браузере И иметь привязанный
    # Telegram одновременно, оба на разных устройствах — не выбираем
    # между ними, слово в это же событие докладывается на все места,
    # где его реально увидят.
    try:
        from app.core.webpush import send_web_push
        # Заголовок push без приставки «PLONK —» — subject тот же самый,
        # что уходит и в тему письма, где эта приставка уместна (почта
        # не показывает источник так же явно), а у push система и так
        # подписывает уведомление названием сайта своей строкой снизу —
        # с приставкой получалось бы «PLONK» дважды подряд.
        push_title = subject or "PLONK"
        if push_title.startswith("PLONK — "):
            push_title = push_title[len("PLONK — "):]
            # После среза первая буква осталась строчной («как прошла
            # сделка?») — в исходной строке это было продолжением
            # фразы после «PLONK —», а отдельным заголовком читается
            # как опечатка.
            push_title = push_title[:1].upper() + push_title[1:]
        send_web_push(db, user_id, push_title or "PLONK", _strip_tags(text), link=link)
    except Exception as exc:                     # noqa: BLE001
        log.warning("Web Push не отправлен: %s", exc)

    if user.telegram_id:
        return _send_telegram(user.telegram_id, text)

    # Уведомления на почту временно выключены.
    #
    # Apple начал отклонять наши письма — 554 5.7.1 [HM07]. Причину
    # искали долго: путь отправки, отправитель, разметка, ссылки,
    # обратный адрес, тема — всё проверено, и по отдельности каждое
    # письмо доходит. Осталось общее: почтовые службы смотрят на
    # отправителя целиком, а мы шлём с одного адреса и коды, и
    # уведомления, и ежедневную сводку. Письма, которые не открывают,
    # тянут доверие вниз — а вместе с ним и доставку кодов.
    #
    # Код для входа важнее всего остального: без него человек не войдёт
    # вообще. Поэтому пока на почту уходит только он, а уведомления
    # доставляются в Telegram и push-сообщением — они выше по коду и
    # работают как прежде.
    #
    # Вернуть просто: снять условие ниже. Стоит сделать это, когда
    # доставка кодов устоится.
    EMAIL_NOTIFICATIONS_ON = False

    if EMAIL_NOTIFICATIONS_ON and (allow_email or force) and user.email:
        try:
            from app.core.notify import _send_email_text, _notification_letter
            plain = _strip_tags(text)
            title = subject or "PLONK"
            _send_email_text(user.email, title, plain,
                             html=_notification_letter(title, plain))
            return True
        except Exception as exc:
            log.warning("Не доставлено на почту %s: %s", user.email, exc)

    return False


def _strip_tags(text: str) -> str:
    """Убираем разметку — в письме она ни к чему."""
    import re
    return re.sub(r"<[^>]+>", "", text)


def notify_new_message(db: Session, recipient_id, sender_id, sender_name: str,
                       preview: str, chat_id=None, message_id=None,
                       listing_title: str | None = None) -> bool:
    # Не чаще одного уведомления за MESSAGE_COOLDOWN на переписку — иначе
    # бурный диалог шлёт уведомление на каждую реплику. Раньше константа
    # была объявлена, но нигде не проверялась. Смотрим сообщения именно
    # от того же отправителя — иначе своё же недавнее сообщение самого
    # получателя (в чате всего два участника, но порядок событий и так
    # не гарантирует, что оно точно от собеседника) сбило бы счётчик.
    if chat_id is not None:
        from app.models import Message
        recent = (
            db.query(Message)
            .filter(
                Message.chat_id == chat_id,
                Message.sender_id == sender_id,
                Message.created_at > utcnow() - MESSAGE_COOLDOWN,
                Message.id != message_id,
            )
            .first()
        )
        if recent:
            return False

    # Раньше писали «написал вам в PLONK»: уведомление и так приходит от
    # нашего бота, приписка занимала строку и ничего не сообщала. Зато
    # не хватало главного — о какой вещи речь: у кого три переписки, тот
    # не понимал, по какой из них пишут, пока не открывал.
    head = f"<b>{sender_name}</b>"
    if listing_title:
        head += f" · {listing_title[:60]}"
    text = f"{head}\n\n{preview[:120]}"
    link = f"/chat/{chat_id}" if chat_id else None
    return notify(db, recipient_id, text, link=link, kind="messages")


def notify_review_request(db: Session, user_id, other_name: str, chat_id=None) -> bool:
    from app.core.morphology import to_instrumental
    text = (
        f"Как прошла сделка с <b>{to_instrumental(other_name)}</b>?\n\n"
        f"Оставьте отзыв — это помогает другим покупателям."
    )
    link = f"/chat/{chat_id}" if chat_id else None
    return notify(db, user_id, text, allow_email=True,
                  subject="PLONK — как прошла сделка?", link=link)


def notify_moderation(db: Session, user_id, title: str, approved: bool,
                      reason: str | None = None, listing_id=None) -> bool:
    if approved:
        text = f"Объявление «{title}» прошло проверку и опубликовано"
    else:
        text = f"Объявление «{title}» отклонено"
        if reason:
            text += f"\n\nПричина: {reason}"
    link = f"/go/{listing_id}" if (approved and listing_id) else "/my"
    return notify(db, user_id, text, force=True, allow_email=True,
                  subject="PLONK — ваше объявление", link=link)


def notify_doc_verification(db: Session, user_id, approved: bool, reason: str | None = None,
                            revoked: bool = False) -> bool:
    if approved:
        text = "Документ проверен — на вашем профиле теперь отметка «Проверенный пользователь»"
    elif revoked:
        # Повторная сверка (её запрашивает модератор у уже проверенного
        # человека) не прошла — снимаем отметку, а не просто «не
        # подтвердили с первого раза», как при обычном отказе.
        text = "Отметка «Проверенный пользователь» снята — повторная сверка личности не подтвердилась"
        if reason:
            text += f"\n\nПричина: {reason}"
        text += "\n\nМожно пройти проверку заново."
    else:
        text = "Не получилось проверить присланный документ"
        if reason:
            text += f"\n\nПричина: {reason}"
        text += "\n\nМожно отправить ещё раз."
    return notify(db, user_id, text, force=True, allow_email=True,
                  subject="PLONK — проверка документа", link="/profile")


def notify_reverify_requested(db: Session, user_id, verify_url: str) -> bool:
    """
    Модератор запросил у уже проверенного человека повторную сверку
    лица — уведомление со ссылкой прямо на сессию Didit, без захода
    на сайт: подтвердить, что аккаунт всё ещё у того же человека, кто
    его заводил.
    """
    text = (
        "Нужно подтвердить, что аккаунт всё ещё у вас — быстрая сверка "
        "лица, без документа заново.\n\n"
        f"Пройти проверку: {verify_url}"
    )
    return notify(db, user_id, text, force=True, allow_email=True,
                  subject="PLONK — подтвердите личность")


def notify_promotion_paid(db: Session, user_id, title: str, promo_type: str) -> bool:
    # Причастие своё на каждый тип — краткая форма («оплачено»/
    # «оплачена») должна согласовываться в роде с названием: «Крупная
    # карточка» женского рода, «оплачено» тут было бы ошибкой,
    # «Поднятие»/«Выделение» — среднего, им подходит «оплачено».
    names = {
        "bump": ("Поднятие в поиске", "оплачено"),
        "highlight": ("Выделение цветом", "оплачено"),
        "xl_card": ("Крупная карточка", "оплачена"),
    }
    name, paid_word = names.get(promo_type, (promo_type, "оплачено"))
    text = f"«{name}» для «{title}» {paid_word} и уже работает"
    return notify(db, user_id, text, force=True, allow_email=False,
                  subject="PLONK — продвижение оплачено")


def notify_expiring_soon(db: Session, user_id, title: str, days_left: int) -> bool:
    text = (
        f"Объявление «{title}» скоро снимется с публикации — через {days_left} дн.\n\n"
        "Если вещь ещё продаётся, поправьте в нём что-нибудь — например, "
        "цену или описание — и сохраните: объявление вернётся на "
        "проверку и получит новый срок показа."
    )
    return notify(db, user_id, text, allow_email=True,
                  subject="PLONK — объявление скоро снимется с публикации", link="/my")


def notify_expired(db: Session, user_id, title: str) -> bool:
    text = (
        f"Объявление «{title}» сняли с публикации — истёк срок показа.\n\n"
        "Если вещь ещё продаётся, в «Моих объявлениях» на вкладке "
        "«Архив» есть кнопка «Вернуть» — она разместит объявление снова."
    )
    return notify(db, user_id, text, allow_email=True,
                  subject="PLONK — объявление снято с публикации", link="/my")


def notify_report_resolved(db: Session, user_id, acted: bool,
                           listing_title: str | None = None) -> bool:
    """
    Ответ тому, кто пожаловался.

    Жалоба уходила в пустоту: человек не узнавал, посмотрел ли её
    кто-нибудь. Тот, кому один раз ответили, жалуется и во второй раз, а
    из таких людей и состоит уборка ленты. Подробностей не пишем —
    решение по чужому объявлению не его дело; говорим только, что
    разобрались.
    """
    thing = f" «{listing_title}»" if listing_title else ""
    text = (f"Спасибо за жалобу{thing} — объявление снято."
            if acted else
            f"Мы проверили объявление{thing} по вашей жалобе. "
            f"Правила оно не нарушает, поэтому осталось на сайте.")
    return notify(db, user_id, text)


def notify_published(db: Session, user_id, title: str, url: str,
                     in_chat: bool) -> bool:
    """
    Объявление из публикатора размещено.

    Человек выкладывал вещь из переписки и окно закрыл — подтверждение
    на экране он уже не видит. Сообщением в бот он узнаёт, что всё
    получилось, и получает ссылку, которой можно поделиться.

    Отправляем даже тому, кто сейчас в приложении (force): он только
    что нажал «опубликовать» и ждёт именно этого ответа.
    """
    where = "уже в чате" if in_chat else "отправлено на проверку"
    text = (f"<b>Объявление {where}</b>\n\n"
            f"{title[:100]}\n\n"
            f"{url}")
    return notify(db, user_id, text, force=True, link=url,
                  subject="PLONK — объявление размещено")
