from flask import Flask, render_template

from config import Config
from .extensions import db, login_manager


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_object(Config)

    if test_config is not None:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)

    from .auth import auth
    from .main import main
    from .wallets import wallets
    from .recovery import recovery

    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(wallets)
    app.register_blueprint(recovery)

    with app.app_context():
        from .models import (
            User,
            Wallet,
            RecoveryOption,
            RecoveryTransaction,
        )

        from .services.recovery import seed_recovery_options

        from .services.database_migration import (
            migrate_wallet_table,
            migrate_recovery_transaction_table,
            reconcile_existing_recovery_transactions,
        )

        db.create_all()

        migrate_wallet_table()

        migrate_recovery_transaction_table()

        reconcile_existing_recovery_transactions()

        seed_recovery_options()

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template(
            "errors/404.html"
        ), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template(
            "errors/403.html"
        ), 403

    return app


@login_manager.user_loader
def load_user(user_id):
    from .models import User

    return db.session.get(
        User,
        int(user_id)
    )