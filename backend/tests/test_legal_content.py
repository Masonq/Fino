"""
Правила, Условия и Политика не должны расходиться с тем, что делает сайт.

Документы уже однажды устарели: они утверждали, что каждое объявление
проверяется человеком до публикации, когда часть объявлений давно
публикуется сразу; в Политике не было ни слова про сервисы ИИ, куда уходят
тексты и фото, про платёжного оператора в другой стране, про то, что
помеченную переписку читают модераторы, и про бонусы. Здесь это закреплено
проверками: сверяем документы с кодом, а не только между собой.

Это не юридическая экспертиза. Текст — черновик под реальное поведение
сервиса; юристу его стоит показать до того, как полагаться всерьёз.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONT = ROOT / "frontend"
BACK = ROOT / "backend"
LANGS = ("ru", "en", "sr")

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="нужен node, чтобы прочитать тексты")


@pytest.fixture(scope="module")
def docs():
    script = (
        "import { RULES, TERMS, PRIVACY } from './src/data/legalContent.js';"
        "console.log(JSON.stringify({ RULES, TERMS, PRIVACY }));"
    )
    out = subprocess.run(["node", "--input-type=module", "-e", script], cwd=FRONT,
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def text_of(docs, name, lang):
    doc = docs[name][lang]
    return "\n".join(doc["title"] for _ in [0]) + "\n" + "\n".join(
        s["h"] + "\n" + "\n".join(s["p"]) for s in doc["sections"])


# ─── структура ──────────────────────────────────────────────────────────
def test_three_languages_have_the_same_shape(docs):
    for name in docs:
        shapes = {lang: [len(s["p"]) for s in docs[name][lang]["sections"]] for lang in LANGS}
        assert shapes["ru"] == shapes["en"] == shapes["sr"], f"{name}: абзацы разошлись между языками"


def test_sections_are_numbered_in_order_and_dates_match(docs):
    for name in docs:
        for lang in LANGS:
            numbers = [int(re.match(r"(\d+)\.", s["h"]).group(1)) for s in docs[name][lang]["sections"]]
            assert numbers == list(range(1, len(numbers) + 1)), f"{name}/{lang}: нумерация разделов сбита"
        dates = {re.sub(r"\D+", " ", docs[name][lang]["updated"]).strip() for lang in LANGS}
        assert len(dates) == 1, f"{name}: дата редакции разная на разных языках"


def test_the_contact_address_is_still_wired_in(docs):
    """Адрес берётся из константы; в тексте должен остаться, на всех языках."""
    for lang in LANGS:
        assert "account@plonk.rs" in text_of(docs, "TERMS", lang)
        assert "account@plonk.rs" in text_of(docs, "PRIVACY", lang)


def test_cross_references_point_at_real_sections(docs):
    """«раздел 13», «раздел 7 Условий», «раздел 10 Правил» — такие разделы должны существовать."""
    terms = len(docs["TERMS"]["ru"]["sections"])
    rules = len(docs["RULES"]["ru"]["sections"])
    assert terms >= 13 and rules >= 11
    assert docs["TERMS"]["ru"]["sections"][6]["h"].startswith("7. Платные услуги")
    assert docs["TERMS"]["ru"]["sections"][12]["h"].startswith("13. Связь")


# ─── бонусы и баланс: главное, что просил закрепить владелец ────────────
MUST = {
    "ru": [
        ("TERMS", "не подлежит обмену на деньги"),
        ("TERMS", "не является банковским счётом"),
        ("TERMS", "только на платные услуги продвижения"),
        ("TERMS", "Бонусы возврату не подлежат"),
        ("TERMS", "сначала списываются Бонусы, затем денежные средства"),
        ("TERMS", "не за саму регистрацию"),
        ("TERMS", "аннулировать зачисленный и неиспользованный бонус"),
        ("RULES", "продавать, покупать, обменивать либо передавать бонусы"),
    ],
    "en": [
        ("TERMS", "cannot be exchanged for money"),
        ("TERMS", "is not a bank account"),
        ("TERMS", "only on paid listing-promotion services"),
        ("TERMS", "Bonuses are not refundable"),
        ("TERMS", "Bonuses are spent first, then money"),
        ("TERMS", "not for registration alone"),
        ("TERMS", "cancel a credited and unused Bonus"),
        ("RULES", "sell, buy, exchange or transfer Bonuses"),
    ],
    "sr": [
        ("TERMS", "ne može zameniti za novac"),
        ("TERMS", "nije bankovni račun"),
        ("TERMS", "isključivo na plaćene usluge izdvajanja oglasa"),
        ("TERMS", "bonusi se ne vraćaju"),
        ("TERMS", "prvo se troše bonusi, a zatim novac"),
        ("TERMS", "a ne samo zbog registracije"),
        ("TERMS", "poništiti upisan a nepotrošen bonus"),
        ("RULES", "prodavati, kupovati, razmenjivati ili prenositi bonuse"),
    ],
}


@pytest.mark.parametrize("lang", LANGS)
def test_bonus_terms_are_stated_in_every_language(docs, lang):
    for name, phrase in MUST[lang]:
        assert phrase in text_of(docs, name, lang), f"{name}/{lang}: нет формулировки «{phrase}»"


def test_documents_do_not_hard_code_bonus_amounts(docs):
    """Размер бонуса меняется в коде и в акции; в юридическом тексте он устарел бы."""
    for name in docs:
        for lang in LANGS:
            assert not re.search(r"\b(300|200)\s*RSD\b", text_of(docs, name, lang)), f"{name}/{lang}"


# ─── прежние ложные утверждения не вернулись ────────────────────────────
def test_the_old_moderate_everything_first_claim_is_gone(docs):
    stale = {
        "ru": ["подлежит проверке (модерации) Администрацией до момента его публикации",
               "вне зависимости от факта приобретения платных услуг, подлежит проверке"],
        "en": ["is subject to review (moderation) by the Administration before publication",
               "regardless of whether paid services were purchased, is subject to review"],
        "sr": ["podleže proveri (moderaciji) od strane Administracije pre objave",
               "bez obzira na to da li su kupljene plaćene usluge, podleže proveri"],
    }
    for lang in LANGS:
        body = text_of(docs, "TERMS", lang) + text_of(docs, "RULES", lang)
        for phrase in stale[lang]:
            assert phrase not in body, f"{lang}: осталось устаревшее «{phrase}»"


def test_automatic_publication_is_disclosed(docs):
    assert "могут публиковаться сразу" in text_of(docs, "TERMS", "ru")
    assert "may be published immediately" in text_of(docs, "TERMS", "en")
    assert "mogu biti objavljeni odmah" in text_of(docs, "TERMS", "sr")


# ─── документы против кода ──────────────────────────────────────────────
# Внешний сервис, которому уходят данные, обязан быть назван в Политике.
BACKEND_HOSTS = {
    "generativelanguage.googleapis.com": ("Google Gemini",),
    "api.mistral.ai": ("Mistral",),
    "api.groq.com": ("Groq",),
    "openrouter.ai": ("OpenRouter",),
    "translate.googleapis.com": ("Google",),
    "api.resend.com": ("Resend",),
    "api.telegram.org": ("Telegram",),
    "api.yookassa.ru": ("ЮKassa", "YooKassa"),
    "verification.didit.me": ("Didit",),

    "accounts.google.com": ("Google",),
}
# Внешние ресурсы, которые подгружает браузер посетителя, — они в разделе про cookie.
FRONT_HOSTS = {
    "fonts.googleapis.com": "Google Fonts",
    "telegram.org": "Telegram",
    "accounts.google.com": "Google",
    "tile.openstreetmap.org": "OpenStreetMap",
}


def _backend_hosts():
    found = set()
    for path in (BACK / "app").rglob("*.py"):
        found |= set(re.findall(r"https://([a-z0-9.-]+\.[a-z]{2,})", path.read_text(encoding="utf-8", errors="ignore")))
    return found


def test_every_outside_service_the_backend_calls_is_named_in_the_privacy_policy(docs):
    used = _backend_hosts()
    for host, names in BACKEND_HOSTS.items():
        if host not in used:
            continue                                   # сервис убрали из кода — упоминание не обязательно
        for lang in LANGS:
            body = text_of(docs, "PRIVACY", lang)
            assert any(n in body for n in names), f"{lang}: код обращается к {host}, а в Политике его нет"


def test_backend_does_not_talk_to_unlisted_services():
    """Новый внешний хост в коде — повод дополнить Политику, а потом этот список."""
    known = set(BACKEND_HOSTS) | {
        "plonk.rs", "schema.org", "www.cbr.ru", "www.googleapis.com", "shop.rs",
        "api.frankfurter.app",      # курсы валют: персональных данных не получает
        "t.me",                     # только ссылки на Telegram, не запросы
    }
    unknown = {h for h in _backend_hosts() if h not in known and not h.endswith("plonk.rs")}
    assert not unknown, f"новые внешние хосты в коде: {sorted(unknown)} — проверьте Политику"


def test_privacy_names_what_the_browser_loads_from_third_parties(docs):
    front = "\n".join(p.read_text(encoding="utf-8", errors="ignore")
                      for p in list((FRONT / "src").rglob("*.js*")) + [FRONT / "index.html", FRONT / "src" / "styles.css"])
    for host, name in FRONT_HOSTS.items():
        if host not in front:
            continue
        for lang in LANGS:
            assert name in text_of(docs, "PRIVACY", lang), f"{lang}: страница грузит {host}, а в Политике нет «{name}»"


def test_the_no_analytics_claim_stays_true():
    """
    Политика говорит: сторонней рекламы и аналитики нет. Пока это так — верно;
    подключили счётчик — нужно менять документ, и этот тест напомнит.
    """
    markers = re.compile(r"gtag\(|googletagmanager|mc\.yandex|ym\(\d|hotjar|clarity\.ms|sentry|posthog|mixpanel|"
                         r"amplitude|fbq\(|connect\.facebook|adsbygoogle|doubleclick", re.I)
    for path in list((FRONT / "src").rglob("*.js*")) + [FRONT / "index.html"]:
        assert not markers.search(path.read_text(encoding="utf-8", errors="ignore")), \
            f"{path.name}: похоже, подключена сторонняя аналитика — исправьте раздел 9 Политики"


def test_documents_match_how_the_team_account_and_chat_scan_really_work():
    """Условия говорят: команду заблокировать нельзя, а переписку проверяют средствами самого Сайта."""
    chats = (BACK / "app" / "routers" / "chats.py").read_text(encoding="utf-8")
    assert "cannot_block_team" in chats
    risk = (BACK / "app" / "core" / "chat_risk.py").read_text(encoding="utf-8")
    imports = re.findall(r"^\s*(?:import|from)\s+(\S+)", risk, re.M)
    assert set(imports) <= {"re", "__future__", "typing", "dataclasses"}, \
        f"проверка переписки стала обращаться к {imports}: Политика утверждает, что она локальная"


def test_bonus_is_spendable_only_on_promotion_and_has_no_cash_out():
    """Условия: бонус — только на продвижение и не выводится. В коде не должно быть вывода средств."""
    promo = (BACK / "app" / "routers" / "promotions.py").read_text(encoding="utf-8")
    assert "balance/topup" in promo
    for path in (BACK / "app").rglob("*.py"):
        body = path.read_text(encoding="utf-8", errors="ignore")
        assert not re.search(r"payout|withdraw|cash_?out|refund_to_card|/balance/withdraw", body, re.I), \
            f"{path.name}: в коде появился вывод или возврат средств — Условия говорят, что его нет"


def test_public_translation_servers_stay_removed():
    """Тексты объявлений (в них бывают телефоны и адреса) не уходят на чужие серверы без договора."""
    for path in (BACK / "app").rglob("*.py"):
        body = path.read_text(encoding="utf-8", errors="ignore")
        assert not re.search(r"libretranslate\.de|terraprint\.co|zillyhuhn\.com", body, re.I), path.name


def test_volunteer_confidentiality_is_promised_in_terms_and_enforced_in_code(docs):
    """Условия говорят, что помощник обязан хранить конфиденциальность; форма и сервер это требуют."""
    needles = {"ru": "обязан сохранять конфиденциальность", "en": "must keep confidential",
               "sr": "dužan je da čuva poverljivost"}
    for lang, phrase in needles.items():
        section6 = docs["TERMS"][lang]["sections"][5]
        assert phrase in "\n".join(section6["p"]), f"{lang}: в разделе 6 нет обязанности помощника"
    router = (BACK / "app" / "routers" / "volunteer.py").read_text(encoding="utf-8")
    assert "confidentiality_required" in router and "confidentiality_missing" in router
    page = (FRONT / "src" / "pages" / "Volunteer.jsx").read_text(encoding="utf-8")
    assert "accept_confidentiality: true" in page and 'to="/terms"' in page


def test_the_wallet_split_is_promised_in_terms_and_real_in_code(docs):
    """Условия обещают: сначала бонусы, потом деньги; бонус отдельно от денег."""
    wallet = (BACK / "app" / "core" / "wallet.py").read_text(encoding="utf-8")
    assert "bonus_balance" in wallet and "from_bonus = min(" in wallet


# ─── что уходит платёжному оператору: сказано конкретно и совпадает с кодом ──
def test_the_payment_operator_is_described_concretely_in_every_language(docs):
    """
    Общая фраза «данные передаются за границу» пугала и ничего не объясняла. Вместо
    неё — кто, где и что именно уходит; страна оператора названа прямо.
    """
    expect = {
        "ru": ("Российской Федерации", "реквизиты карты вводятся на странице оператора и нам не передаются",
               "имя, адрес электронной почты и номер телефона ему не передаются"),
        "en": ("Russian Federation", "card details are entered on the operator’s page and are not passed to us",
               "your name, email address and phone number are not passed to it"),
        "sr": ("Ruskoj Federaciji", "podaci o kartici unose se na stranici operatora i ne prosleđuju se nama",
               "vaše ime, adresa elektronske pošte i broj telefona ne prosleđuju mu se"),
    }
    for lang, phrases in expect.items():
        body = text_of(docs, "PRIVACY", lang)
        for phrase in phrases:
            assert phrase in body, f"{lang}: нет формулировки «{phrase}»"


def test_the_payment_request_really_carries_no_personal_contact_data():
    """
    Политика говорит: имя, почта и телефон оператору не уходят, карта вводится на его
    странице. Появился чек с почтой или встроенная форма карты — сначала правится текст.
    """
    promo = (BACK / "app" / "routers" / "promotions.py").read_text(encoding="utf-8")
    assert '"type": "redirect"' in promo, "карта вводится на странице оператора"
    for key in ('"receipt"', '"customer"', '"email"', '"phone"', '"full_name"'):
        assert key not in promo, f"в запросе к оператору появилось {key}: обновите раздел 6 Политики"



# ─── проверки по законам Республики Сербия (черновик; юристу показать перед тем, как полагаться) ───
def test_terms_state_the_consumer_right_of_withdrawal_and_its_exception(docs):
    """Закон о защите потребителей: 14 дней, для услуги — со дня заключения; исключение при явной просьбе и подтверждении."""
    expect = {
        "ru": ("в течение 14 дней со дня его заключения", "явной просьбы Пользователя", "право на отказ теряется"),
        "en": ("within 14 days of its conclusion", "express request", "the right of withdrawal is lost"),
        "sr": ("u roku od 14 dana od dana zaključenja", "izričitog zahteva korisnika", "gubi pravo na odustanak"),
    }
    for lang, phrases in expect.items():
        section7 = "\n".join(docs["TERMS"][lang]["sections"][6]["p"])
        for phrase in phrases:
            assert phrase in section7, f"{lang}: в разделе 7 нет «{phrase}»"


def test_the_consent_promised_in_terms_really_exists_in_the_payment_flow():
    """Условия говорят «отметка в окне оплаты продвижения; без неё деньгами не оплатить» — код это исполняет."""
    promo = (BACK / "app" / "routers" / "promotions.py").read_text(encoding="utf-8")
    assert promo.count('raise HTTPException(400, "consent_required")') >= 2
    assert "consent_immediate_at" in promo


def test_animals_are_allowed_when_the_law_allows_and_the_old_ban_is_gone(docs):
    old = {"ru": "живые животные — в части", "en": "live animals, insofar", "sr": "žive životinje — u delu"}
    new = {"ru": "домашних и сельскохозяйственных животных, оборот которых законом не запрещён",
           "en": "domestic and farm animals whose circulation is not prohibited by law",
           "sr": "domaćih i farmskih životinja čiji promet zakon ne zabranjuje"}
    for lang in LANGS:
        body = text_of(docs, "RULES", lang).replace("\\u0111", "đ")
        assert old[lang] not in body, f"{lang}: осталось прежнее полное запрещение"
        assert new[lang] in body, f"{lang}: нет разрешения на законные виды"


def test_the_own_referral_program_is_carved_out_of_the_pyramid_ban(docs):
    for lang, phrase in (("ru", "реферальная программа самого Сайта"), ("en", "own referral program"), ("sr", "program preporuke samog Sajta")):
        assert phrase in text_of(docs, "RULES", lang), lang


def test_privacy_names_the_supervisory_authority_and_the_deadline(docs):
    for lang, phrase in (("ru", "poverenik.rs"), ("en", "poverenik.rs"), ("sr", "poverenik.rs")):
        assert phrase in text_of(docs, "PRIVACY", lang), lang
    for lang, phrase in (("ru", "не позднее 30 дней"), ("en", "no later than 30 days"), ("sr", "najkasnije u roku od 30 dana")):
        assert phrase in text_of(docs, "PRIVACY", lang), lang
    for lang, phrase in (("ru", "ограничения обработки"), ("en", "restriction of processing"), ("sr", "ograničenje obrade")):
        assert phrase in text_of(docs, "PRIVACY", lang), lang


def test_every_sign_in_method_the_code_offers_is_named_in_terms_and_privacy(docs):
    auth = (BACK / "app" / "routers" / "auth.py").read_text(encoding="utf-8")
    assert '"/google"' in auth and '"/request-code"' in auth
    for lang, word in (("ru", "Google"), ("en", "Google"), ("sr", "Google")):
        assert word in "\n".join(docs["TERMS"][lang]["sections"][2]["p"]), f"{lang}: вход через Google не назван в Условиях, 3"
        assert word in "\n".join(docs["PRIVACY"][lang]["sections"][2]["p"]), f"{lang}: вход через Google не назван в Политике, 3"


def test_the_operator_block_is_optional_but_never_shows_a_hole():
    """Пока поля пусты — в документах нет ни «undefined», ни пустых скобок; заполнили — строка появляется."""
    script = (
        "import { OPERATOR, operatorParagraph, TERMS, PRIVACY } from './src/data/legalContent.js';"
        "const empty = ['ru','en','sr'].map(l => operatorParagraph(l).length);"
        "OPERATOR.name = 'Иван Иванов'; OPERATOR.address = 'Београд';"
        "const filled = ['ru','en','sr'].map(l => operatorParagraph(l)[0]);"
        "const all = JSON.stringify({TERMS, PRIVACY});"
        "console.log(JSON.stringify({ empty, filled, bad: /undefined|\\[object|null/.test(all) }));"
    )
    out = subprocess.run(["node", "--input-type=module", "-e", script], cwd=FRONT,
                         capture_output=True, text=True, check=True).stdout
    got = json.loads(out)
    assert got["empty"] == [0, 0, 0]
    assert all("Иван Иванов" in x and "Београд" in x for x in got["filled"])
    assert got["bad"] is False


def test_terms_say_card_payment_can_be_unavailable_without_touching_the_refund_right(docs):
    """Владелец может выключить оплату картой в админке: Условия об этом предупреждают и не отменяют возврат."""
    expect = {"ru": ("может быть временно недоступна", "права Пользователя на возврат неизрасходованных"),
              "en": ("may be temporarily unavailable", "right to a refund of unspent funds"),
              "sr": ("može privremeno biti nedostupno", "pravo korisnika na povraćaj neutrošenih")}
    for lang, phrases in expect.items():
        section7 = "\n".join(docs["TERMS"][lang]["sections"][6]["p"])
        for phrase in phrases:
            assert phrase in section7, f"{lang}: нет «{phrase}»"
