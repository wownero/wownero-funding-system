from datetime import datetime, date

import requests
from flask import request

import settings
from funding.factory import cache


def json_encoder(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


class Summary:
    @staticmethod
    @cache.cached(timeout=600, key_prefix="fetch_prices")
    def fetch_prices():
        return {
            'coin-btc': coin_btc_value(),
            'btc-usd': price_cmc_btc_usd()
        }

    @staticmethod
    @cache.cached(timeout=600, key_prefix="funding_stats")
    def fetch_stats():
        from funding.factory import db
        from funding.orm import Proposal, User

        data = {}
        categories = settings.FUNDING_CATEGORIES
        statuses = settings.FUNDING_STATUSES.keys()

        for cat in categories:
            q = db.session.query(Proposal)
            q = q.filter(Proposal.category == cat)
            res = q.count()
            data.setdefault('cats', {})
            data['cats'][cat] = res

        for status in statuses:
            q = db.session.query(Proposal)
            q = q.filter(Proposal.status == status)
            res = q.count()
            data.setdefault('statuses', {})
            data['statuses'][status] = res

        data.setdefault('users', {})
        data['users']['count'] = db.session.query(User.id).count()
        return data


def price_cmc_btc_usd():
    headers = {'User-Agent': 'Mozilla/5.0 (Android 4.4; Mobile; rv:41.0) Gecko/41.0 Firefox/41.0'}
    try:
        r = requests.get('https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd', headers=headers)
        r.raise_for_status()
        data = r.json()
        btc = next(c for c in data if c['symbol'] == 'btc')
        return btc['current_price']
    except:
        return


def coin_btc_value():
    headers = {'User-Agent': 'Mozilla/5.0 (Android 4.4; Mobile; rv:41.0) Gecko/41.0 Firefox/41.0'}
    try:
        r = requests.get('https://tradeogre.com/api/v1/ticker/BTC-WOW', headers=headers)
        r.raise_for_status()
        return float(r.json().get('high'))
    except:
        return


def coin_to_usd(amt: float, usd_per_btc: float, btc_per_coin: float):
    try:
        return round(usd_per_btc / (1.0 / (amt * btc_per_coin)), 2)
    except:
        pass


def get_ip():
    return request.headers.get('X-Forwarded-For') or request.remote_addr
