from flask_login import login_required
from funding.factory import app, db


@app.route('/admin/index')
@login_required
def admin_home():
    return 'yep'
