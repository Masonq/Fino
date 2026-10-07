"""
Сообщения сайта о сбоях до запуска (белый экран): что за браузер и какие ошибки были. Пишется в журнал
службы, смотреть: journalctl -u fino --since today | grep client-log
"""
import json
import logging

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["client-log"])
log = logging.getLogger("client-log")


@router.post("/client-log")
async def client_log(request: Request):
    raw = (await request.body())[:4000]
    try:
        d = json.loads(raw or b"{}")
    except Exception:  # noqa: BLE001
        d = {"raw": raw.decode("utf8", "replace")[:500]}
    line = "client-log %s | %s | %s | %s" % (d.get("kind"), str(d.get("url"))[:200], str(d.get("ua"))[:200], " || ".join(map(str, d.get("errors") or []))[:1500])
    log.warning(line)
    print(line, flush=True)   # в журнал службы наверняка (настройки журналов приложения могут глушить warning)
    return {"ok": True}
