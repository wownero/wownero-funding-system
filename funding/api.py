import re

import requests
from flask import jsonify, send_from_directory, Response
from flask_yoloapi import endpoint, parameter

from funding.bin.utils import get_ip
from funding.bin.qr import QrCodeGenerator
from funding.factory import app, cache
from funding.orm import Proposal


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
    parameter('amount', type=int, location='args', required=True)
)
def api_coin_usd(amount):
    from funding.bin.utils import Summary, coin_to_usd
    prices = Summary.fetch_prices()
    return jsonify(usd=coin_to_usd(amt=amount, btc_per_coin=prices['coin-btc'], usd_per_btc=prices['btc-usd']))


@app.route('/api/1/qr')
@endpoint.api(
    parameter('address', type=str, location='args', required=True)
)
def api_qr_generate(address):
    """
    Generate a QR image. Subject to IP throttling.
    :param address: valid receiving address
    :return:
    """
    from funding.factory import cache

    qr = QrCodeGenerator()
    if not qr.exists(address):
        # create a new QR code
        ip = get_ip()
        cache_key = 'qr_ip_%s' % ip
        hit = cache.get(cache_key)

        if hit and ip not in ['127.0.0.1', 'localhost']:
            return Response('Wait a bit before generating a new QR', 403)

        throttling_seconds = 3
        cache.set(cache_key, {'wow': 'kek'}, throttling_seconds)

        created = qr.create(address)
        if not created:
            raise Exception('Could not create QR code')

    return send_from_directory('static/qr', '%s.png' % address)


@app.route('/api/1/wowlite')
@endpoint.api(
    parameter('version', type=str, location='args', required=True)
)
@cache.cached(timeout=600 * 6, make_cache_key=lambda version: f"api_wowlight_version_check_{version}")
def api_wowlight_version_check(version: str) -> bool:
    """
    Checks incoming wow-lite wallet version, returns False when the version is too old and needs to be upgraded.
    :param version:
    :return: bool
    """
    url = "https://raw.githubusercontent.com/wownero/wow-lite-wallet/master/src/renderer/components/Landing/LandingPage.vue"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla 5.0"})
        resp.raise_for_status()
        content = resp.content.decode()
    except:
        return True  # default to true

    # parse latest version
    current = next(re.finditer(r"wowlite\?version=(\d+.\d+.\d+)", content), None)
    if not current:
        return False

    return version == current.group(1)


@app.route('/api/1/wow/supply')
@endpoint.api()
def api_wow_supply():
    from funding.factory import cache
    cache_key = 'wow_supply'
    hit = cache.get(cache_key)
    if hit:
        return float(hit.get('data', -1))

    try:
        resp = requests.get('http://explorer.wowne.ro/api/emission', headers={'User-Agent': 'WFS'})
        resp.raise_for_status()
        blob = resp.json()
        assert 'data' in blob
        assert 'coinbase' in blob['data']
    except:
        return Exception('error fetching circulating supply')

    supply = blob['data'].get('coinbase') / 100000000000
    cache.set(cache_key, {'data': supply}, 120)
    return supply
