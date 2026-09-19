from collections import defaultdict
from decimal import Decimal

from sqlalchemy import inspect, text

from ..extensions import db


def migrate_wallet_table():
    """
    Add the wallet status column if it does not already exist.

    Existing exit_requested values are converted into
    the new wallet status lifecycle.
    """

    inspector = inspect(db.engine)

    if "wallets" not in inspector.get_table_names():
        return

    columns = inspector.get_columns("wallets")

    column_names = {
        column["name"]
        for column in columns
    }

    if "status" not in column_names:

        with db.engine.begin() as connection:

            connection.execute(
                text(
                    """
                    ALTER TABLE wallets
                    ADD COLUMN status VARCHAR(30)
                    NOT NULL
                    DEFAULT 'active'
                    """
                )
            )

            if "exit_requested" in column_names:

                connection.execute(
                    text(
                        """
                        UPDATE wallets
                        SET status = 'exit_requested'
                        WHERE exit_requested = 1
                        """
                    )
                )


def migrate_recovery_transaction_table():
    """
    Add recovery_type to existing recovery transactions.

    Existing transactions are treated as normal surplus
    recoveries.
    """

    inspector = inspect(db.engine)

    if "recovery_transactions" not in inspector.get_table_names():
        return

    columns = inspector.get_columns(
        "recovery_transactions"
    )

    column_names = {
        column["name"]
        for column in columns
    }

    if "recovery_type" in column_names:
        return

    with db.engine.begin() as connection:

        connection.execute(
            text(
                """
                ALTER TABLE recovery_transactions
                ADD COLUMN recovery_type VARCHAR(30)
                NOT NULL
                DEFAULT 'surplus'
                """
            )
        )


def _get_existing_wallet_transaction(
    recovery_transaction
):
    """
    Find the wallet ledger transaction already associated
    with a recovery transaction.

    The reference code is used as the stable identifier.
    """

    from ..models import WalletTransaction

    if recovery_transaction.recovery_type == "exit":

        description = (
            "Exit recovery transaction "
            f"{recovery_transaction.reference_code}"
        )

        transaction_type = "exit_recovery"

    else:

        description = (
            "Recovery transaction "
            f"{recovery_transaction.reference_code}"
        )

        transaction_type = "recovery"

    return (
        WalletTransaction.query
        .filter_by(
            wallet_id=recovery_transaction.wallet_id,
            user_id=recovery_transaction.user_id,
            transaction_type=transaction_type,
            description=description,
        )
        .first()
    )


def reconcile_existing_recovery_transactions():
    """
    Reconcile historical recovery transactions with the
    wallet transaction ledger.

    IMPORTANT:

    Historical recovery transactions may already be reflected
    in Wallet.balance. Therefore this migration MUST NOT deduct
    the recovery amounts from Wallet.balance again.

    Instead, the migration reconstructs ledger entries from the
    existing final wallet balance and creates any missing
    WalletTransaction records.

    The migration is safe to run repeatedly because an existing
    ledger transaction is detected before a new one is created.
    """

    from ..models import (
        RecoveryTransaction,
        Wallet,
        WalletTransaction,
    )

    completed_transactions = (
        RecoveryTransaction.query
        .filter_by(status="completed")
        .order_by(
            RecoveryTransaction.wallet_id.asc(),
            RecoveryTransaction.created_at.asc(),
            RecoveryTransaction.id.asc(),
        )
        .all()
    )

    if not completed_transactions:
        return

    transactions_by_wallet = defaultdict(list)

    for recovery_transaction in completed_transactions:

        transactions_by_wallet[
            recovery_transaction.wallet_id
        ].append(recovery_transaction)

    for wallet_id, recovery_transactions in (
        transactions_by_wallet.items()
    ):

        wallet = db.session.get(
            Wallet,
            wallet_id
        )

        if wallet is None:

            raise RuntimeError(
                "A recovery transaction references a wallet "
                "that does not exist."
            )

        for recovery_transaction in recovery_transactions:

            if (
                wallet.user_id
                != recovery_transaction.user_id
            ):

                raise RuntimeError(
                    "Recovery transaction ownership does not "
                    "match wallet ownership."
                )

        missing_transactions = []

        for recovery_transaction in recovery_transactions:

            existing_transaction = (
                _get_existing_wallet_transaction(
                    recovery_transaction
                )
            )

            if existing_transaction is None:

                missing_transactions.append(
                    recovery_transaction
                )

        if not missing_transactions:
            continue

        """
        The wallet balance is the current balance after the
        historical transactions have already been applied.

        To reconstruct historical balance_after values, begin
        with the current balance and add back every completed
        historical recovery amount.

        We then replay the recovery transactions in their
        original order.

        Exit recovery always ends with balance 0.
        """

        historical_total = Decimal("0.00")

        for recovery_transaction in recovery_transactions:

            historical_total += Decimal(
                recovery_transaction.amount
            )

        running_balance = (
            Decimal(wallet.balance)
            + historical_total
        )

        for recovery_transaction in recovery_transactions:

            recovery_amount = Decimal(
                recovery_transaction.amount
            )

            if recovery_transaction.recovery_type == "exit":

                running_balance = Decimal("0.00")

                transaction_type = "exit_recovery"

                description = (
                    "Exit recovery transaction "
                    f"{recovery_transaction.reference_code}"
                )

                balance_after = Decimal("0.00")

            else:

                running_balance -= recovery_amount

                transaction_type = "recovery"

                description = (
                    "Recovery transaction "
                    f"{recovery_transaction.reference_code}"
                )

                balance_after = running_balance

            existing_transaction = (
                _get_existing_wallet_transaction(
                    recovery_transaction
                )
            )

            if existing_transaction is not None:
                continue

            wallet_transaction = WalletTransaction(
                wallet_id=wallet.id,
                user_id=wallet.user_id,
                transaction_type=transaction_type,
                amount=recovery_amount,
                balance_after=balance_after,
                description=description,
            )

            db.session.add(
                wallet_transaction
            )

    db.session.commit()