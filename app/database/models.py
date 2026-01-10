from pathlib import Path
from sqlalchemy import BigInteger, String, ForeignKey, Integer, Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from config import DB_PATH


BASE_DIR = Path(__file__).resolve().parents[2]
DB_FILE = Path(DB_PATH)
if not DB_FILE.is_absolute():
    DB_FILE = BASE_DIR / DB_FILE

engine = create_async_engine(url=f"sqlite+aiosqlite:///{DB_FILE.as_posix()}")
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    role: Mapped[str] = mapped_column(String(20))
    currencies = relationship("UserCurrency", back_populates="user", cascade="all, delete-orphan")
    gift_orders = relationship("GiftOrder", back_populates="user", cascade="all, delete-orphan")


class Currency(Base):
    __tablename__ = "currencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    icon: Mapped[str] = mapped_column(String(10))
    description: Mapped[str] = mapped_column(Text)
    daily_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user_currencies = relationship("UserCurrency", back_populates="currency", cascade="all, delete-orphan")
    gift_prices = relationship("GiftPrice", back_populates="currency", cascade="all, delete-orphan")


class UserCurrency(Base):
    __tablename__ = "user_currencies"
    __table_args__ = (UniqueConstraint("user_id", "currency_id", name="uq_user_currency"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id", ondelete="CASCADE"))
    amount: Mapped[int] = mapped_column(Integer, default=0)

    user = relationship("User", back_populates="currencies")
    currency = relationship("Currency", back_populates="user_currencies")


class Gift(Base):
    __tablename__ = "gifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    max_orders: Mapped[int | None] = mapped_column(nullable=True)
    delivery: Mapped[str] = mapped_column(String(20), default="manual")

    prices = relationship("GiftPrice", back_populates="gift", cascade="all, delete-orphan")
    orders = relationship("GiftOrder", back_populates="gift", cascade="all, delete-orphan")
    content = relationship("GiftContent", back_populates="gift", cascade="all, delete-orphan", uselist=False)


class GiftPrice(Base):
    __tablename__ = "gift_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    gift_id: Mapped[int] = mapped_column(ForeignKey("gifts.id", ondelete="CASCADE"))
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id", ondelete="CASCADE"))
    amount: Mapped[int] = mapped_column(Integer)

    gift = relationship("Gift", back_populates="prices")
    currency = relationship("Currency", back_populates="gift_prices")


class GiftContent(Base):
    __tablename__ = "gift_contents"

    id: Mapped[int] = mapped_column(primary_key=True)
    gift_id: Mapped[int] = mapped_column(ForeignKey("gifts.id", ondelete="CASCADE"), unique=True)
    kind: Mapped[str] = mapped_column(String(20))
    data: Mapped[str] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)

    gift = relationship("Gift", back_populates="content")


class GiftOrder(Base):
    __tablename__ = "gift_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    gift_id: Mapped[int] = mapped_column(ForeignKey("gifts.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(50))
    updated_at: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user = relationship("User", back_populates="gift_orders")
    gift = relationship("Gift", back_populates="orders")


class CurrencyRequest(Base):
    __tablename__ = "currency_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id", ondelete="CASCADE"))
    comment: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[str] = mapped_column(String(50))
    decided_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decided_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user = relationship("User", backref="currency_requests")
    currency = relationship("Currency", backref="currency_requests")


class ActionLog(Base):
    __tablename__ = "action_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(50))
    details: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(50))


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
