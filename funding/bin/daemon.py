import settings
import requests
from requests.auth import HTTPDigestAuth

class Daemon:
    def __init__(self):
        self.url = settings.RPC_LOCATION
        self.username = settings.RPC_USERNAME
        self.password = settings.RPC_PASSWORD
        self.headers = {"User-Agent": "Mozilla"}

    def create_address(self, label_name):
        data = {
            'method': 'create_address',
            'params': {'account_index': 0, 'label': label_name},
            'jsonrpc': '2.0',
            'id': '0'
        }
        return self._make_request(data)

    def create_account(self, pid):
        data = {
            'method': 'create_account',
            'params': {'label': '%s' % pid},
            'jsonrpc': '2.0',
            'id': '0'
        }
        return self._make_request(data)

    def get_address(self, index, proposal_id):
        data = {
            'method': 'getaddress',
            'params': {'account_index': proposal_id, 'address_index': '[0]'},
            'jsonrpc': '2.0',
            'id': '0'
        }
        try:
            result = self._make_request(data)
            return result['result']
        except:
            return

    def get_transfers_in(self, index, proposal_id):
        data = {
            "method":"get_transfers",
            "params": {"pool": True, "in": True, "account_index": proposal_id},
            "jsonrpc": "2.0",
            "id": "0",
        }
        data = self._make_request(data)
        data = data['result'].get('in', [])
        for d in data:
            d['amount_human'] = float(d['amount'])/1e12
        return {
            'sum': sum([float(z['amount'])/1e12 for z in data]),
            'txs': data
        }
    
    def get_transfers_out(self, index, proposal_id):
        data = {
            "method":"get_transfers",
            "params": {"pool": True, "out": True, "account_index": proposal_id},
            "jsonrpc": "2.0",
            "id": "0",
        }
        data = self._make_request(data)
        data = data['result'].get('out', [])
        for d in data:
            d['amount_human'] = float(d['amount'])/1e12
        return {
            'sum': sum([float(z['amount'])/1e12 for z in data]),
            'txs': data
        }

    def _make_request(self, data):
        if self.username:
            if self.password:
                r = requests.post(self.url, auth=HTTPDigestAuth(settings.RPC_USERNAME, settings.RPC_PASSWORD), json=data, headers=self.headers)
        else:
            r = requests.post(self.url, json=data, headers=self.headers)
        r.raise_for_status()
        return r.json()