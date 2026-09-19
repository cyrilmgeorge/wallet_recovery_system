import pytest

from app import create_app
from app.extensions import db
from app.models import (
    RecoveryOption,
    RecoveryTransaction,
    User,
    Wallet,
    WalletTransaction,
)
from app.services.recovery import seed_recovery_options
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret-key",
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()

        seed_recovery_options()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def create_user(app):

    def _create_user(
        username,
        email,
        password
    ):

        with app.app_context():

            user = User(
                username=username,
                email=email,
                password_hash=(
                    generate_password_hash(password)
                ),
            )

            db.session.add(user)
            db.session.commit()

            return user.id

    return _create_user


def login(
    client,
    email,
    password
):
    return client.post(
        "/auth/login",
        data={
            "email": email,
            "password": password,
        },
        follow_redirects=True,
    )


def test_user_can_create_and_view_own_wallet(
    client,
    create_user,
    app
):

    create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    login(
        client,
        "user1@example.com",
        "Password123",
    )

    response = client.post(
        "/wallets/add",
        data={
            "name": "User 1 Wallet",
            "provider": "Test Provider",
            "balance": "100.00",
            "minimum_balance": "60.00",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"User 1 Wallet" in response.data


def test_user_cannot_see_another_users_wallet(
    client,
    create_user,
    app
):

    user1_id = create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    create_user(
        "user2",
        "user2@example.com",
        "Password456",
    )

    with app.app_context():

        wallet = Wallet(
            name="User 1 Private Wallet",
            provider="Test Provider",
            balance=100.00,
            minimum_balance=60.00,
            status="active",
            user_id=user1_id,
        )

        db.session.add(wallet)
        db.session.commit()

        wallet_id = wallet.id

    login(
        client,
        "user2@example.com",
        "Password456",
    )

    response = client.get(
        f"/recovery/request/{wallet_id}",
        follow_redirects=False,
    )

    assert response.status_code == 404


def test_user_wallet_list_is_isolated(
    client,
    create_user,
    app
):

    user1_id = create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    user2_id = create_user(
        "user2",
        "user2@example.com",
        "Password456",
    )

    with app.app_context():

        user1_wallet = Wallet(
            name="User 1 Wallet",
            provider="Provider A",
            balance=100.00,
            minimum_balance=60.00,
            status="active",
            user_id=user1_id,
        )

        user2_wallet = Wallet(
            name="User 2 Wallet",
            provider="Provider B",
            balance=200.00,
            minimum_balance=150.00,
            status="active",
            user_id=user2_id,
        )

        db.session.add_all(
            [
                user1_wallet,
                user2_wallet,
            ]
        )

        db.session.commit()

    login(
        client,
        "user1@example.com",
        "Password123",
    )

    response = client.get("/wallets/")

    assert response.status_code == 200
    assert b"User 1 Wallet" in response.data
    assert b"User 2 Wallet" not in response.data


def test_stranded_balance_is_isolated(
    client,
    create_user,
    app
):

    user1_id = create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    user2_id = create_user(
        "user2",
        "user2@example.com",
        "Password456",
    )

    with app.app_context():

        user1_wallet = Wallet(
            name="User 1 Wallet",
            provider="Provider A",
            balance=100.00,
            minimum_balance=60.00,
            status="active",
            user_id=user1_id,
        )

        user2_wallet = Wallet(
            name="User 2 Wallet",
            provider="Provider B",
            balance=200.00,
            minimum_balance=150.00,
            status="active",
            user_id=user2_id,
        )

        db.session.add_all(
            [
                user1_wallet,
                user2_wallet,
            ]
        )

        db.session.commit()

    login(
        client,
        "user1@example.com",
        "Password123",
    )

    response = client.get(
        "/wallets/stranded"
    )

    assert response.status_code == 200
    assert b"User 1 Wallet" in response.data
    assert b"User 2 Wallet" not in response.data


def test_recovery_transactions_are_isolated(
    client,
    create_user,
    app
):

    user1_id = create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    user2_id = create_user(
        "user2",
        "user2@example.com",
        "Password456",
    )

    with app.app_context():

        user1_wallet = Wallet(
            name="User 1 Wallet",
            provider="Provider A",
            balance=100.00,
            minimum_balance=60.00,
            status="active",
            user_id=user1_id,
        )

        user2_wallet = Wallet(
            name="User 2 Wallet",
            provider="Provider B",
            balance=200.00,
            minimum_balance=150.00,
            status="active",
            user_id=user2_id,
        )

        db.session.add_all(
            [
                user1_wallet,
                user2_wallet,
            ]
        )

        db.session.flush()

        option = RecoveryOption(
            name="Test Reward",
            description="Test recovery option",
            is_active=True,
        )

        db.session.add(option)
        db.session.flush()

        user1_transaction = RecoveryTransaction(
            amount=10.00,
            status="completed",
            recovery_type="surplus",
            reference_code="REC-USER1-001",
            user_id=user1_id,
            wallet_id=user1_wallet.id,
            recovery_option_id=option.id,
        )

        user2_transaction = RecoveryTransaction(
            amount=20.00,
            status="completed",
            recovery_type="surplus",
            reference_code="REC-USER2-001",
            user_id=user2_id,
            wallet_id=user2_wallet.id,
            recovery_option_id=option.id,
        )

        db.session.add_all(
            [
                user1_transaction,
                user2_transaction,
            ]
        )

        db.session.commit()

    login(
        client,
        "user1@example.com",
        "Password123",
    )

    response = client.get(
        "/recovery/transactions"
    )

    assert response.status_code == 200
    assert b"REC-USER1-001" in response.data
    assert b"REC-USER2-001" not in response.data


def test_user_cannot_recover_from_another_users_wallet(
    client,
    create_user,
    app
):

    user1_id = create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    create_user(
        "user2",
        "user2@example.com",
        "Password456",
    )

    with app.app_context():

        wallet = Wallet(
            name="Private Wallet",
            provider="Provider A",
            balance=100.00,
            minimum_balance=60.00,
            status="active",
            user_id=user1_id,
        )

        db.session.add(wallet)
        db.session.commit()

        wallet_id = wallet.id

    login(
        client,
        "user2@example.com",
        "Password456",
    )

    response = client.get(
        f"/recovery/request/{wallet_id}",
        follow_redirects=False,
    )

    assert response.status_code == 404


def test_wallet_creation_records_initial_balance_transaction(
    client,
    create_user,
    app
):

    create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    login(
        client,
        "user1@example.com",
        "Password123",
    )

    response = client.post(
        "/wallets/add",
        data={
            "name": "Accounting Wallet",
            "provider": "Test Provider",
            "balance": "150.00",
            "minimum_balance": "100.00",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        wallet = Wallet.query.filter_by(
            name="Accounting Wallet"
        ).first()

        assert wallet is not None
        assert wallet.balance == 150
        assert wallet.status == "active"

        transactions = WalletTransaction.query.filter_by(
            wallet_id=wallet.id
        ).all()

        assert len(transactions) == 1

        transaction = transactions[0]

        assert transaction.transaction_type == (
            "initial_balance"
        )
        assert transaction.amount == 150
        assert transaction.balance_after == 150


def test_add_money_updates_wallet_balance_and_records_deposit(
    client,
    create_user,
    app
):

    create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    login(
        client,
        "user1@example.com",
        "Password123",
    )

    create_response = client.post(
        "/wallets/add",
        data={
            "name": "Deposit Wallet",
            "provider": "Test Provider",
            "balance": "100.00",
            "minimum_balance": "60.00",
        },
        follow_redirects=True,
    )

    assert create_response.status_code == 200

    with app.app_context():

        wallet = Wallet.query.filter_by(
            name="Deposit Wallet"
        ).first()

        assert wallet is not None
        assert wallet.status == "active"

        wallet_id = wallet.id

    deposit_response = client.post(
        f"/wallets/{wallet_id}/add-money",
        data={
            "amount": "50.00",
            "description": "Test deposit",
        },
        follow_redirects=True,
    )

    assert deposit_response.status_code == 200
    assert b"Money added successfully." in deposit_response.data

    with app.app_context():

        wallet = db.session.get(
            Wallet,
            wallet_id
        )

        assert wallet is not None
        assert wallet.status == "active"
        assert wallet.balance == 150

        transactions = (
            WalletTransaction.query
            .filter_by(wallet_id=wallet_id)
            .order_by(WalletTransaction.id)
            .all()
        )

        assert len(transactions) == 2

        initial_transaction = transactions[0]
        deposit_transaction = transactions[1]

        assert initial_transaction.transaction_type == (
            "initial_balance"
        )
        assert initial_transaction.amount == 100
        assert initial_transaction.balance_after == 100

        assert deposit_transaction.transaction_type == (
            "deposit"
        )
        assert deposit_transaction.amount == 50
        assert deposit_transaction.balance_after == 150
        assert deposit_transaction.description == (
            "Test deposit"
        )


def test_user_cannot_add_money_to_another_users_wallet(
    client,
    create_user,
    app
):

    user1_id = create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    create_user(
        "user2",
        "user2@example.com",
        "Password456",
    )

    with app.app_context():

        wallet = Wallet(
            name="User 1 Wallet",
            provider="Provider A",
            balance=100.00,
            minimum_balance=60.00,
            status="active",
            user_id=user1_id,
        )

        db.session.add(wallet)
        db.session.commit()

        wallet_id = wallet.id

    login(
        client,
        "user2@example.com",
        "Password456",
    )

    response = client.post(
        f"/wallets/{wallet_id}/add-money",
        data={
            "amount": "50.00",
            "description": "Unauthorized deposit",
        },
        follow_redirects=False,
    )

    assert response.status_code == 404

    with app.app_context():

        wallet = db.session.get(
            Wallet,
            wallet_id
        )

        assert wallet.balance == 100

        transactions = WalletTransaction.query.filter_by(
            wallet_id=wallet_id
        ).all()

        assert len(transactions) == 0


def test_wallet_transaction_history_is_user_isolated(
    client,
    create_user,
    app
):

    user1_id = create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    user2_id = create_user(
        "user2",
        "user2@example.com",
        "Password456",
    )

    with app.app_context():

        user1_wallet = Wallet(
            name="User 1 Wallet",
            provider="Provider A",
            balance=150.00,
            minimum_balance=100.00,
            status="active",
            user_id=user1_id,
        )

        user2_wallet = Wallet(
            name="User 2 Wallet",
            provider="Provider B",
            balance=250.00,
            minimum_balance=150.00,
            status="active",
            user_id=user2_id,
        )

        db.session.add_all(
            [
                user1_wallet,
                user2_wallet,
            ]
        )

        db.session.flush()

        user1_transaction = WalletTransaction(
            wallet_id=user1_wallet.id,
            user_id=user1_id,
            transaction_type="deposit",
            amount=50.00,
            balance_after=150.00,
            description="User 1 deposit",
        )

        user2_transaction = WalletTransaction(
            wallet_id=user2_wallet.id,
            user_id=user2_id,
            transaction_type="deposit",
            amount=100.00,
            balance_after=250.00,
            description="User 2 deposit",
        )

        db.session.add_all(
            [
                user1_transaction,
                user2_transaction,
            ]
        )

        db.session.commit()

        user1_wallet_id = user1_wallet.id

    login(
        client,
        "user1@example.com",
        "Password123",
    )

    response = client.get(
        f"/wallets/{user1_wallet_id}/transactions"
    )

    assert response.status_code == 200
    assert b"User 1 deposit" in response.data
    assert b"User 2 deposit" not in response.data


def test_active_wallet_can_request_exit(
    client,
    create_user,
    app
):

    create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    login(
        client,
        "user1@example.com",
        "Password123",
    )

    create_response = client.post(
        "/wallets/add",
        data={
            "name": "Exit Wallet",
            "provider": "Provider A",
            "balance": "150.00",
            "minimum_balance": "100.00",
        },
        follow_redirects=True,
    )

    assert create_response.status_code == 200

    with app.app_context():

        wallet = Wallet.query.filter_by(
            name="Exit Wallet"
        ).first()

        assert wallet is not None
        wallet_id = wallet.id
        assert wallet.status == "active"

    response = client.post(
        f"/wallets/{wallet_id}/toggle-exit",
        data={
            "submit": "Change Wallet Status",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        wallet = db.session.get(
            Wallet,
            wallet_id
        )

        assert wallet.status == "exit_requested"
        assert wallet.balance == 150


def test_exit_requested_wallet_can_be_resumed(
    client,
    create_user,
    app
):

    user_id = create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    with app.app_context():

        wallet = Wallet(
            name="Resume Wallet",
            provider="Provider A",
            balance=120.00,
            minimum_balance=80.00,
            status="exit_requested",
            user_id=user_id,
        )

        db.session.add(wallet)
        db.session.commit()

        wallet_id = wallet.id

    login(
        client,
        "user1@example.com",
        "Password123",
    )

    response = client.post(
        f"/wallets/{wallet_id}/toggle-exit",
        data={
            "submit": "Change Wallet Status",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        wallet = db.session.get(
            Wallet,
            wallet_id
        )

        assert wallet.status == "active"
        assert wallet.balance == 120


def test_user_cannot_request_exit_on_another_users_wallet(
    client,
    create_user,
    app
):

    user1_id = create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    create_user(
        "user2",
        "user2@example.com",
        "Password456",
    )

    with app.app_context():

        wallet = Wallet(
            name="Private Exit Wallet",
            provider="Provider A",
            balance=150.00,
            minimum_balance=100.00,
            status="active",
            user_id=user1_id,
        )

        db.session.add(wallet)
        db.session.commit()

        wallet_id = wallet.id

    login(
        client,
        "user2@example.com",
        "Password456",
    )

    response = client.post(
        f"/wallets/{wallet_id}/toggle-exit",
        data={
            "submit": "Change Wallet Status",
        },
        follow_redirects=False,
    )

    assert response.status_code == 404

    with app.app_context():

        wallet = db.session.get(
            Wallet,
            wallet_id
        )

        assert wallet.status == "active"
        assert wallet.balance == 150


def test_exit_requested_wallet_can_retrieve_trapped_value(
    client,
    create_user,
    app
):

    user_id = create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    with app.app_context():

        wallet = Wallet(
            name="Trapped Value Wallet",
            provider="Provider A",
            balance=100.00,
            minimum_balance=100.00,
            status="exit_requested",
            user_id=user_id,
        )

        db.session.add(wallet)
        db.session.commit()

        wallet_id = wallet.id

    login(
        client,
        "user1@example.com",
        "Password123",
    )

    response = client.post(
        f"/recovery/exit/{wallet_id}",
        data={
            "submit": "Retrieve Trapped Value",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert (
        b"Trapped value was retrieved successfully."
        in response.data
    )

    with app.app_context():

        wallet = db.session.get(
            Wallet,
            wallet_id
        )

        assert wallet is not None
        assert wallet.balance == 0
        assert wallet.status == "exited"

        wallet_transactions = (
            WalletTransaction.query
            .filter_by(wallet_id=wallet_id)
            .order_by(WalletTransaction.id)
            .all()
        )

        assert len(wallet_transactions) == 1

        wallet_transaction = wallet_transactions[0]

        assert wallet_transaction.transaction_type == (
            "exit_recovery"
        )
        assert wallet_transaction.amount == 100
        assert wallet_transaction.balance_after == 0

        recovery_transaction = (
            RecoveryTransaction.query
            .filter_by(
                wallet_id=wallet_id,
                user_id=user_id,
                recovery_type="exit",
            )
            .first()
        )

        assert recovery_transaction is not None
        assert recovery_transaction.amount == 100
        assert recovery_transaction.status == "completed"
        assert recovery_transaction.reference_code.startswith(
            "EXIT-"
        )


def test_user_cannot_retrieve_trapped_value_from_another_users_wallet(
    client,
    create_user,
    app
):

    user1_id = create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    create_user(
        "user2",
        "user2@example.com",
        "Password456",
    )

    with app.app_context():

        wallet = Wallet(
            name="Private Trapped Wallet",
            provider="Provider A",
            balance=125.00,
            minimum_balance=100.00,
            status="exit_requested",
            user_id=user1_id,
        )

        db.session.add(wallet)
        db.session.commit()

        wallet_id = wallet.id

    login(
        client,
        "user2@example.com",
        "Password456",
    )

    response = client.post(
        f"/recovery/exit/{wallet_id}",
        data={
            "submit": "Retrieve Trapped Value",
        },
        follow_redirects=False,
    )

    assert response.status_code == 404

    with app.app_context():

        wallet = db.session.get(
            Wallet,
            wallet_id
        )

        assert wallet.status == "exit_requested"
        assert wallet.balance == 125

        recovery_transaction = (
            RecoveryTransaction.query
            .filter_by(wallet_id=wallet_id)
            .first()
        )

        assert recovery_transaction is None

        wallet_transactions = WalletTransaction.query.filter_by(
            wallet_id=wallet_id
        ).all()

        assert len(wallet_transactions) == 0


def test_exited_wallet_cannot_be_resumed(
    client,
    create_user,
    app
):

    user_id = create_user(
        "user1",
        "user1@example.com",
        "Password123",
    )

    with app.app_context():

        wallet = Wallet(
            name="Closed Wallet",
            provider="Provider A",
            balance=0.00,
            minimum_balance=100.00,
            status="exited",
            user_id=user_id,
        )

        db.session.add(wallet)
        db.session.commit()

        wallet_id = wallet.id

    login(
        client,
        "user1@example.com",
        "Password123",
    )

    response = client.post(
        f"/wallets/{wallet_id}/toggle-exit",
        data={
            "submit": "Change Wallet Status",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():

        wallet = db.session.get(
            Wallet,
            wallet_id
        )

        assert wallet.status == "exited"
        assert wallet.balance == 0

        assert b"cannot be resumed" in response.data.lower()