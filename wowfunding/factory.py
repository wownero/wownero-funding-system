# -*- coding: utf-8 -*-
import settings
from werkzeug.contrib.fixers import ProxyFix
from flask import Flask

app = None
sentry = None
cache = None
db_session = None
bcrypt = None
summary_data = []


def create_app():
    global app
    global db_session
    global sentry
    global cache
    global bcrypt

    from wowfunding.orm.connect import create_session
    db_session = create_session()

    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.config.from_object(settings)
    app.config['PERMANENT_SESSION_LIFETIME'] = 2678400
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 30
    app.secret_key = settings.SECRET

    # flask-login
    from flask.ext.login import LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    from flask.ext.bcrypt import Bcrypt
    bcrypt = Bcrypt(app)

    @login_manager.user_loader
    def load_user(_id):
        from wowfunding.orm.orm import User
        return User.query.get(int(_id))

    # session init
    from wowfunding.cache import JsonRedis, WowCache
    app.session_interface = JsonRedis(key_prefix=app.config['SESSION_PREFIX'], use_signer=False)
    cache = WowCache()

    # template vars
    @app.context_processor
    def _bootstrap_templating():
        from flask.ext.login import current_user
        return dict(logged_in=current_user.is_authenticated,
                    current_user=current_user)

    # import routes
    from wowfunding import routes
    from wowfunding import api
    from wowfunding.bin import utils_request

    # generate some statistics
    utils_request.fetch_summary()

    app.app_context().push()
    return app
