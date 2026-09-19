from flask_login import UserMixin

from .extensions import db


class User(UserMixin, db.Model):
    __tablename__ ="users"

    id=db.Column(
        db.Integer,
        primary_key=True
    )

    username=db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    email=db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash=db.Column(
        db.String(255),
        nullable=False
    )

    wallets=db.relationship(
        "Wallet",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Wallet(db.Model):
    __tablename__ = "wallets"

    id=db.Column(
        db.Integer,
        primary_key=True
    )

    name=db.Column(
        db.String(100),
        nullable=False
    )

    provider=db.Column(
        db.String(100),
        nullable=False
    )

    balance=db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0
    )

    minimum_balance=db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0
    )

    status=db.Column(
        db.String(30),
        nullable=False,
        default="active"
    )

    # Legacy database compatibility.
    # The application uses `status` as the source of truth,
    # but the existing SQLite database still contains this
    # NOT NULL column.
    exit_requested=db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    user_id=db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    user = db.relationship(
        "User",
        back_populates="wallets"
    )

    transactions = db.relationship(
        "WalletTransaction",
        back_populates="wallet",
        cascade="all, delete-orphan"
    )


class WalletTransaction(db.Model):
    __tablename__ = "wallet_transactions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    wallet_id = db.Column(
        db.Integer,
        db.ForeignKey("wallets.id"),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    transaction_type = db.Column(
        db.String(30),
        nullable=False
    )

    amount = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    balance_after = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    description = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.now()
    )

    wallet = db.relationship(
        "Wallet",
        back_populates="transactions"
    )

    user = db.relationship(
        "User",
        backref="wallet_transactions"
    )


class RecoveryOption(db.Model):
    __tablename__ = "recovery_options"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    description = db.Column(
        db.String(255),
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    transactions = db.relationship(
        "RecoveryTransaction",
        back_populates="recovery_option"
    )


class RecoveryTransaction(db.Model):
    __tablename__ = "recovery_transactions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    amount = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="completed"
    )

    recovery_type = db.Column(
        db.String(30),
        nullable=False,
        default="surplus"
    )

    reference_code = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.now()
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    wallet_id = db.Column(
        db.Integer,
        db.ForeignKey("wallets.id"),
        nullable=False
    )

    recovery_option_id = db.Column(
        db.Integer,
        db.ForeignKey("recovery_options.id"),
        nullable=False
    )

    user = db.relationship(
        "User",
        backref="recovery_transactions"
    )

    wallet = db.relationship(
        "Wallet",
        backref="recovery_transactions"
    )

    recovery_option = db.relationship(
        "RecoveryOption",
        back_populates="transactions"
    )