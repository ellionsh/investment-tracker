from app import db
from datetime import datetime

class Account(db.Model):
    __tablename__ = 'Accounts'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    details = db.Column(db.String(100), nullable=False)
    stockSymbol = db.Column(db.String(10), nullable=True)
    shares = db.Column(db.Integer, nullable=True)
    marketValue = db.Column(db.Float, nullable=True)
    createdAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('accounts', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'details': self.details,
            'stockSymbol': self.stockSymbol,
            'shares': self.shares,
            'marketValue': self.marketValue,
            'createdAt': self.createdAt.strftime('%Y-%m-%d %H:%M:%S'),
            'updatedAt': self.updatedAt.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': self.user_id
        }

class MonthlyMarketValue(db.Model):
    __tablename__ = 'MonthlyMarketValues'
    id = db.Column(db.Integer, primary_key=True)
    totalMarketValue = db.Column(db.Float, nullable=False)
    month = db.Column(db.Date, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'totalMarketValue': self.totalMarketValue,
            'month': self.month.strftime('%Y-%m-%d')
        }

class Transaction(db.Model):
    __tablename__ = 'Transactions'
    id = db.Column(db.Integer, primary_key=True)
    accountId = db.Column(db.Integer, nullable=False)
    change = db.Column(db.Float, nullable=False)
    previousBalance = db.Column(db.Float, nullable=False)
    newBalance = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    createdAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'accountId': self.accountId,
            'change': self.change,
            'previousBalance': self.previousBalance,
            'newBalance': self.newBalance,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'createdAt': self.createdAt.strftime('%Y-%m-%d %H:%M:%S'),
            'updatedAt': self.updatedAt.strftime('%Y-%m-%d %H:%M:%S')
        }
