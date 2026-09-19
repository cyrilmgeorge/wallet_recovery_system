from decimal import Decimal

from flask import redirect, render_template, url_for
from flask_login import current_user, login_required

from . import main
from ..models import RecoveryTransaction, Wallet
from ..services.recovery import get_recovered_amount_for_wallet
from ..services.stranded_balance import (
    calculate_remaining_recoverable_balance,
    calculate_stranded_balance,
)


@main.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    return render_template("main/home.html")


@main.route("/dashboard")
@login_required
def dashboard():

    user_wallets = Wallet.query.filter_by(
        user_id=current_user.id
    ).all()

    total_current_balance = Decimal("0.00")
    total_recoverable_surplus = Decimal("0.00")
    total_recovered = Decimal("0.00")
    total_remaining_recoverable = Decimal("0.00")

    for wallet in user_wallets:

        total_current_balance += Decimal(
            wallet.balance
        )

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

        total_recoverable_surplus += (
            recoverable_surplus
        )

        total_recovered += recovered_amount

        total_remaining_recoverable += (
            remaining_recoverable
        )

    transaction_count = RecoveryTransaction.query.filter_by(
        user_id=current_user.id
    ).count()

    return render_template(
        "main/dashboard.html",
        total_wallets=len(user_wallets),
        total_current_balance=total_current_balance,
        total_original_stranded=total_recoverable_surplus,
        total_recovered=total_recovered,
        total_remaining_recoverable=(
            total_remaining_recoverable
        ),
        transaction_count=transaction_count
    )


@main.route("/profile")
@login_required
def profile():
    return render_template(
        "profile/profile.html",
        user=current_user
    )