from app.models.user import User, UserRole, Language
from app.models.category import Category
from app.models.listing import Listing, ListingTranslation, ListingPhoto, ListingStatus, Currency
from app.models.favorites import Favorite, SavedSearch
from app.models.verification import VerificationCode, VerifyChannel
from app.models.review_invite import ReviewInvite
from app.models.chat import Chat, Message
from app.models.trust import Review, Report, ReportReason, ReportStatus
from app.models.promotion import Promotion, PromotionType
from app.models.audit import AuditEntry
from app.models.login_ticket import LoginTicket
from app.models.blocked_user import BlockedUser
from app.models.document_verification import DocVerificationRequest, DocVerificationStatus, DocVerificationKind
from app.models.login_event import LoginEvent
from app.models.telegram_import_progress import TelegramImportProgress
from app.models.listing_view_daily import ListingViewDaily
from app.models.notification import Notification
from app.models.support import (
    Ticket, TicketMessage, TicketStatus, TicketTopic,
)

__all__ = [
    "User", "UserRole", "Language",
    "Category",
    "Listing", "ListingTranslation", "ListingPhoto", "ListingStatus", "Currency",
    "Favorite", "SavedSearch",
    "VerificationCode", "VerifyChannel",
    "ReviewInvite",
    "Chat", "Message",
    "Review", "Report", "ReportReason", "ReportStatus",
    "Promotion", "PromotionType",
    "AuditEntry", "LoginTicket",
    "BlockedUser",
    "ListingViewDaily",
    "DocVerificationRequest", "DocVerificationStatus", "DocVerificationKind",
    "LoginEvent",
    "TelegramImportProgress",
    "Notification",
    "Ticket", "TicketMessage", "TicketStatus", "TicketTopic",
]

# Временная слежка за откатом статуса объявления active → pending_moderation
# в обход approve()/reject() — см. докстринг в самом модуле. Подключена
# здесь, а не в main.py: так её видят все процессы, которые трогают
# базу (веб-сервер, бот, разовые скрипты вроде перевода и импорта из
# чатов), а не только сам веб-сервер.
from app.core import status_watch  # noqa: F401,E402
