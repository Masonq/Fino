#!/usr/bin/env python3
"""
Отклоняет разом всё, что сейчас в очереди на модерацию.

Та же запись, что делает POST /moderation/{id}/reject (статус
rejected, причина, запись в audit-лог, уведомление владельцу) — но по
всей очереди сразу, без разбора по одному. actor=None в журнале —
решение принято не конкретным модератором с аккаунтом, а разовой
командой владельца сайта.

    python tools/reject-all-pending.py                # сухой прогон
    python tools/reject-all-pending.py --apply         # применить
    python tools/reject-all-pending.py --apply --reason "..."
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.audit import record  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.notifications import notify_moderation  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402

DEFAULT_REASON = "Объявление снято с проверки при массовой очистке очереди модерации"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--reason", default=DEFAULT_REASON)
    ap.add_argument("--show", type=int, default=20)
    args = ap.parse_args()

    with SessionLocal() as db:
        rows = (
            db.query(Listing, ListingTranslation)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.status == ListingStatus.pending_moderation)
            .order_by(Listing.created_at.desc())
            .all()
        )

        print(f"в очереди на модерацию: {len(rows)}")
        if not rows:
            return

        by_source = Counter(l.external_source or "сайт" for l, _ in rows)
        for source, count in by_source.most_common():
            print(f"  {source}: {count}")

        print(f"\nпримеры (первые {args.show}):")
        for listing, tr in rows[:args.show]:
            print(f"  {(tr.title or '')[:60]}")

        if not args.apply:
            print("\n  (ничего не изменено — добавьте --apply)")
            return

        # Уведомление владельцу — best-effort, как и у самого reject()
        # (см. _after_reject в moderation.py): у объявлений, перенесённых
        # из Telegram-чатов, владелец — служебный аккаунт чата, ему
        # уведомление ничего не даёт, но и не вредит; для объявлений от
        # реальных продавцов через бота это единственный способ узнать,
        # почему объявление не опубликовалось.
        for listing, tr in rows:
            listing.status = ListingStatus.rejected
            listing.rejection_reason = args.reason
            record(db, None, "listing.reject", target_type="listing",
                   target_id=listing.id, reason=args.reason,
                   owner=str(listing.owner_id), bulk=True)
            try:
                notify_moderation(db, listing.owner_id, tr.title or "", False,
                                  args.reason, listing_id=listing.id)
            except Exception:
                pass

        db.commit()
        print(f"\nотклонено: {len(rows)}")


if __name__ == "__main__":
    main()
