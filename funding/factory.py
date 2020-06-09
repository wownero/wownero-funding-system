# -*- coding: utf-8 -*-
import settings
from flask import Flask
from flask_caching import Cache
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
import redis

app = None
cache = None
db = None
bcrypt = None


def _setup_cache(app: Flask):
    global cache

    cache_config = {
        "CACHE_TYPE": "redis",
        "CACHE_DEFAULT_TIMEOUT": 60,
        "CACHE_KEY_PREFIX": "wow_cache_",
        "CACHE_REDIS_PORT": settings.REDIS_PORT
    }

    if settings.REDIS_PASSWD:
        cache_config["CACHE_REDIS_PASSWORD"] = settings.REDIS_PASSWD

    app.config.from_mapping(cache_config)
    cache = Cache(app)


def _setup_session(app: Flask):
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_COOKIE_NAME'] = 'bar'
    app.config['SESSION_REDIS'] = redis.from_url(settings.REDIS_URI)
    Session(app)  # defaults to timedelta(days=31)


def _setup_db(app: Flask):
    global db

    DB_URL = 'postgresql+psycopg2://{user}:{pw}@{url}/{db}'.format(
        user=settings.PSQL_USER,
        pw=settings.PSQL_PASS,
        url=settings.PSQL_HOST,
        db=settings.PSQL_DB)
    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
    db = SQLAlchemy(app)

    import funding.orm

    with app.app_context():
        db.create_all()
        db.session.commit()


def create_app():
    global app
    global db
    global cache
    global bcrypt

    app = Flask(import_name=__name__,
                static_folder='static',
                template_folder='templates')
    app.config.from_object(settings)
    app.config['PERMANENT_SESSION_LIFETIME'] = 2678400
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 30
    app.secret_key = settings.SECRET

    _setup_cache(app)
    _setup_session(app)
    _setup_db(app)

    # flask-login
    from flask_login import LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    from flask_bcrypt import Bcrypt
    bcrypt = Bcrypt(app)

    @login_manager.user_loader
    def load_user(_id):
        from funding.orm.orm import User
        return User.query.get(int(_id))

    # import routes
    from funding import routes
    from funding import api
    from funding.bin import utils_request

    app.app_context().push()
    return app
