from decimal import Decimal

from ..extensions import db
from ..models import RecoveryOption, RecoveryTransaction


DEFAULT_RECOVERY_OPTIONS = [
    {
        "name": "Reward Credits",
        "description": (
            "Convert stranded wallet value into reward credits."
        )
    },
    {
        "name": "Voucher",
        "description": (
            "Convert stranded wallet value into a simulated voucher."
        )
    },
    {
        "name": "Wallet Consolidation",
        "description": (
            "Consolidate recoverable value into a simulated wallet credit."
        )
    }
]


def seed_recovery_options():
    for option_data in DEFAULT_RECOVERY_OPTIONS:
        existing_option = RecoveryOption.query.filter_by(
            name=option_data["name"]
        ).first()

        if existing_option is None:
            option = RecoveryOption(
                name=option_data["name"],
                description=option_data["description"]
            )

            db.session.add(option)

    db.session.commit()


def get_recovered_amount_for_wallet(wallet_id):
    """
    Return the total amount already recovered from a wallet
    through completed recovery transactions.
    """

    transactions = RecoveryTransaction.query.filter_by(
        wallet_id=wallet_id,
        status="completed"
    ).all()

    total_recovered = Decimal("0.00")

    for transaction in transactions:
        total_recovered += Decimal(transaction.amount)

    return total_recovered