import os

basedir = os.path.abspath(os.path.dirname(__file__))


class DefaultConfig(object):
    SECRET_KEY = 'secret-key'
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = ('sqlite:///' +
                               os.path.join(basedir, 'default.sqlite'))
    SESSION_TYPE = 'sqlalchemy'
    URL_BASE = 'localhost:5000'
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', None)
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', None)
    TWILIO_NUMBER = os.environ.get('TWILIO_NUMBER', None)
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', None)
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', None)
    
    S3_BUCKET_NAME = 'footprint-user-data'
    AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY', None)
    AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY', None)

    WASABI_BUCKET_NAME = 'footprint'
    WASABI_ACCESS_KEY = os.environ.get('WASABI_ACCESS_KEY', None)
    WASABI_SECRET_KEY = os.environ.get('WASABI_SECRET_KEY', None)

class DevelopmentConfig(DefaultConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = ('sqlite:///' +
                               os.path.join(basedir, 'dev.sqlite'))


class TestConfig(DefaultConfig):
    SQLALCHEMY_DATABASE_URI = ('sqlite:///' +
                               os.path.join(basedir, 'test.sqlite'))
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    DEBUG = True
    TWILIO_ACCOUNT_SID = 'AC2XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    TWILIO_AUTH_TOKEN = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    TWILIO_NUMBER = '+15551230987'

config_env_files = {
    'test': 'sms2fa_flask.config.TestConfig',
    'development': 'sms2fa_flask.config.DevelopmentConfig',
}
