import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+mysqlconnector://<username>:<password>@localhost/investment_tracker'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    POLYGON_API_KEY = os.environ.get('POLYGON_API_KEY') or 'your_polygon_api_key'
    EXCHANGE_RATE_API_URL = 'https://api.exchangerate-api.com/v4/latest/USD'
