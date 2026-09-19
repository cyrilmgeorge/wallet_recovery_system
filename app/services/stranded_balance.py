from decimal import Decimal


def calculate_stranded_balance(
    balance,
    minimum_balance
):
    """
    Calculate recoverable surplus above the required
    minimum balance.
    """

    balance = Decimal(balance)
    minimum_balance = Decimal(minimum_balance)

    if balance <= minimum_balance:
        return Decimal("0.00")

    return balance - minimum_balance


def calculate_recoverable_surplus(
    balance,
    minimum_balance
):
    """
    Calculate the surplus currently available above
    the wallet's required minimum.
    """

    return calculate_stranded_balance(
        balance,
        minimum_balance
    )


def calculate_remaining_recoverable_balance(
    balance,
    minimum_balance
):
    """
    Calculate the current surplus that can still be
    recovered.
    """

    return calculate_recoverable_surplus(
        balance,
        minimum_balance
    )


def calculate_trapped_value(
    balance,
    minimum_balance,
    wallet_status
):
    """
    Calculate value considered trapped when the wallet
    is in an exit-requested state.

    This is a project-level simulation rule.
    """

    balance = Decimal(balance)

    if wallet_status != "exit_requested":
        return Decimal("0.00")

    if balance <= Decimal("0.00"):
        return Decimal("0.00")

    return balance