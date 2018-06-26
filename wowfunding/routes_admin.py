from flask.ext.login import login_required
from wowfunding.factory import app, db_session


@app.route('/admin/index')
@login_required
def admin_home():
    return 'yep'
