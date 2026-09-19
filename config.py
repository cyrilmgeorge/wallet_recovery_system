import os


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "wallet-recovery-development-key"
    )

    SQLALCHEMY_DATABASE_URI = "sqlite:///wallet_recovery.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WTF_CSRF_ENABLED = True