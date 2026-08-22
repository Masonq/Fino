"""
Убирает демонстрационные объявления и всё, что к ним привязано.

Демо-данные создавались, пока витрина была пустой. Теперь в ленте настоящие
объявления, и вымышленные среди них только путают: покупатель напишет
несуществующему продавцу.

Удаляются объявления демо-продавца вместе с переводами, фотографиями,
отзывами и избранным, затем сами демо-аккаунты. Ничего чужого не трогаем:
отбор идёт по аккаунтам, созданным сидом.

    python3 tools/drop-demo.py            показать, что будет удалено
    python3 tools/drop-demo.py --yes      удалить
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from app.core.database import SessionLocal
from app.models import Favorite, Listing, ListingPhoto, ListingTranslation, Review, User


def main() -> None:
    confirm = "--yes" in sys.argv
    db = SessionLocal()
    try:
        # демо-аккаунты помечены паролем-заглушкой: войти в них нельзя
        users = db.query(User).filter(User.hashed_password == "demo").all()
        if not users:
            print("демо-аккаунтов не найдено")
            return

        user_ids = [u.id for u in users]
        listings = db.query(Listing).filter(Listing.owner_id.in_(user_ids)).all()
        listing_ids = [l.id for l in listings]

        print("будет удалено:")
        for u in users:
            print(f"  аккаунт: {u.display_name}")
        print(f"  объявлений: {len(listing_ids)}")
        reviews = db.query(Review).filter(Review.target_id.in_(user_ids)).count()
        print(f"  отзывов: {reviews}")

        if not confirm:
            print("\nничего не удалено — добавь --yes")
            return

        if listing_ids:
            # избранное чистим первым: иначе останутся ссылки на удалённое
            db.query(Favorite).filter(
                Favorite.listing_id.in_(listing_ids)).delete(synchronize_session=False)
            db.query(ListingPhoto).filter(
                ListingPhoto.listing_id.in_(listing_ids)).delete(synchronize_session=False)
            db.query(ListingTranslation).filter(
                ListingTranslation.listing_id.in_(listing_ids)).delete(synchronize_session=False)
            db.query(Listing).filter(
                Listing.id.in_(listing_ids)).delete(synchronize_session=False)
        db.query(Review).filter(Review.target_id.in_(user_ids)).delete(synchronize_session=False)
        db.query(Review).filter(Review.author_id.in_(user_ids)).delete(synchronize_session=False)
        db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        db.commit()
        print("\nудалено")
    finally:
        db.close()


if __name__ == "__main__":
    main()
