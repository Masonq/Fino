"""
Системные окна браузера (confirm/alert) заменены своими.

В приложении с главного экрана iPhone и во встроенных браузерах (Telegram, Instagram) window.confirm бывает подавлен и
молча отвечает «нет»: кнопка «Удалить» ничего не делала. Было 3 подтверждения и 15 сообщений в 9 файлах.
Подтверждения теперь — шторка снизу (components/ConfirmHost.jsx), сообщения — остров уведомлений (kind: 'warn').
"""
import json
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


def test_no_native_dialogs_are_left_in_the_app():
    for path in SRC.rglob("*.jsx"):
        body = path.read_text(encoding="utf-8")
        code = re.sub(r"//[^\n]*|/\*.*?\*/|\{/\*.*?\*/\}", "", body, flags=re.S)        # комментарии не в счёт
        assert not re.search(r"window\.(confirm|alert|prompt)\(|(?<![\w.])alert\(|(?<![\w.])confirm\(", code), path.name


def test_the_confirm_host_is_mounted_once_next_to_the_island():
    app = (SRC / "App.jsx").read_text(encoding="utf-8")
    assert app.count("<ConfirmHost />") == 1 and app.index("<Island />") < app.index("<ConfirmHost />")


def test_confirm_falls_back_to_the_system_dialog_only_without_a_host():
    helper = (SRC / "utils" / "confirm.js").read_text(encoding="utf-8")
    assert "__plonkConfirmReady" in helper and "window.confirm(title)" in helper
    host = (SRC / "components" / "ConfirmHost.jsx").read_text(encoding="utf-8")
    assert "__plonkConfirmReady = true" in host and "'Escape'" in host and 'role="alertdialog"' in host and 'aria-modal="true"' in host


def test_destructive_actions_ask_with_a_red_button():
    for name, phrase in (("MyListings", "my.confirm_delete"), ("ChatScreen", "chat.confirm_block"), ("Notifications", "notif.clear_all_confirm")):
        body = (SRC / "pages" / f"{name}.jsx").read_text(encoding="utf-8")
        start = body.index(phrase)
        assert "await confirmSheet(" in body[start - 60:start] and "danger: true" in body[start:start + 160], name


def test_errors_go_to_the_island_as_warnings():
    total = 0
    for path in SRC.rglob("*.jsx"):
        total += len(re.findall(r"showIsland\(\{ text: [^}]*kind: 'warn' \}\)", path.read_text(encoding="utf-8")))
    assert total >= 14


def test_sheet_strings_exist_in_every_language():
    for lang in ("ru", "en", "sr"):
        data = json.loads((SRC / "i18n" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
        assert set(data["confirm"]) >= {"yes", "cancel", "delete", "block", "clear"}, lang
