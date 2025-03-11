# Investment Tracker

This is a Python-based investment tracking application that allows users to manage their investment accounts, track stock prices, and calculate monthly market values.

## Features

- User registration and login
- Add, edit, and delete investment accounts
- Track stock prices and calculate market values
- Monthly market value tracking and visualization
- Transfer funds between accounts

## Installation

1. Clone the repository:

```sh
git clone -b master https://github.com/ellionsh/investment-tracker.git
cd investment-tracker
```

2. Create and activate a virtual environment:

```sh
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install the dependencies:

```sh
pip install -r requirements.txt
```

4. Configure the database and environment variables in `config.py`:

```python
class Config:
    SECRET_KEY = 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://your_username:your_password@localhost/investment_tracker'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    POLYGON_API_KEY = 'your_polygon_api_key'
    EXCHANGE_RATE_API_URL = 'https://api.exchangerate-api.com/v4/latest/USD'
```

5. Initialize the database:

```sh
python manage.py db init
python manage.py db migrate
python manage.py db upgrade
```

6. Run the application:

```sh
flask run
```

## Usage

1. Register a new user account.
2. Login with the registered account.
3. Add and manage investment accounts.
4. Track stock prices and market values.
5. View monthly market value changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
