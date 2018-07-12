from datetime import datetime, date

import requests
from flask import g
from flask.json import JSONEncoder

import settings


def json_encoder(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))


class Summary:
    @staticmethod
    def fetch_prices():
        if hasattr(g, 'wowfunding_prices') and g.wow_prices:
            return g.wow_prices

        from wowfunding.factory import cache
        cache_key = 'wowfunding_prices'
        data = cache.get(cache_key)
        if data:
            return data
        data = {
            'wow-btc': price_tradeogre_wow_btc(),
            'btc-usd': price_cmc_btc_usd()
        }

        cache.set(cache_key, data=data, expiry=7200)
        g.wow_prices = data
        return data

    @staticmethod
    def fetch_stats(purge=False):
        from wowfunding.factory import db_session
        from wowfunding.orm.orm import Proposal, User, Comment
        from wowfunding.factory import cache
        cache_key = 'wowfunding_stats'
        data = cache.get(cache_key)
        if data and not purge:
            return data

        categories = settings.FUNDING_CATEGORIES
        statuses = settings.FUNDING_STATUSES.keys()

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
        cache.set(cache_key, data=data, expiry=300)
        return data


def price_cmc_btc_usd():
    headers = {'User-Agent': 'Mozilla/5.0 (Android 4.4; Mobile; rv:41.0) Gecko/41.0 Firefox/41.0'}
    try:
        r = requests.get('https://api.coinmarketcap.com/v2/ticker/1/?convert=USD', headers=headers)
        r.raise_for_status()
        return r.json().get('data', {}).get('quotes', {}).get('USD', {}).get('price')
    except:
        return


def price_tradeogre_wow_btc():
    headers = {'User-Agent': 'Mozilla/5.0 (Android 4.4; Mobile; rv:41.0) Gecko/41.0 Firefox/41.0'}
    try:
        r = requests.get('https://tradeogre.com/api/v1/ticker/BTC-WOW', headers=headers)
        r.raise_for_status()
        return float(r.json().get('high'))
    except:
        return


def wow_to_usd(wows: float, usd_per_btc: float, btc_per_wow: float):
    try:
        return round(usd_per_btc / (1.0 / (wows * btc_per_wow)), 2)
    except:
        pass