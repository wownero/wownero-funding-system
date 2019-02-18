from datetime import datetime

import requests
from requests.auth import HTTPDigestAuth

import settings
from funding.orm.orm import User


class Daemon:
    def __init__(self, url=None, username=None, password=None):
        self.url = url
        self.username = username
        self.password = password

        if url is None:
            self.url = settings.RPC_LOCATION
        if username is None:
            self.username = settings.RPC_USERNAME
        if password is None:
            self.password = settings.RPC_PASSWORD

        self.headers = {"User-Agent": "Mozilla"}

    def create_address(self, account_index, label_name):
        data = {
            'method': 'create_address',
            'params': {'account_index': account_index, 'label': 'p_%s' % label_name},
            'jsonrpc': '2.0',
            'id': '0'
        }

        try:
            result = self._make_request(data)
            return result['result']
        except:
            return

    def create_account(self, pid):
        data = {
            'method': 'create_account',
            'params': {'label': 'p_%s' % pid},
            'jsonrpc': '2.0',
            'id': '0'
        }
        try:
            result = self._make_request(data)
            return result['result']
        except:
            return

    def get_accounts(self, proposal_id:int = None):
        data = {
            'method': 'get_accounts',
            'jsonrpc': '2.0',
            'id': '0'
        }
        try:
            result = self._make_request(data)
            result = result['result']

            if isinstance(proposal_id, int):
                account_user = [acc for acc in result.get('subaddress_accounts', []) if acc['label'] == 'p_%d' % proposal_id]
                if account_user:
                    return account_user[0]
                else:
                    return

            return result
        except Exception as ex:
            return

    def get_address(self, account_index: int, proposal_id: int = None):
        data = {
            'method': 'getaddress',
            'params': {'account_index': account_index},
            'jsonrpc': '2.0',
            'id': '0'
        }
        try:
            result = self._make_request(data)
            addresses = result['result']['addresses']

            if isinstance(proposal_id, int):
                address = [addy for addy in addresses if addy['label'] == 'p_%d' % proposal_id]
                if address:
                    return address[0]
                else:
                    return
            return addresses
        except:
            return

    def get_transfers_in(self, proposal):
        account = self.get_accounts(proposal.id)
        if not account and proposal.addr_donation:
            account = self.create_account(proposal.id)
            account = self.get_accounts(proposal.id)
        if not account:
            raise Exception('wallet error; pid not found found')
        index = account['account_index']

        address = self.get_address(index, proposal_id=proposal.id)
        if not address:
            print('Could not fetch transfers_in for proposal id %d' % proposal.id)
            return {'sum': [], 'txs': []}

        data = {
            "method": "get_transfers",
            "params": {"pool": True, "in": True, "account_index": index},
            "jsonrpc": "2.0",
            "id": "0",
        }

        data = self._make_request(data)
        data = data['result']
        data = data.get('in', []) + data.get('pool', [])

        # filter by current proposal
        txs = [tx for tx in data if tx.get('address') == address['address']]

        for d in txs:
            d['amount_human'] = float(d['amount'])/1e11

        return {
            'sum': sum([float(z['amount'])/1e11 for z in txs]),
            'txs': txs
        }

    def get_transfers_in_simple(self):
        data = {
            "method": "get_transfers",
            "params": {"pool": True, "in": True},
            "jsonrpc": "2.0",
            "id": "0",
        }

        data = self._make_request(data)
        data = data['result']
        data = data.get('in', []) + data.get('pool', [])

        for d in data:
            d['datetime'] = datetime.fromtimestamp(d['timestamp'])
            d['amount_human'] = float(d['amount'])/1e11

        # most recent tx first
        data = sorted(data, key=lambda k: k['datetime'], reverse=True)

        return {
            'sum': sum([float(z['amount'])/1e11 for z in data]),
            'txs': data
        }

    def get_transfers_out(self, proposal):
        account = self.get_accounts(proposal.id)
        if not account:
            raise Exception('wallet error; pid not found found')
        index = account['account_index']

        address = self.get_address(index, proposal_id=proposal.id)
        if not address:
            print('Could not fetch transfers_in for proposal id %d' % proposal.id)
            return {'sum': [], 'txs': []}

        data = {
            "method": "get_transfers",
            "params": {"pool": False, "out": True, "account_index": index},
            "jsonrpc": "2.0",
            "id": "0",
        }

        data = self._make_request(data)
        data = data['result']
        data = data.get('out', []) + data.get('pool', [])

        # filter by current proposal
        txs = [tx for tx in data if tx.get('address') == address['address']]

        for d in txs:
            d['amount_human'] = float(d['amount'])/1e11

        return {
            'sum': sum([float(z['amount'])/1e11 for z in txs]),
            'txs': txs
        }

    def _make_request(self, data):
        options = {'json': data, 'headers': self.headers}
        if self.username and self.password:
            options['auth'] = HTTPDigestAuth(settings.RPC_USERNAME, settings.RPC_PASSWORD)

        r = requests.post(self.url, **options)
        r.raise_for_status()
        return r.json()
