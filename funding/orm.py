from datetime import datetime
import string
import random

import requests
from sqlalchemy.orm import relationship, backref
import sqlalchemy as sa
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import Float
from sqlalchemy_json import MutableJson

import settings
from funding.factory import db, cache

base = declarative_base(name="Model")


class User(db.Model):
    __tablename__ = "users"
    id = db.Column('user_id', db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, index=True)
    password = db.Column(db.String(60))
    email = db.Column(db.String(50), unique=True, index=True)
    registered_on = db.Column(db.DateTime)
    admin = db.Column(db.Boolean, default=False)
    proposals = relationship('Proposal', back_populates="user")
    comments = relationship("Comment", back_populates="user")
    uuid = db.Column(UUID(as_uuid=True), unique=True)

    def __init__(self, username, password, email, uuid=None):
        from funding.factory import bcrypt
        self.username = username
        if password:
            self.password = bcrypt.generate_password_hash(password).decode('utf8')
        self.uuid = uuid
        self.email = email
        self.registered_on = datetime.utcnow()

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_admin(self):
        return self.admin

    def get_id(self):
        return self.id

    def __repr__(self):
        return self.username

    @classmethod
    def add(cls, username, password=None, email=None, uuid=None):
        from funding.factory import db
        from funding.validation import val_username, val_email

        try:
            # validate incoming username/email
            val_username(username)
            if email:
                val_email(email)

            user = User(username=username, password=password, email=email, uuid=uuid)
            db.session.add(user)
            db.session.commit()
            db.session.flush()
            return user
        except Exception as ex:
            db.session.rollback()
            raise


class Proposal(db.Model):
    __tablename__ = "proposals"
    id = db.Column(db.Integer, primary_key=True)
    archived = db.Column(db.Boolean, default=False)
    headline = db.Column(db.VARCHAR, nullable=False)
    content = db.Column(db.VARCHAR, nullable=False)
    category = db.Column(db.VARCHAR, nullable=False)
    date_added = db.Column(db.TIMESTAMP, default=datetime.now)
    html = db.Column(db.VARCHAR)
    last_edited = db.Column(db.TIMESTAMP)

    # the FFS target
    funds_target = db.Column(db.Float, nullable=False)

    # the FFS progress (cached)
    funds_progress = db.Column(db.Float, nullable=False, default=0)

    # the FFS withdrawal amount (paid to the author)
    funds_withdrew = db.Column(db.Float, nullable=False, default=0)

    # the FFS receiving and withdrawal addresses
    addr_donation = db.Column(db.VARCHAR)
    addr_receiving = db.Column(db.VARCHAR)
    payment_id = db.Column(db.VARCHAR)

    # proposal status:
    # 0: disabled
    # 1: proposed
    # 2: funding required
    # 3: wip
    # 4: completed
    status = db.Column(db.INTEGER, default=1)

    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    user = relationship("User", back_populates="proposals")

    payouts = relationship("Payout", back_populates="proposal")
    comments = relationship("Comment", back_populates="proposal", lazy='select')

    def __init__(self, headline, content, category, user: User):
        if not headline or not content:
            raise Exception('faulty proposal')
        self.headline = headline
        self.content = content
        self.user_id = user.id
        if category not in settings.FUNDING_CATEGORIES:
            raise Exception('wrong category')
        self.category = category

    @property
    def json(self):
        return {
            'date_posted_epoch': self.date_added.strftime('%s'),
            'date_posted': self.date_added.strftime('%b %d %Y %H:%M:%S'),
            'headline': self.headline,
            'content_markdown': self.content,
            'category': self.category,
            'funds_target': self.funds_target,
            'funded_pct': self.funds_progress,
            'addr_donation': self.addr_donation,
            'status': self.status,
            'user': self.user.username,
            'id': self.id
        }

    @classmethod
    def find_by_id(cls, pid: int):
        from funding.factory import db
        q = cls.query
        q = q.filter(Proposal.id == pid)
        result = q.first()
        if not result:
            return
        return result

    @property
    def funds_target_usd(self):
        from funding.bin.utils import Summary, coin_to_usd
        prices = Summary.fetch_prices()
        if not prices:
            return
        return coin_to_usd(amt=self.funds_target, btc_per_coin=prices['coin-btc'], usd_per_btc=prices['btc-usd'])

    @property
    def comment_count(self):
        from funding.factory import db
        q = db.session.query(db.func.count(Comment.id))
        q = q.filter(Comment.proposal_id == self.id)
        return q.scalar()

    def get_comments(self):
        from funding.factory import db
        q = db.session.query(Comment)
        q = q.filter(Comment.proposal_id == self.id)
        q = q.filter(Comment.replied_to.is_(None))
        q = q.order_by(Comment.date_added.desc())
        comments = q.all()

        for c in comments:
            q = db.session.query(Comment)
            q = q.filter(Comment.proposal_id == self.id)
            q = q.filter(Comment.replied_to == c.id)
            _c = q.all()
            setattr(c, 'comments', _c)

        setattr(self, '_comments', comments)
        return self

    @property
    def spends(self):
        amount = sum([p.amount for p in self.payouts])
        pct = amount / 100 * self.balance['sum']
        return {"amount": amount, "pct": pct}

    @property
    @cache.cached(timeout=60, make_cache_key=lambda p: f"proposal_balance_{p.id}")
    def balance(self):
        """This property retrieves the current funding status
        of this proposal. It uses Redis cache to not spam the
        daemon too much. Returns a nice dictionary containing
        all relevant proposal funding info"""
        from funding.bin.utils import Summary, coin_to_usd
        from funding.factory import db
        rtn = {'sum': 0.0, 'txs': [], 'pct': 0.0, 'available': 0}

        if self.archived:
            return rtn

        try:
            r = requests.get(f'http://{settings.RPC_HOST}:{settings.RPC_PORT}/json_rpc', json={
                "jsonrpc": "2.0",
                "id": "0",
                "method": "get_payments",
                "params": {
                    "payment_id": self.payment_id
                }
            })
            r.raise_for_status()
            blob = r.json()

            assert 'result' in blob
            assert 'payments' in blob['result']
            assert isinstance(blob['result']['payments'], list)
        except Exception as ex:
            return rtn

        txs = blob['result']['payments']
        for tx in txs:
            tx['amount_human'] = float(tx['amount'])/1e11
            tx['txid'] = tx['tx_hash']
            tx['type'] = 'in'

        data = {
            'sum': sum([float(z['amount']) / 1e11 for z in txs]),
            'txs': txs
        }

        if not isinstance(data, dict):
            print('error; get_transfers_in; %d' % self.id)
            return rtn

        prices = Summary.fetch_prices()
        for tx in data['txs']:
            if prices:
                tx['amount_usd'] = coin_to_usd(amt=tx['amount_human'], btc_per_coin=prices['coin-btc'], usd_per_btc=prices['btc-usd'])

        if data.get('sum', 0.0):
            data['pct'] = 100 / float(self.funds_target / data.get('sum', 0.0))
            data['available'] = data['sum']
        else:
            data['pct'] = 0.0
            data['available'] = 0.0

        if data['pct'] != self.funds_progress:
            self.funds_progress = data['pct']
            db.session.commit()
            db.session.flush()

        if data['available']:
            data['remaining_pct'] = 100 / float(data['sum'] / data['available'])
        else:
            data['remaining_pct'] = 0.0

        return data

    @classmethod
    def find_by_args(cls, status: int = None, cat: str = None, limit: int = 20, offset=0):
        if isinstance(status, int) and status not in settings.FUNDING_STATUSES.keys():
            raise NotImplementedError('invalid status')
        if isinstance(cat, str) and cat not in settings.FUNDING_CATEGORIES:
            raise NotImplementedError('invalid cat')

        q = cls.query
        if isinstance(status, int):
            q = q.filter(Proposal.status == status)
        if cat:
            q = q.filter(Proposal.category == cat)
        q = q.order_by(Proposal.date_added.desc())
        q = q.limit(limit)
        if isinstance(offset, int):
            q = q.offset(offset)

        return q.all()

    @classmethod
    def search(cls, key: str):
        key_ilike = f"%{key.replace('%', '')}%"
        q = Proposal.query
        q = q.filter(db.or_(
            Proposal.headline.ilike(key_ilike),
            Proposal.content.ilike(key_ilike)))
        return q.all()


class Payout(db.Model):
    __tablename__ = "payouts"
    id = db.Column(db.Integer, primary_key=True)

    proposal_id = db.Column(db.Integer, db.ForeignKey('proposals.id'))
    proposal = relationship("Proposal", back_populates="payouts")

    amount = db.Column(db.Integer, nullable=False)
    to_address = db.Column(db.VARCHAR, nullable=False)

    date_sent = db.Column(db.TIMESTAMP, default=datetime.now)

    ix_proposal_id = db.Index("ix_proposal_id", proposal_id)

    @classmethod
    def add(cls, proposal_id, amount, to_address):
        # @TODO: validate that we can make this payout; check previous payouts
        from flask_login import current_user
        if not current_user.admin:
            raise Exception("user must be admin to add a payout")
        from funding.factory import db

        try:
            payout = Payout(propsal_id=proposal_id, amount=amount, to_address=to_address)
            db.session.add(payout)
            db.session.commit()
            db.session.flush()
            return payout
        except Exception as ex:
            db.session.rollback()
            raise

    @staticmethod
    def get_payouts(proposal_id):
        from funding.factory import db
        return db.session.query(Payout).filter(Payout.proposal_id == proposal_id).all()

    @property
    def as_tx(self):
        return {
            "block_height": "-",
            "type": "out",
            "amount_human": self.amount,
            "amount": self.amount
        }


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)

    proposal_id = db.Column(db.Integer, db.ForeignKey('proposals.id'))
    proposal = relationship("Proposal", back_populates="comments")

    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    user = relationship("User", back_populates="comments")

    date_added = db.Column(db.TIMESTAMP, default=datetime.now)

    message = db.Column(db.VARCHAR, nullable=False)
    replied_to = db.Column(db.ForeignKey("comments.id"))

    locked = db.Column(db.Boolean, default=False)

    automated = db.Column(db.Boolean, default=False)

    ix_comment_replied_to = db.Index("ix_comment_replied_to", replied_to)
    ix_comment_proposal_id = db.Index("ix_comment_proposal_id", proposal_id)

    @property
    def message_html(self):
        return [line for line in self.message.strip().split('\r\n') if line]

    @property
    def ago(self):
        from funding.bin.utils_time import TimeMagic
        return TimeMagic().ago(self.date_added)

    @staticmethod
    def find_by_id(cid: int):
        from funding.factory import db
        return db.session.query(Comment).filter(Comment.id == cid).first()

    @staticmethod
    def remove(cid: int):
        from funding.factory import db
        from flask_login import current_user
        comment = Comment.get(cid=cid)

        if current_user.id != comment.user_id and not current_user.admin:
            raise Exception("no rights to remove this comment")

        try:
            comment.delete()
            db.session.commit()
            db.session.flush()
        except:
            db.session.rollback()
            raise

    @staticmethod
    def lock(cid: int):
        from funding.factory import db
        from flask_login import current_user
        if not current_user.admin:
            raise Exception("admin required")
        comment = Comment.find_by_id(cid=cid)
        if not comment:
            raise Exception("comment by that id not found")
        comment.locked = True
        try:
            db.session.commit()
            db.session.flush()
            return comment
        except:
            db.session.rollback()
            raise

    @classmethod
    def add_comment(cls, pid: int, user_id: int, message: str, cid: int = None, message_id: int = None, automated=False):
        from flask_login import current_user
        from funding.factory import db
        if not message:
            raise Exception("empty message")

        if current_user.id != user_id and not current_user.admin:
            raise Exception("no rights to add or modify this comment")

        if not message_id:
            proposal = Proposal.find_by_id(pid=pid)
            if not proposal:
                raise Exception("no proposal by that id")
            comment = Comment(user_id=user_id, proposal_id=proposal.id, automated=automated)
            if cid:
                parent = Comment.find_by_id(cid=cid)
                if not parent:
                    raise Exception("cannot reply to a non-existent comment")
                comment.replied_to = parent.id
        else:
            try:
                user = db.session.query(User).filter(User.id == user_id).first()
                if not user:
                    raise Exception("no user by that id")
                comment = next(c for c in user.comments if c.id == message_id)
                if comment.locked and not current_user.admin:
                    raise Exception("your comment has been locked/removed")
            except StopIteration:
                raise Exception("no message by that id")
            except:
                raise Exception("unknown error")
        try:
            comment.message = message
            db.session.add(comment)
            db.session.commit()
            db.session.flush()
        except Exception as ex:
            db.session.rollback()
            raise Exception(str(ex))
        return comment
