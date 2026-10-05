import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class ListingEmbedding(Base):
    """Смысловой отпечаток объявления (вектор 384 числа float32) — для поиска по смыслу: «софа» находит «диван»,
    «sofa» — тоже. Считает служба plonk-embed, заполняет задача plonk-embed-index."""
    __tablename__ = "listing_embeddings"

    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    vec: Mapped[bytes] = mapped_column(LargeBinary)
    text_hash: Mapped[str] = mapped_column(String(40))  # пересчитываем, только если название/описание поменялись
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
