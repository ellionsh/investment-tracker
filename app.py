from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DECIMAL, func
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, date
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import re
import os

app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    __tablename__ = 'Users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    createdAt = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updatedAt = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'createdAt': self.createdAt.strftime('%Y-%m-%d %H:%M:%S'),
            'updatedAt': self.updatedAt.strftime('%Y-%m-%d %H:%M:%S')
        }

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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_stock_price(symbol):
    url = f'https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?adjusted=true&apiKey={app.config["POLYGON_API_KEY"]}'
    response = requests.get(url)
    data = response.json()
    return data['results'][0]['c']

def get_exchange_rate():
    response = requests.get(app.config['EXCHANGE_RATE_API_URL'])
    data = response.json()
    return data['rates']['CNY']

def is_local_network(ip):
    local_patterns = [
        re.compile(r'^127\.'), 
        re.compile(r'^192\.168\.'), 
        re.compile(r'^10\.'), 
        re.compile(r'^172\.(1[6-9]|2[0-9]|3[0-1])\.')
    ]
    for pattern in local_patterns:
        if pattern.match(ip):
            return True
    return False

def local_network_or_login_required(func):
    def wrapper(*args, **kwargs):
        if is_local_network(request.remote_addr):
            if not current_user.is_authenticated:
                user = User.query.get(1) 
                login_user(user)
            return func(*args, **kwargs)
        return login_required(func)(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('注册成功，请登录。')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误。')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@local_network_or_login_required
def index():
    return render_template('index.html')

@app.route('/api/accounts', methods=['GET'])
@local_network_or_login_required
def get_accounts():
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    return jsonify([account.to_dict() for account in accounts])

@app.route('/api/accounts/<int:id>', methods=['GET'])
@local_network_or_login_required
def get_account(id):
    account = db.session.get(Account, id)
    if account and account.user_id == current_user.id:
        return jsonify(account.to_dict())
    return jsonify({'message': 'Account not found'}), 404

@app.route('/api/accounts', methods=['POST'])
@local_network_or_login_required
def add_account():
    data = request.json
    if data['type'] == '股票账户':
        stock_price = get_stock_price(data['stockSymbol'])
        exchange_rate = get_exchange_rate()
        market_value = stock_price * data['shares'] * exchange_rate
    else:
        market_value = data.get('marketValue', 0) 

    new_account = Account(
        type=data['type'],
        details=data['details'],
        stockSymbol=data.get('stockSymbol'),
        shares=data.get('shares'),
        marketValue=market_value,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        user_id=current_user.id
    )
    db.session.add(new_account)
    db.session.commit()
    return jsonify(new_account.to_dict()), 201

@app.route('/api/accounts/<int:id>', methods=['PUT'])
@local_network_or_login_required
def update_account(id):
    data = request.json
    account = db.session.get(Account, id)
    if account and account.user_id == current_user.id:
        account.shares = data.get('shares', account.shares)
        if account.type == '股票账户':
            stock_price = get_stock_price(account.stockSymbol)
            exchange_rate = get_exchange_rate()
            account.marketValue = stock_price * account.shares * exchange_rate
        else:
            account.marketValue = data.get('marketValue', account.marketValue)
        account.updatedAt = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify(account.to_dict())
    return jsonify({'message': 'Account not found'}), 404

@app.route('/api/accounts/<int:id>', methods=['DELETE'])
@local_network_or_login_required
def delete_account(id):
    account = db.session.get(Account, id)
    if account and account.user_id == current_user.id:
        db.session.delete(account)
        db.session.commit()
        return jsonify({'message': 'Account deleted'})
    return jsonify({'message': 'Account not found'}), 404

@app.route('/api/monthlyMarketValues', methods=['GET'])
@local_network_or_login_required
def get_monthly_market_values():
    values = MonthlyMarketValue.query.order_by(MonthlyMarketValue.month.asc()).all()
    return jsonify([value.to_dict() for value in values])

@app.route('/api/monthlyMarketValues', methods=['POST'])
@local_network_or_login_required
def add_monthly_market_value():
    data = request.json
    new_value = MonthlyMarketValue(
        totalMarketValue=data['totalMarketValue'],
        month=datetime.strptime(data['month'], '%Y-%m-%d')
    )
    db.session.add(new_value)
    db.session.commit()
    return jsonify(new_value.to_dict()), 201

@app.route('/api/refresh', methods=['POST'])
@local_network_or_login_required
def refresh_market_values():
    accounts = Account.query.filter_by(type='股票账户', user_id=current_user.id).all()
    exchange_rate = get_exchange_rate()
    for account in accounts:
        stock_price = get_stock_price(account.stockSymbol)
        account.marketValue = stock_price * account.shares * exchange_rate
        account.updatedAt = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'message': 'Market values refreshed'}), 200

@app.route('/api/transfer', methods=['POST'])
@local_network_or_login_required
def transfer_funds():
    data = request.json
    from_account = db.session.get(Account, data['fromAccountId'])
    to_account = db.session.get(Account, data['toAccountId'])
    amount = data['amount']

    if not from_account or not to_account or from_account.user_id != current_user.id or to_account.user_id != current_user.id:
        return jsonify({'message': '无效的账户ID'}), 400

    if from_account.marketValue is None or from_account.marketValue < amount:
        return jsonify({'message': '转出账户余额不足'}), 400

    from_previous_balance = from_account.marketValue
    to_previous_balance = to_account.marketValue or 0

    from_account.marketValue -= amount
    to_account.marketValue += amount

    from_transaction = Transaction(
        accountId=from_account.id,
        change=-amount,
        previousBalance=from_previous_balance,
        newBalance=from_account.marketValue,
        timestamp=datetime.now(timezone.utc),
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc)
    )
    to_transaction = Transaction(
        accountId=to_account.id,
        change=amount,
        previousBalance=to_previous_balance,
        newBalance=to_account.marketValue,
        timestamp=datetime.now(timezone.utc),
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc)
    )

    db.session.add(from_transaction)
    db.session.add(to_transaction)
    db.session.commit()

    return jsonify({'message': '转账成功'}), 200

@app.route('/api/typeMarketValues', methods=['GET'])
@local_network_or_login_required
def get_type_market_values():
    type_market_values = db.session.query(
        Account.type, func.sum(Account.marketValue).label('totalMarketValue')
    ).filter(Account.user_id == current_user.id).group_by(Account.type).all()
    result = {type_: marketValue for type_, marketValue in type_market_values}
    return jsonify(result)

def refresh_daily_stock_market_values():
    with app.app_context():
        accounts = Account.query.filter_by(type='股票账户').all()
        exchange_rate = get_exchange_rate()
        for account in accounts:
            stock_price = get_stock_price(account.stockSymbol)
            account.marketValue = stock_price * account.shares * exchange_rate
            account.updatedAt = datetime.now(timezone.utc)
        db.session.commit()

def calculate_monthly_total_market_value():
    with app.app_context():
        accounts = Account.query.all()
        total_market_value = sum(account.marketValue or 0 for account in accounts)
        new_value = MonthlyMarketValue(
            totalMarketValue=total_market_value,
            month=date.today().replace(day=1) 
        )
        db.session.add(new_value)
        db.session.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(func=refresh_daily_stock_market_values, trigger='cron', hour=0, minute=0)
scheduler.add_job(func=calculate_monthly_total_market_value, trigger='cron', day=1, hour=0, minute=0)
scheduler.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
