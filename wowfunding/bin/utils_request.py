from datetime import datetime
from flask import session, g

import settings
from wowfunding.factory import app, db_session, summary_data
from wowfunding.orm.orm import Proposal, User


@app.context_processor
def template_vars():
    global summary_data
    return dict(summary_data=summary_data[1])


def fetch_summary():
    global summary_data
    if summary_data:
        if (datetime.now() - summary_data[0]).total_seconds() <= 120:
            return

    data = {}
    categories = settings.FUNDING_CATEGORIES
    statuses = [0, 1, 2]

    for cat in categories:
        q = db_session.query(Proposal)
        q = q.filter(Proposal.category == cat)
        res = q.count()
        data.setdefault('cats', {})
        data['cats'][cat] = res

    for status in statuses:
        q = db_session.query(Proposal)
        q = q.filter(Proposal.status == status)
        res = q.count()
        data.setdefault('statuses', {})
        data['statuses'][status] = res

    data.setdefault('users', {})
    data['users']['count'] = db_session.query(User.id).count()
    summary_data = [datetime.now(), data]


@app.before_request
def before_request():
    fetch_summary()


@app.after_request
def after_request(res):
    res.headers.add('Accept-Ranges', 'bytes')
    if settings.DEBUG:
        res.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        res.headers['Pragma'] = 'no-cache'
        res.headers['Expires'] = '0'
        res.headers['Cache-Control'] = 'public, max-age=0'
    return res


@app.teardown_appcontext
def shutdown_session(**kwargs):
    db_session.remove()


@app.errorhandler(404)
def error(err):
    return 'Error', 404
