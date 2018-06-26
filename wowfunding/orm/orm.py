from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
import settings

base = declarative_base(name="Model")


class User(base):
    __tablename__ = "users"
    id = sa.Column('user_id', sa.Integer, primary_key=True)
    username = sa.Column(sa.String(20), unique=True, index=True)
    password = sa.Column(sa.String(60))
    email = sa.Column(sa.String(50), unique=True, index=True)
    registered_on = sa.Column(sa.DateTime)
    admin = sa.Column(sa.Boolean, default=False)
    proposals = relationship('Proposal', back_populates="user")

    def __init__(self, username, password, email):
        from wowfunding.factory import bcrypt
        self.username = username
        self.password = bcrypt.generate_password_hash(password).decode('utf8')
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
        return '<User %r>' % self.username


class Proposal(base):
    __tablename__ = "proposals"
    id = sa.Column(sa.Integer, primary_key=True)
    headline = sa.Column(sa.VARCHAR, nullable=False)
    content = sa.Column(sa.VARCHAR, nullable=False)
    category = sa.Column(sa.VARCHAR, nullable=False)
    date_added = sa.Column(sa.TIMESTAMP, default=datetime.now)
    html = sa.Column(sa.VARCHAR)
    last_edited = sa.Column(sa.TIMESTAMP)

    # the FFS target
    funds_target = sa.Column(sa.Float, nullable=False)

    # the FFS progress (cached)
    funds_progress = sa.Column(sa.Float, nullable=False)

    # the FFS withdrawal amount (paid to the author)
    funds_withdrew = sa.Column(sa.Float, nullable=False, default=0)

    # the FFS receiving and withdrawal addresses
    addr_donation = sa.Column(sa.VARCHAR)
    addr_receiving = sa.Column(sa.VARCHAR)

    # proposal status:
    # -1: disabled
    # 0: proposed
    # 1: wip
    # 2: completed
    status = sa.Column(sa.INTEGER, default=0)

    user_id = sa.Column(sa.Integer, sa.ForeignKey('users.user_id'))
    user = relationship("User", back_populates="proposals")

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
            'content': self.content,
            'category': self.category,
            'funds_target': self.funds_target,
            'funded_pct': self.funds_progress,
            'addr_donation': self.addr_donation,
            'status': self.status,
            'user': self.user.username
        }

    @classmethod
    def find_by_id(cls, pid: int):
        q = cls.query
        q = q.filter(Proposal.id == pid)
        result = q.first()
        if not result:
            return
        # check if we have a valid addr_donation generated. if not, make one.
        if not result.addr_donation:
            Proposal.generate_donation_addr(result)
        return result

    @property
    def balance(self):
        """This property retrieves the current funding status
        of this proposal. It uses Redis cache to not spam the
        wownerod too much. Returns a nice dictionary containing
        all relevant proposal funding info"""
        from wowfunding.factory import cache, db_session
        rtn = {'sum': 0.0, 'txs': [], 'pct': 0.0}

        cache_key = 'wow_balance_pid_%d' % self.id
        data = cache.get(cache_key)
        if not data:
            from wowfunding.bin.daemon import WowneroDaemon
            try:
                data = WowneroDaemon().get_transfers_in(index=self.id)
                if not isinstance(data, dict):
                    print('error; get_transfers; %d' % self.id)
                    return rtn
                cache.set(cache_key, data=data, expiry=300)
            except:
                print('error; get_transfers; %d' % self.id)
                return rtn

        for tx in data['txs']:
            tx['datetime'] = datetime.fromtimestamp(tx['timestamp'])

        if data.get('sum', 0.0):
            data['pct'] = 100 / float(self.funds_target / data.get('sum', 0.0))
            data['remaining'] = data['sum'] - self.funds_withdrew
        else:
            data['pct'] = 0.0
            data['remaining'] = 0.0

        if data['pct'] != self.funds_progress:
            self.funds_progress = data['pct']
            db_session.commit()
            db_session.flush()

        if data['remaining']:
            data['remaining_pct'] = 100 / float(data['sum'] / data['remaining'])
        else:
            data['remaining_pct'] = 0.0

        return data

    @staticmethod
    def generate_donation_addr(cls):
        from wowfunding.factory import db_session
        from wowfunding.bin.daemon import WowneroDaemon
        if cls.addr_donation:
            return cls.addr_donation

        try:
            addr_donation = WowneroDaemon().get_address(index=cls.id)
            if not isinstance(addr_donation, dict):
                raise Exception('get_address, needs dict; %d' % cls.id)
        except Exception as ex:
            print('error: %s' % str(ex))
            return

        if addr_donation.get('address'):
            cls.addr_donation = addr_donation['address']
            db_session.commit()
            db_session.flush()
            return addr_donation['address']

    @classmethod
    def find_by_args(cls, status:int = None, cat: str = None, limit: int = 20, offset=0):
        if status is None or not status >= 0 or not status <= 2:
            raise NotImplementedError('missing status')

        q = cls.query
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
        key_ilike = '%' + key.replace('%', '') + '%'
        q = Proposal.query
        q = q.filter(sa.or_(
            Proposal.headline.ilike(key_ilike),
            Proposal.content.ilike(key_ilike)))
        return q.all()
