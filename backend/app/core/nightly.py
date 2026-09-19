"""
Ночной уход за лентой.

Мы написали с десяток полезных скриптов, но каждый требовал ручного
запуска — и половина так и не дошла до дела. Перевод работал сам и
почти закончил (99 непереведённых из четырёх тысяч), разбор компьютеров
запустили один раз и он сработал (95 → 28). А чистка не запускалась
ни разу: 105 объявлений без фото, тысяча без города, две сотни кривых
заголовков.

Вывод простой: работает то, что работает само. Здесь всё собрано в один
проход, который идёт ночью и утром присылает короткий отчёт.

Что делает, по порядку:

1. Переводит непереведённое.
2. Чинит заголовки, где они кривые или пустые.
3. Дописывает город тем, у кого он есть в описании.
4. Удаляет объявления без фото — они мертвы, их не открывают.
5. Помечает найденное на разбор: перечни и объявления без города,
   которые не удалось починить.

Чего НЕ делает без человека: не удаляет ничего, кроме объявлений без
фото. Перечни и объявления без города только считает и показывает в
отчёте — решать по ним должен человек, потому что приметы ошибаются, и
я это уже проходил пять раз подряд.

Запуск по расписанию:
    python3 -m app.core.nightly
"""
from sqlalchemy import or_, text

from app.core.database import SessionLocal

# Сколько заголовков и переводов чиним за ночь.
#
# Не всё разом: перевод идёт через внешнюю службу с ограничениями, а
# переписывание заголовков стоит держать в пределах, которые человек
# успеет проглядеть в журнале, если что-то пойдёт не так.
# Доли одного бесплатного лимита, а не «сколько получится».
#
# У провайдера полсотни запросов в сутки на всех. Раньше каждая работа
# просила сотни, первая же выедала лимит, и остальные молча ничего не
# делали — включая эту.
# Делим суточный запас между работами.
#
# Сейчас отвечает один провайдер из четырёх: у Gemini и Mistral лимит
# кончился, ключ Groq отозван. У бесплатного OpenRouter полсотни
# запросов в сутки — их и делим.
#
# Заголовкам даём больше: их полторы сотни и они видны людям в ленте, а
# перевод догоняется машинными переводчиками, когда нейросеть занята.
# Ночью берём немного: основную работу делает почасовой заход
# (plonk-translate.timer), а здесь — подчистить то, что он не успел.
TRANSLATE_LIMIT = 40
RETITLE_LIMIT = 60

# Починка заголовков по фотографии — самая полезная работа за ночь:
# восемь из десяти получают настоящее название вместо «Мякишей» и
# «Одежды». Даём ей больше всех.
#
# Пределы у Gemini свои, отдельные от прочих провайдеров, и снимки идут
# через него — этот запас мы почти не тратим на другое.
PHOTO_RETITLE_LIMIT = 150

# Разбор одежды по снимкам — сто за ночь.
#
# Пятьсот объявлений разберутся за неделю, и это правильный темп:
# видно, что происходит, и есть время остановиться, если пойдёт не так.
CLOTHES_LIMIT = 100


def run() -> dict:
    """Делает ночной проход. Возвращает, что сделано — для отчёта."""
    done = {}

    # 1. Перевод.
    try:
        from app.core.translate import translate_pending
        with SessionLocal() as db:
            done["переведено"] = translate_pending(db, limit=TRANSLATE_LIMIT)
    except Exception as e:                                 # noqa: BLE001
        done["перевод не вышел"] = str(e)[:60]

    # 2. Заголовки.
    try:
        from app.core.retitle import run as retitle
        done["заголовков поправлено"] = retitle(limit=RETITLE_LIMIT,
                                                dry_run=False)
    except Exception as e:                                 # noqa: BLE001
        done["заголовки не вышли"] = str(e)[:60]

    # 3–4. Город из описания и удаление объявлений без фото.
    #
    # Город дописываем всегда: это спасает объявление, а не выбрасывает
    # его. Объявления без фото удаляем — на доске объявление без
    # картинки не открывают, оно только занимает место в ленте.
    try:
        from app.core.feed_cleanup import NO_PHOTO, fill_cities, purge
        with SessionLocal() as db:
            done["городов дописано"] = fill_cities(db, apply=True)
            done["удалено без фото"] = purge(
                db, [row[0] for row in db.execute(text(NO_PHOTO))],
                apply=True, label="без фото")
    except Exception as e:                                 # noqa: BLE001
        done["чистка не вышла"] = str(e)[:60]

    # 5. Убираем чужие ссылки из описаний.
    #
    # Люди приносят их из чатов: на свой магазин, на маркетплейс, иногда
    # на мошеннический сайт. Кликабельными они не становятся, но
    # проверяющие читают текст страницы и видят адрес — этого хватило,
    # чтобы Instagram начал показывать предупреждение о мошенническом
    # сайте, хотя по всем спискам безопасности мы чисты.
    try:
        from app.core.strip_links import run as strip_links

        strip_links(apply=True, limit=100000)
    except Exception as e:                                 # noqa: BLE001
        done["чистка ссылок не вышла"] = str(e)[:60]

    # 6. Удаляем объявления без города.
    #
    # Город дописать не удалось — значит его нет ни в заголовке, ни в
    # описании, ни в самом объявлении. Такое не найдут ни поиском по
    # городу, ни фильтром: человек в Белграде его не увидит, человек в
    # Нови-Саде тоже. Оно просто занимает место в ленте.
    #
    # Удаляем после того, как отработала дописка города: сперва спасаем
    # что можно, и только потом убираем остальное.
    try:
        done["удалено без города"] = _purge_without_city()
    except Exception as e:                                 # noqa: BLE001
        done["удаление без города не вышло"] = str(e)[:60]

    # 7. Приглашаем оставить отзыв.
    #
    # Рассылка была написана и не запускалась нигде: отзывов пять на всю
    # площадку, приглашений — ни одного. Оттого у продавцов пустые
    # оценки, а человек боится писать незнакомцу.
    #
    # Сам механизм осторожен: спрашивает только при высокой вероятности
    # сделки, по одному покупателю на объявление, одно напоминание через
    # три дня — и больше не беспокоит того, кто дважды промолчал.
    try:
        from app.core.review_invites import scan_recent_deals, send_reminders

        with SessionLocal() as db:
            done["приглашений на отзыв"] = scan_recent_deals(db)
            done["напоминаний об отзыве"] = send_reminders(db)
    except Exception as e:                                 # noqa: BLE001
        done["приглашения на отзыв не вышли"] = str(e)[:60]

    # 8. Чиним заголовки по фотографии — до удаления безнадёжных.
    #
    # Порядок важен: сперва даём объявлению шанс, потом убираем. Иначе
    # удалим то, что можно было спасти.
    #
    # Собрать заголовок из описания часто не выходит — описания нет
    # вовсе. А на фотографии видно вещь: «Мякиши» становятся «Игрушкой
    # мягкой зелёной», «Завалялись русскоязычные книги» — «Мангой
    # Истребитель демонов». Восемь из десяти на живой выгрузке.
    try:
        from app.core.retitle_by_photo import run as retitle_photo

        retitle_photo(apply=True, limit=PHOTO_RETITLE_LIMIT)
    except Exception as e:                                 # noqa: BLE001
        done["починка по фото не вышла"] = str(e)[:60]

    # 9. Раскладываем одежду по фотографии.
    #
    # В «Одежде» висят пятьсот объявлений: «Куртка Zara», «Футболка
    # Lime». Вещь названа, а пол — нет, и по заголовку не понять. Зато
    # видно на снимке: на живой выгрузке разбирается четырнадцать из
    # двадцати.
    #
    # После починки заголовков: у объявления с починенным названием
    # больше шансов, что вид вещи определится верно.
    try:
        from app.core.sort_clothes import run as sort_clothes

        sort_clothes(apply=True, limit=CLOTHES_LIMIT)
    except Exception as e:                                 # noqa: BLE001
        done["разбор одежды не вышел"] = str(e)[:60]

    # 10. Удаляем безнадёжные.
    #
    # Объявление, у которого заголовок непонятен и починить его не
    # удалось, в ленте бесполезно: «Даром», «Коляски», «Белград» —
    # человек не знает, что там, и не открывает. Из описания взять
    # нечего, иначе заголовок бы починился.
    #
    # Удаляем только после двух неудачных попыток в разные ночи: с
    # первого раза могла просто не ответить нейросеть, и выбрасывать
    # живое объявление из-за этого нельзя.
    try:
        done["удалено безнадёжных"] = _purge_hopeless()
    except Exception as e:                                 # noqa: BLE001
        done["удаление безнадёжных не вышло"] = str(e)[:60]

    # 11. Что осталось человеку.
    with SessionLocal() as db:
        done["осталось без города"] = db.execute(text(
            "select count(*) from listings "
            "where status='active' and (city is null or city='')")).scalar()

        try:
            from app.core.find_bundles import SQL, safe_to_delete, why_bundle
            bundles = 0
            for row in db.execute(text(SQL)).fetchall():
                why = why_bundle(row.title, row.description)
                if why and safe_to_delete(why):
                    bundles += 1
            done["похоже на перечни"] = bundles
        except Exception:                                  # noqa: BLE001
            pass

    return done



# Сколько раз заголовок должен не поддаться, прежде чем удалять.
#
# Два: с первого раза могла не ответить нейросеть — сегодня лимит
# кончился, завтра ответит. А вот если и во вторую ночь взять из
# описания нечего, там и правда пусто.
HOPELESS_TRIES = 2


def _purge_hopeless() -> int:
    """Удаляет объявления, чей заголовок не удалось починить дважды."""
    from collections import Counter

    from app.core.retitle import FAILED_ACTION
    from app.models import AuditEntry, Listing, ListingStatus

    with SessionLocal() as db:
        tries = Counter(
            row[0] for row in
            db.query(AuditEntry.target_id)
            .filter(AuditEntry.action == FAILED_ACTION)
        )
        hopeless = [key for key, count in tries.items()
                    if count >= HOPELESS_TRIES]
        if not hopeless:
            return 0

        # Объявления с перепиской или в избранном не трогаем: там
        # завязались люди, и плохой заголовок этого не отменяет.
        busy = {str(row[0]) for row in db.execute(text("""
            select distinct listing_id from chats
            union
            select distinct listing_id from favorites
        """))}
        targets = [key for key in hopeless if key not in busy]
        if not targets:
            return 0

        rows = (db.query(Listing)
                .filter(Listing.id.in_(targets),
                        Listing.status == ListingStatus.active)
                .all())
        ids = [r.id for r in rows]
        if not ids:
            return 0

        for table in ("listing_photos", "favorites", "chats", "reviews",
                      "reports", "promotions", "listing_view_logs",
                      "listing_view_daily", "listing_signal_daily",
                      "tickets", "review_invites", "listing_translations"):
            db.execute(text(f"delete from {table} where listing_id = any(:ids)"),
                       {"ids": ids})
        db.execute(text("delete from listings where id = any(:ids)"),
                   {"ids": ids})
        db.commit()
        return len(ids)


def _purge_without_city() -> int:
    """
    Удаляет объявления, у которых так и не нашлось города.

    За ночь берём не больше двухсот: восемьсот удалённых разом — это
    пятая часть ленты, и если в приметах ошибка, откатить будет нечего.
    Порциями заметно, что происходит, и есть время остановиться.
    """
    from app.models import Listing, ListingStatus

    with SessionLocal() as db:
        rows = (
            db.query(Listing.id)
            .filter(Listing.status == ListingStatus.active,
                    or_(Listing.city.is_(None), Listing.city == ""))
            .limit(200)
            .all()
        )
        ids = [row[0] for row in rows]
        if not ids:
            return 0

        # Объявления с перепиской или в избранном не трогаем: там
        # завязались люди, и отсутствие города этого не отменяет.
        busy = {row[0] for row in db.execute(text("""
            select distinct listing_id from chats where listing_id = any(:ids)
            union
            select distinct listing_id from favorites where listing_id = any(:ids)
        """), {"ids": ids})}
        targets = [i for i in ids if i not in busy]
        if not targets:
            return 0

        for table in ("listing_photos", "favorites", "chats", "reviews",
                      "reports", "promotions", "listing_view_logs",
                      "listing_view_daily", "listing_signal_daily",
                      "tickets", "review_invites", "listing_translations"):
            db.execute(text(f"delete from {table} where listing_id = any(:ids)"),
                       {"ids": targets})
        db.execute(text("delete from listings where id = any(:ids)"),
                   {"ids": targets})
        db.commit()
        return len(targets)


def report(done: dict) -> str:
    """Короткий отчёт человеку. Без цифр, равных нулю, — они не новость."""
    lines = ["Ночной уход за лентой:"]
    for key, value in done.items():
        if value in (0, None):
            continue
        lines.append(f"• {key}: {value}")

    if len(lines) == 1:
        return ""      # всё чисто — молчим, пустых отчётов не шлём
    return "\n".join(lines)


if __name__ == "__main__":
    result = run()
    text_out = report(result)
    print(text_out or "нечего делать, всё чисто")

    # Отчёт человеку — тем же путём, что и прочие уведомления.
    if text_out:
        try:
            from app.core.notifications import notify
            from app.models import User, UserRole

            with SessionLocal() as db:
                for admin in db.query(User).filter(
                        User.role == UserRole.admin).all():
                    notify(db, admin.id, text_out, force=True,
                           subject="Ночной уход за лентой")
        except Exception as e:                             # noqa: BLE001
            print("отчёт не ушёл:", str(e)[:80])
