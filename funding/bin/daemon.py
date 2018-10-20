import settings
import requests
from requests.auth import HTTPDigestAuth

from funding.orm.orm import User


class Daemon:
    def __init__(self):
        self.url = settings.RPC_LOCATION
        self.username = settings.RPC_USERNAME
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
        daemon = Daemon()

        account = daemon.get_accounts(proposal.id)
        if not account:
            raise Exception('wallet error; pid not found found')
        index = account['account_index']

        address = daemon.get_address(index, proposal_id=proposal.id)
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
    
    def get_transfers_out(self, proposal):
        daemon = Daemon()

        account = daemon.get_accounts(proposal.id)
        if not account:
            raise Exception('wallet error; pid not found found')
        index = account['account_index']

        address = daemon.get_address(index, proposal_id=proposal.id)
        if not address:
            print('Could not fetch transfers_in for proposal id %d' % proposal.id)
            return {'sum': [], 'txs': []}

        data = {
            "method": "get_transfers",
            "params": {"pool": True, "out": True, "account_index": index},
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
        if self.username:
            if self.password:
                r = requests.post(self.url, auth=HTTPDigestAuth(settings.RPC_USERNAME, settings.RPC_PASSWORD), json=data, headers=self.headers)
        else:
            r = requests.post(self.url, json=data, headers=self.headers)
        r.raise_for_status()
        return r.json()