from decimal import Decimal

from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, SubmitField, StringField
from wtforms.validators import DataRequired, Length, NumberRange

from . import wallets
from ..extensions import db
from ..models import Wallet, WalletTransaction
from ..services.recovery import get_recovered_amount_for_wallet
from ..services.stranded_balance import (
    calculate_remaining_recoverable_balance,
    calculate_stranded_balance,
    calculate_trapped_value,
)


class WalletForm(FlaskForm):
    name = StringField(
        "Wallet Name",
        validators=[
            DataRequired(),
            Length(min=2, max=100)
        ]
    )

    provider = StringField(
        "Provider",
        validators=[
            DataRequired(),
            Length(min=2, max=100)
        ]
    )

    balance = DecimalField(
        "Current Balance",
        validators=[
            DataRequired(),
            NumberRange(min=0)
        ],
        places=2
    )

    minimum_balance = DecimalField(
        "Minimum Balance",
        validators=[
            DataRequired(),
            NumberRange(min=0)
        ],
        places=2
    )

    exit_requested = BooleanField(
        "I want to leave or consolidate this wallet"
    )

    submit = SubmitField("Add Wallet")


class AddMoneyForm(FlaskForm):
    amount = DecimalField(
        "Amount to Add",
        validators=[
            DataRequired(),
            NumberRange(min=0.01)
        ],
        places=2
    )

    description = StringField(
        "Description",
        validators=[
            DataRequired(),
            Length(min=2, max=255)
        ]
    )

    submit = SubmitField("Add Money")


class WalletStatusForm(FlaskForm):
    submit = SubmitField("Change Wallet Status")


@wallets.route("/")
@login_required
def index():

    user_wallets = Wallet.query.filter_by(
        user_id=current_user.id
    ).all()

    wallet_data = []

    status_form = WalletStatusForm()

    for wallet in user_wallets:

        recoverable_surplus = (
            calculate_stranded_balance(
                wallet.balance,
                wallet.minimum_balance
            )
        )

        remaining_recoverable = (
            calculate_remaining_recoverable_balance(
                wallet.balance,
                wallet.minimum_balance
            )
        )

        recovered_amount = (
            get_recovered_amount_for_wallet(
                wallet.id
            )
        )

        trapped_value = calculate_trapped_value(
            wallet.balance,
            wallet.minimum_balance,
            wallet.status
        )

        wallet_data.append(
            {
                "wallet": wallet,
                "stranded_balance": (
                    recoverable_surplus
                ),
                "recovered_amount": (
                    recovered_amount
                ),
                "remaining_recoverable": (
                    remaining_recoverable
                ),
                "trapped_value": trapped_value,
            }
        )

    return render_template(
        "wallets/index.html",
        wallet_data=wallet_data,
        status_form=status_form
    )


@wallets.route(
    "/add",
    methods=["GET", "POST"]
)
@login_required
def add():

    form = WalletForm()

    if form.validate_on_submit():

        balance = Decimal(
            form.balance.data
        )

        minimum_balance = Decimal(
            form.minimum_balance.data
        )

        if minimum_balance > balance:

            flash(
                "Minimum balance cannot be greater "
                "than the current balance.",
                "error"
            )

            return render_template(
                "wallets/add.html",
                form=form
            )

        wallet_status = (
            "exit_requested"
            if form.exit_requested.data
            else "active"
        )

        wallet = Wallet(
            name=form.name.data.strip(),
            provider=form.provider.data.strip(),
            balance=balance,
            minimum_balance=minimum_balance,
            status=wallet_status,
            user_id=current_user.id
        )

        db.session.add(wallet)

        db.session.flush()

        if balance > Decimal("0.00"):

            initial_transaction = WalletTransaction(
                wallet_id=wallet.id,
                user_id=current_user.id,
                transaction_type="initial_balance",
                amount=balance,
                balance_after=balance,
                description="Initial wallet balance"
            )

            db.session.add(
                initial_transaction
            )

        db.session.commit()

        flash(
            "Wallet added successfully.",
            "success"
        )

        return redirect(
            url_for("wallets.index")
        )

    return render_template(
        "wallets/add.html",
        form=form
    )


@wallets.route(
    "/<int:wallet_id>/add-money",
    methods=["GET", "POST"]
)
@login_required
def add_money(wallet_id):

    wallet = Wallet.query.filter_by(
        id=wallet_id,
        user_id=current_user.id
    ).first_or_404()

    form = AddMoneyForm()

    if form.validate_on_submit():

        if wallet.status != "active":

            flash(
                "Money can only be added to an active wallet.",
                "error"
            )

            return render_template(
                "wallets/add_money.html",
                form=form,
                wallet=wallet
            )

        amount = Decimal(
            form.amount.data
        )

        if amount <= Decimal("0.00"):

            flash(
                "Amount must be greater than zero.",
                "error"
            )

            return render_template(
                "wallets/add_money.html",
                form=form,
                wallet=wallet
            )

        wallet.balance = (
            Decimal(wallet.balance)
            + amount
        )

        transaction = WalletTransaction(
            wallet_id=wallet.id,
            user_id=current_user.id,
            transaction_type="deposit",
            amount=amount,
            balance_after=wallet.balance,
            description=form.description.data.strip()
        )

        db.session.add(transaction)

        db.session.commit()

        flash(
            "Money added successfully.",
            "success"
        )

        return redirect(
            url_for("wallets.index")
        )

    return render_template(
        "wallets/add_money.html",
        form=form,
        wallet=wallet
    )


@wallets.route(
    "/<int:wallet_id>/toggle-exit",
    methods=["POST"]
)
@login_required
def toggle_exit(wallet_id):

    wallet = Wallet.query.filter_by(
        id=wallet_id,
        user_id=current_user.id
    ).first_or_404()

    form = WalletStatusForm()

    if not form.validate_on_submit():

        flash(
            "Invalid wallet status request.",
            "error"
        )

        return redirect(
            url_for("wallets.index")
        )

    if wallet.status == "active":

        wallet.status = "exit_requested"

        db.session.commit()

        flash(
            "Wallet marked for exit/consolidation.",
            "success"
        )

    elif wallet.status == "exit_requested":

        wallet.status = "active"

        db.session.commit()

        flash(
            "Wallet resumed. You can add money again.",
            "success"
        )

    else:

        flash(
            "This wallet has already been exited and cannot "
            "be resumed.",
            "error"
        )

    return redirect(
        url_for("wallets.index")
    )


@wallets.route(
    "/<int:wallet_id>/transactions"
)
@login_required
def transactions(wallet_id):

    wallet = Wallet.query.filter_by(
        id=wallet_id,
        user_id=current_user.id
    ).first_or_404()

    wallet_transactions = (
        WalletTransaction.query
        .filter_by(
            wallet_id=wallet.id,
            user_id=current_user.id
        )
        .order_by(
            WalletTransaction.created_at.desc()
        )
        .all()
    )

    return render_template(
        "wallets/transactions.html",
        wallet=wallet,
        transactions=wallet_transactions
    )


@wallets.route("/stranded")
@login_required
def stranded():

    user_wallets = Wallet.query.filter_by(
        user_id=current_user.id
    ).all()

    stranded_data = []

    total_recoverable_surplus = (
        Decimal("0.00")
    )

    total_recovered = Decimal("0.00")

    total_remaining = Decimal("0.00")

    total_trapped = Decimal("0.00")

    for wallet in user_wallets:

        recoverable_surplus = (
            calculate_stranded_balance(
                wallet.balance,
                wallet.minimum_balance
            )
        )

        recovered_amount = (
            get_recovered_amount_for_wallet(
                wallet.id
            )
        )

        remaining_recoverable = (
            calculate_remaining_recoverable_balance(
                wallet.balance,
                wallet.minimum_balance
            )
        )

        trapped_value = calculate_trapped_value(
            wallet.balance,
            wallet.minimum_balance,
            wallet.status
        )

        stranded_data.append(
            {
                "wallet": wallet,
                "original_stranded": (
                    recoverable_surplus
                ),
                "recovered_amount": (
                    recovered_amount
                ),
                "remaining_recoverable": (
                    remaining_recoverable
                ),
                "trapped_value": trapped_value,
            }
        )

        total_recoverable_surplus += (
            recoverable_surplus
        )

        total_recovered += (
            recovered_amount
        )

        total_remaining += (
            remaining_recoverable
        )

        total_trapped += (
            trapped_value
        )

    return render_template(
        "wallets/stranded.html",
        stranded_data=stranded_data,
        total_original_stranded=(
            total_recoverable_surplus
        ),
        total_recovered=total_recovered,
        total_remaining=total_remaining,
        total_trapped=total_trapped
    )