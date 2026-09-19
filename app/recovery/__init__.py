from flask import Blueprint


recovery = Blueprint(
    "recovery",
    __name__,
    url_prefix="/recovery"
)


from . import routes