import settings
import requests


class WowneroDaemon:
    def __init__(self):
        self.url = settings.RPC_LOCATION
        self.headers = {"User-Agent": "Mozilla"}

    def create_address(self, label_name):
        data = {
            'method': 'create_address',
            'params': {'account_index': 0, 'label': label_name},
            'jsonrpc': '2.0',
            'id': '0'
        }
        return self._make_request(data)

    def get_address(self, index):
        data = {
            'method': 'get_address',
            'params': {'address_index': [index], 'account_index': 0},
            'jsonrpc': '2.0',
            'id': '0'
        }
        try:
            result = self._make_request(data)
            return next(z for z in result['result']['addresses'] if z['address_index'] == index)
        except:
            return

    def get_transfers_in(self, index):
        data = {
            "method":"get_transfers",
            "params": {"in": True, "account_index": 0, "subaddr_indices": [index]},
            "jsonrpc": "2.0",
            "id": "0",
        }
        data = self._make_request(data)
        data = data['result'].get('in', [])
        for d in data:
            d['amount_human'] = float(d['amount'])/1e11

        return {
            'sum': sum([float(z['amount'])/1e11 for z in data]),
            'txs': data
        }

    def _make_request(self, data):
        r = requests.post(self.url, json=data, headers=self.headers)
        r.raise_for_status()
        return r.json()
