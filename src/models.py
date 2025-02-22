from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    tg_id: Mapped[int] = mapped_column(unique=True, index=True, nullable=False)

    coins: Mapped[list["Coin"]] = relationship(
        "Coin", secondary="user_coin", back_populates="users"
    )


class Coin(Base):
    __tablename__ = "coin"
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    chain_id: Mapped[str] = mapped_column(nullable=False)
    token_address: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    token_name: Mapped[str] = mapped_column(nullable=False)
    price: Mapped[float] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list["User"]] = relationship(
        "User", secondary="user_coin", back_populates="coins"
    )


class UserCoin(Base):
    __tablename__ = "user_coin"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    coin_id: Mapped[int] = mapped_column(
        ForeignKey("coin.id", ondelete="CASCADE"), primary_key=True
    )
    alert_price: Mapped[float] = mapped_column(nullable=True)
