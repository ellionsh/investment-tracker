from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DECIMAL, func
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask_migrate import Migrate
import requests
import re
import os
import logging
import fcntl

app = Flask(__name__)
app.config.from_object('config.Config')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # 设置 session 有效期为 30 分钟

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.session_protection = 'strong'  # 启用 session 保护

logging.basicConfig(level=logging.INFO)

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
    marketValue = db.Column(db.DECIMAL(12, 2), nullable=True)
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
            'marketValue': float(self.marketValue) if self.marketValue is not None else 0,
            'createdAt': self.createdAt.strftime('%Y-%m-%d %H:%M:%S'),
            'updatedAt': self.updatedAt.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': self.user_id
        }

class MonthlyMarketValue(db.Model):
    __tablename__ = 'MonthlyMarketValues'
    id = db.Column(db.Integer, primary_key=True)
    totalMarketValue = db.Column(db.DECIMAL(12, 2), nullable=False)
    month = db.Column(db.Date, nullable=False)
    createdAt = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updatedAt = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'totalMarketValue': float(self.totalMarketValue),
            'month': self.month.strftime('%Y-%m-%d'),
            'createdAt': self.createdAt.strftime('%Y-%m-%d %H:%M:%S'),
            'updatedAt': self.updatedAt.strftime('%Y-%m-%d %H:%M:%S')
        }

class Transaction(db.Model):
    __tablename__ = 'Transactions'
    id = db.Column(db.Integer, primary_key=True)
    accountId = db.Column(db.Integer, nullable=False)
    change = db.Column(db.DECIMAL(12, 2), nullable=False)
    previousBalance = db.Column(db.DECIMAL(12, 2), nullable=False)
    newBalance = db.Column(db.DECIMAL(12, 2), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    createdAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updatedAt = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    reason = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'accountId': self.accountId,
            'change': float(self.change),
            'previousBalance': float(self.previousBalance),
            'newBalance': float(self.newBalance),
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'createdAt': self.createdAt.strftime('%Y-%m-%d %H:%M:%S'),
            'updatedAt': self.updatedAt.strftime('%Y-%m-%d %H:%M:%S'),
            'reason': self.reason
        }

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def get_stock_price(symbol):
    url = f'https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?adjusted=true&apiKey={app.config["POLYGON_API_KEY"]}'
    response = requests.get(url)
    data = response.json()
    if 'results' not in data:
        logging.error(f"Error fetching stock price for {symbol}: {data}")
        raise ValueError(f"Error fetching stock price for {symbol}: {data}")
    return data['results'][0]['c']

def get_exchange_rate():
    response = requests.get(app.config['EXCHANGE_RATE_API_URL'])
    data = response.json()
    return data['rates']['CNY']

def is_local_network(ip):
    local_patterns = [
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
        forwarded_for = request.headers.get('X-Forwarded-For', '')
        ip = forwarded_for.split(',')[0] if forwarded_for else request.remote_addr
        if is_local_network(ip):
            if not current_user.is_authenticated:
                user = db.session.query(User).first()
                if user:
                    login_user(user)
                else:
                    return redirect(url_for('register'))
            return func(*args, **kwargs)
        return login_required(func)(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({'message': '用户名已存在，请选择其他用户名。'}), 400

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            return jsonify({'message': '注册成功，请登录。'}), 200
        except IntegrityError:
            db.session.rollback()
            return jsonify({'message': '用户名已存在，请选择其他用户名。'}), 400
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return jsonify({'message': '登录成功。'}), 200
        else:
            return jsonify({'message': '用户名或者密码错误。'}), 400
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
    if current_user.is_authenticated:
        accounts = Account.query.filter_by(user_id=current_user.id).all()
        return jsonify([account.to_dict() for account in accounts])
    return jsonify({'message': 'User not authenticated'}), 401

@app.route('/api/accounts/<int:id>', methods=['GET'])
@local_network_or_login_required
def get_account(id):
    account = db.session.get(Account, id)
    if account and current_user.is_authenticated and account.user_id == current_user.id:
        return jsonify(account.to_dict())
    return jsonify({'message': 'Account not found'}), 404

@app.route('/api/accounts', methods=['POST'])
@local_network_or_login_required
def add_account():
    if current_user.is_authenticated:
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

        # Add transaction
        transaction = Transaction(
            accountId=new_account.id,
            change=market_value,
            previousBalance=0,
            newBalance=market_value,
            timestamp=datetime.now(timezone.utc),
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
            reason='Account creation'
        )
        db.session.add(transaction)
        db.session.commit()

        return jsonify(new_account.to_dict()), 201
    return jsonify({'message': 'User not authenticated'}), 401

@app.route('/api/accounts/<int:id>', methods=['PUT'])
@local_network_or_login_required
def update_account(id):
    account = db.session.get(Account, id)
    if account and current_user.is_authenticated and account.user_id == current_user.id:
        data = request.json
        previous_market_value = float(account.marketValue)
        account.shares = data.get('shares', account.shares)
        if account.type == '股票账户':
            stock_price = get_stock_price(account.stockSymbol)
            exchange_rate = get_exchange_rate()
            account.marketValue = stock_price * account.shares * exchange_rate
        else:
            account.marketValue = data.get('marketValue', account.marketValue)
        account.updatedAt = datetime.now(timezone.utc)

        # Add transaction only if market value changed
        if account.marketValue != previous_market_value:
            transaction = Transaction(
                accountId=account.id,
                change=float(account.marketValue) - previous_market_value,
                previousBalance=previous_market_value,
                newBalance=float(account.marketValue),
                timestamp=datetime.now(timezone.utc),
                createdAt=datetime.now(timezone.utc),
                updatedAt=datetime.now(timezone.utc),
                reason='Account update'
            )
            db.session.add(transaction)
            db.session.commit()

        return jsonify(account.to_dict())
    return jsonify({'message': 'Account not found'}), 404

@app.route('/api/accounts/<int:id>', methods=['DELETE'])
@local_network_or_login_required
def delete_account(id):
    account = db.session.get(Account, id)
    if account and current_user.is_authenticated and account.user_id == current_user.id:
        previous_market_value = float(account.marketValue)
        db.session.delete(account)
        db.session.commit()

        # Add transaction
        transaction = Transaction(
            accountId=account.id,
            change=-previous_market_value,
            previousBalance=previous_market_value,
            newBalance=0,
            timestamp=datetime.now(timezone.utc),
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
            reason='Account deletion'
        )
        db.session.add(transaction)
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
        month=datetime.strptime(data['month'], '%Y-%m-%d'),
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc)
    )
    db.session.add(new_value)
    db.session.commit()
    return jsonify(new_value.to_dict()), 201

@app.route('/api/refresh', methods=['POST'])
@local_network_or_login_required
def refresh_market_values():
    if current_user.is_authenticated:
        accounts = Account.query.filter_by(type='股票账户', user_id=current_user.id).all()
        exchange_rate = get_exchange_rate()
        for account in accounts:
            stock_price = get_stock_price(account.stockSymbol)
            previous_market_value = float(account.marketValue)
            new_market_value = round(stock_price * account.shares * exchange_rate,2)
            if previous_market_value != new_market_value:
                transaction = Transaction(
                    accountId=account.id,
                    change=new_market_value - previous_market_value,
                    previousBalance=previous_market_value,
                    newBalance=new_market_value,
                    timestamp=datetime.now(timezone.utc),
                    createdAt=datetime.now(timezone.utc),
                    updatedAt=datetime.now(timezone.utc),
                    reason='Market value refresh'
                )
                db.session.add(transaction)
                account.marketValue = new_market_value
                account.updatedAt = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify({'message': 'Market values refreshed'}), 200
    return jsonify({'message': 'User not authenticated'}), 401

@app.route('/api/transfer', methods=['POST'])
@local_network_or_login_required
def transfer_funds():
    if current_user.is_authenticated:
        data = request.json
        from_account = db.session.get(Account, data['fromAccountId'])
        to_account = db.session.get(Account, data['toAccountId'])
        amount = data['amount']

        if not from_account or not to_account or from_account.user_id != current_user.id or to_account.user_id != current_user.id:
            return jsonify({'message': '无效的账户ID'}), 400

        if from_account.marketValue is None or from_account.marketValue < amount:
            return jsonify({'message': '转出账户余额不足'}), 400

        from_previous_balance = float(from_account.marketValue)
        to_previous_balance = float(to_account.marketValue) or 0

        from_account.marketValue = float(from_account.marketValue) - amount
        to_account.marketValue = float(to_account.marketValue) + amount

        from_transaction = Transaction(
            accountId=from_account.id,
            change=-amount,
            previousBalance=from_previous_balance,
            newBalance=float(from_account.marketValue),
            timestamp=datetime.now(timezone.utc),
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
            reason='Transfer out'
        )
        to_transaction = Transaction(
            accountId=to_account.id,
            change=amount,
            previousBalance=to_previous_balance,
            newBalance=float(to_account.marketValue),
            timestamp=datetime.now(timezone.utc),
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
            reason='Transfer in'
        )

        db.session.add(from_transaction)
        db.session.add(to_transaction)
        db.session.commit()

        return jsonify({'message': '转账成功'}), 200
    return jsonify({'message': 'User not authenticated'}), 401

@app.route('/api/typeMarketValues', methods=['GET'])
@local_network_or_login_required
def get_type_market_values():
    if current_user.is_authenticated:
        type_market_values = db.session.query(
            Account.type, func.sum(Account.marketValue).label('totalMarketValue')
        ).filter(Account.user_id == current_user.id).group_by(Account.type).all()
        result = {type_: float(marketValue) for type_, marketValue in type_market_values}
        return jsonify(result)
    return jsonify({'message': 'User not authenticated'}), 401

@app.route('/api/transactions', methods=['GET'])
@local_network_or_login_required
def get_transactions():
    if current_user.is_authenticated:
        start_date = request.args.get('start')
        end_date = request.args.get('end')

        if not start_date or not end_date:
            return jsonify({'message': '请输入有效的日期范围'}), 400

        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)

        transactions = Transaction.query.filter(
            Transaction.timestamp >= start_datetime,
            Transaction.timestamp <= end_datetime,
            Transaction.accountId.in_([account.id for account in current_user.accounts])
        ).order_by(Transaction.timestamp.desc()).all()

        result = []
        for transaction in transactions:
            account = db.session.get(Account, transaction.accountId)
            account_details = account.details if account else '已经删除账户'
            result.append({
                'accountDetails': account_details,
                'change': float(transaction.change),
                'reason': transaction.reason,
                'timestamp': transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })

        return jsonify(result)
    return jsonify({'message': 'User not authenticated'}), 401

@app.route('/api/income', methods=['POST'])
@local_network_or_login_required
def add_income():
    if current_user.is_authenticated:
        data = request.json
        account = db.session.get(Account, data['accountId'])
        if account and account.user_id == current_user.id:
            amount = data['amount']
            account.marketValue = float(account.marketValue) + amount
            transaction = Transaction(
                accountId=account.id,
                change=amount,
                previousBalance=float(account.marketValue) - amount,
                newBalance=float(account.marketValue),
                timestamp=datetime.now(timezone.utc),
                createdAt=datetime.now(timezone.utc),
                updatedAt=datetime.now(timezone.utc),
                reason=data['reason']
            )
            db.session.add(transaction)
            db.session.commit()
            return jsonify({'message': '收入已记录'}), 200
        return jsonify({'message': '账户未找到或无权限'}), 404
    return jsonify({'message': 'User not authenticated'}), 401

@app.route('/api/expense', methods=['POST'])
@local_network_or_login_required
def add_expense():
    if current_user.is_authenticated:
        data = request.json
        account = db.session.get(Account, data['accountId'])
        if account and account.user_id == current_user.id:
            amount = data['amount']
            if account.marketValue is None or account.marketValue < amount:
                return jsonify({'message': '账户余额不足'}), 400
            account.marketValue = float(account.marketValue) - amount
            transaction = Transaction(
                accountId=account.id,
                change=-amount,
                previousBalance=float(account.marketValue) + amount,
                newBalance=float(account.marketValue),
                timestamp=datetime.now(timezone.utc),
                createdAt=datetime.now(timezone.utc),
                updatedAt=datetime.now(timezone.utc),
                reason=data['reason']
            )
            db.session.add(transaction)
            db.session.commit()
            return jsonify({'message': '支出已记录'}), 200
        return jsonify({'message': '账户未找到或无权限'}), 404
    return jsonify({'message': 'User not authenticated'}), 401

def refresh_daily_stock_market_values():
    with app.app_context():
        accounts = Account.query.filter_by(type='股票账户').all()
        exchange_rate = get_exchange_rate()
        for account in accounts:
            try:
                stock_price = get_stock_price(account.stockSymbol)
                previous_market_value = float(account.marketValue)
                new_market_value = round(stock_price * account.shares * exchange_rate,2)
                if previous_market_value != new_market_value:
                    transaction = Transaction(
                        accountId=account.id,
                        change=new_market_value - previous_market_value,
                        previousBalance=previous_market_value,
                        newBalance=new_market_value,
                        timestamp=datetime.now(timezone.utc),
                        createdAt=datetime.now(timezone.utc),
                        updatedAt=datetime.now(timezone.utc),
                        reason='Daily market value refresh'
                    )
                    db.session.add(transaction)
                    account.marketValue = new_market_value
                    account.updatedAt = datetime.now(timezone.utc)
            except ValueError as e:
                logging.error(f"Error updating stock price for {account.stockSymbol}: {e}")
        db.session.commit()

def calculate_monthly_total_market_value():
    with app.app_context():
        accounts = Account.query.all()
        total_market_value = sum(float(account.marketValue) or 0 for account in accounts)
        new_value = MonthlyMarketValue(
            totalMarketValue=total_market_value,
            month=date.today().replace(day=1),
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc)
        )
        db.session.add(new_value)
        db.session.commit()

# 手动刷新路由
@app.route('/manual-refresh', methods=['POST'])
@local_network_or_login_required
def manual_refresh():
    refresh_daily_stock_market_values()
    return jsonify({'message': 'Market values refreshed manually'}), 200

@app.route('/scheduler/jobs', methods=['GET'])
@local_network_or_login_required
def get_scheduler_jobs():
    jobs = scheduler.get_jobs()
    job_list = [{'id': job.id, 'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None} for job in jobs]
    return jsonify(job_list)

scheduler = BackgroundScheduler()
# 获取锁文件的路径
lock_file_path = '/tmp/myaccounts_scheduler.lock'

def acquire_lock():
    if not os.path.exists(lock_file_path):
        open(lock_file_path, 'w').close()
    lock_file = open(lock_file_path, 'r+')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_file
    except IOError:
        lock_file.close()
        return None

# 仅在获得锁时添加调度任务
lock_file = acquire_lock()
if lock_file:
    scheduler.add_job(func=refresh_daily_stock_market_values, trigger='cron', hour=9, minute=0)
    scheduler.add_job(func=calculate_monthly_total_market_value, trigger='cron', day=1, hour=9, minute=0)
    scheduler.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
