import os

from datetime import timedelta

PERMANENT_SESSION_LIFETIME = timedelta(days=4)
SECRET_KEY = os.getenv('SECRET_KEY', '31415926535')
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql:///finnsyll')
TESTING = not bool(os.environ.get('DATABASE_URL'))

# if TESTING:
#     SQLALCHEMY_DATABASE_URI = 'postgresql:///FINNSYLL_BACKUP'

# else:
#     SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
