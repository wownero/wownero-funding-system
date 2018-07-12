from datetime import datetime
from flask import request, redirect, Response, abort, render_template, url_for, flash, make_response, send_from_directory, jsonify
from flask.ext.login import login_user , logout_user , current_user , login_required, current_user
from flask_yoloapi import endpoint, parameter

import settings
from wowfunding.factory import app, db_session
from wowfunding.orm.orm import Proposal, User


@app.route('/api/1/proposals')
@endpoint.api(
    parameter('status', type=int, location='args', default=1),
    parameter('cat', type=str, location='args'),
    parameter('limit', type=int, location='args', default=20),
    parameter('offset', type=int, location='args', default=0)
)
def api_proposals_get(status, cat, limit, offset):
    try:
        proposals = Proposal.find_by_args(status=status, cat=cat, limit=limit, offset=offset)
    except Exception as ex:
        print(ex)
        return 'error', 500

    return [p.json for p in proposals]


@app.route('/api/1/convert/wow-usd')
@endpoint.api(
    parameter('wow', type=int, location='args', required=True)
)
def api_wow_usd(wow):
    from wowfunding.bin.utils import Summary, wow_to_usd
    prices = Summary.fetch_prices()
    return jsonify(usd=wow_to_usd(wows=wow, btc_per_wow=prices['wow-btc'], usd_per_btc=prices['btc-usd']))
