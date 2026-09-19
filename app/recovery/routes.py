from decimal import Decimal, InvalidOperation
from uuid import uuid4

from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange

from . import recovery
from ..extensions import db
from ..models import (
    RecoveryOption,
    RecoveryTransaction,
    Wallet,
    WalletTransaction,
)
from ..services.stranded_balance import (
    calculate_remaining_recoverable_balance,
)


class RecoveryForm(FlaskForm):
    amount = DecimalField(
        "Recovery Amount",
        validators=[
            DataRequired(),
            NumberRange(min=0.01)
        ],
        places=2
    )

    recovery_option_id = SelectField(
        "Recovery Option",
        coerce=int,
        validators=[
            DataRequired()
        ]
    )

    submit = SubmitField("Recover Value")


class ExitRecoveryForm(FlaskForm):
    submit = SubmitField("Retrieve Trapped Value")


@recovery.route("/options")
@login_required
def options():
    user_wallets = Wallet.query.filter_by(
        user_id=current_user.id
    ).all()

    wallet_data = []
    total_remaining = Decimal("0.00")

    for wallet in user_wallets:

        remaining_recoverable = (
            calculate_remaining_recoverable_balance(
                wallet.balance,
                wallet.minimum_balance
            )
        )

        if remaining_recoverable > Decimal("0.00"):

            wallet_data.append(
                {
                    "wallet": wallet,
                    "remaining_recoverable": (
                        remaining_recoverable
                    )
                }
            )

        total_remaining += remaining_recoverable

    available_options = RecoveryOption.query.filter_by(
        is_active=True
    ).all()

    return render_template(
        "recovery/options.html",
        total_stranded=total_remaining,
        wallet_data=wallet_data,
        recovery_options=available_options
    )


@recovery.route(
    "/request/<int:wallet_id>",
    methods=["GET", "POST"]
)
@login_required
def request_recovery(wallet_id):

    wallet = Wallet.query.filter_by(
        id=wallet_id,
        user_id=current_user.id
    ).first_or_404()

    if wallet.status != "active":
        flash(
            "This wallet is not active for surplus recovery.",
            "error"
        )

        return redirect(
            url_for("wallets.index")
        )

    remaining_recoverable = (
        calculate_remaining_recoverable_balance(
            wallet.balance,
            wallet.minimum_balance
        )
    )

    available_options = RecoveryOption.query.filter_by(
        is_active=True
    ).all()

    form = RecoveryForm()

    form.recovery_option_id.choices = [
        (option.id, option.name)
        for option in available_options
    ]

    if form.validate_on_submit():

        try:
            requested_amount = Decimal(
                form.amount.data
            )

        except (InvalidOperation, TypeError):

            flash(
                "Invalid recovery amount.",
                "error"
            )

            return render_template(
                "recovery/request.html",
                form=form,
                wallet=wallet,
                stranded_balance=(
                    remaining_recoverable
                )
            )

        if requested_amount <= Decimal("0.00"):

            flash(
                "Recovery amount must be greater than zero.",
                "error"
            )

            return render_template(
                "recovery/request.html",
                form=form,
                wallet=wallet,
                stranded_balance=(
                    remaining_recoverable
                )
            )

        if requested_amount > remaining_recoverable:

            flash(
                "Recovery amount cannot exceed the "
                "remaining recoverable balance.",
                "error"
            )

            return render_template(
                "recovery/request.html",
                form=form,
                wallet=wallet,
                stranded_balance=(
                    remaining_recoverable
                )
            )

        recovery_option = RecoveryOption.query.filter_by(
            id=form.recovery_option_id.data,
            is_active=True
        ).first()

        if recovery_option is None:

            flash(
                "The selected recovery option is not available.",
                "error"
            )

            return render_template(
                "recovery/request.html",
                form=form,
                wallet=wallet,
                stranded_balance=(
                    remaining_recoverable
                )
            )

        new_balance = (
            Decimal(wallet.balance)
            - requested_amount
        )

        if new_balance < Decimal(
            wallet.minimum_balance
        ):

            flash(
                "The recovery would reduce the wallet "
                "below its required minimum balance.",
                "error"
            )

            return render_template(
                "recovery/request.html",
                form=form,
                wallet=wallet,
                stranded_balance=(
                    remaining_recoverable
                )
            )

        reference_code = (
            f"REC-{uuid4().hex[:12].upper()}"
        )

        wallet.balance = new_balance

        wallet_transaction = WalletTransaction(
            wallet_id=wallet.id,
            user_id=current_user.id,
            transaction_type="recovery",
            amount=requested_amount,
            balance_after=new_balance,
            description=(
                f"Recovery transaction "
                f"{reference_code}"
            )
        )

        recovery_transaction = RecoveryTransaction(
            amount=requested_amount,
            status="completed",
            recovery_type="surplus",
            reference_code=reference_code,
            user_id=current_user.id,
            wallet_id=wallet.id,
            recovery_option_id=recovery_option.id
        )

        db.session.add(wallet_transaction)
        db.session.add(recovery_transaction)

        db.session.commit()

        flash(
            "Recovery transaction completed successfully.",
            "success"
        )

        return redirect(
            url_for("recovery.transactions")
        )

    return render_template(
        "recovery/request.html",
        form=form,
        wallet=wallet,
        stranded_balance=(
            remaining_recoverable
        )
    )


@recovery.route(
    "/exit/<int:wallet_id>",
    methods=["GET", "POST"]
)
@login_required
def exit_recovery(wallet_id):

    wallet = Wallet.query.filter_by(
        id=wallet_id,
        user_id=current_user.id
    ).first_or_404()

    if wallet.status != "exit_requested":

        flash(
            "This wallet is not currently awaiting exit recovery.",
            "error"
        )

        return redirect(
            url_for("wallets.index")
        )

    trapped_value = Decimal(
        wallet.balance
    )

    if trapped_value <= Decimal("0.00"):

        flash(
            "This wallet has no value available for exit recovery.",
            "error"
        )

        return redirect(
            url_for("wallets.index")
        )

    form = ExitRecoveryForm()

    if form.validate_on_submit():

        exit_option = RecoveryOption.query.filter_by(
            name="Wallet Consolidation",
            is_active=True
        ).first()

        if exit_option is None:

            flash(
                "The wallet consolidation recovery option "
                "is currently unavailable.",
                "error"
            )

            return render_template(
                "recovery/exit.html",
                form=form,
                wallet=wallet,
                trapped_value=trapped_value
            )

        reference_code = (
            f"EXIT-{uuid4().hex[:12].upper()}"
        )

        wallet.balance = Decimal("0.00")

        wallet.status = "exited"

        wallet_transaction = WalletTransaction(
            wallet_id=wallet.id,
            user_id=current_user.id,
            transaction_type="exit_recovery",
            amount=trapped_value,
            balance_after=Decimal("0.00"),
            description=(
                f"Exit recovery transaction "
                f"{reference_code}"
            )
        )

        recovery_transaction = RecoveryTransaction(
            amount=trapped_value,
            status="completed",
            recovery_type="exit",
            reference_code=reference_code,
            user_id=current_user.id,
            wallet_id=wallet.id,
            recovery_option_id=exit_option.id
        )

        db.session.add(wallet_transaction)
        db.session.add(recovery_transaction)

        db.session.commit()

        flash(
            "Trapped value was retrieved successfully. "
            "The wallet is now closed.",
            "success"
        )

        return redirect(
            url_for("wallets.index")
        )

    return render_template(
        "recovery/exit.html",
        form=form,
        wallet=wallet,
        trapped_value=trapped_value
    )


@recovery.route("/transactions")
@login_required
def transactions():

    user_transactions = (
        RecoveryTransaction.query
        .filter_by(
            user_id=current_user.id
        )
        .order_by(
            RecoveryTransaction.created_at.desc()
        )
        .all()
    )

    return render_template(
        "recovery/transactions.html",
        transactions=user_transactions
    )