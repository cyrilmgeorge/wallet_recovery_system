from flask import Blueprint


wallets = Blueprint(
    "wallets",
    __name__,
    url_prefix="/wallets"
)


from . import routes