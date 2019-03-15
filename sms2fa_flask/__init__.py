from sms2fa_flask.config import config_env_files
from sms2fa_flask.models import db, User
from flask import Flask

from flask.ext.login import LoginManager
from flask.ext.session import Session
from flask_bootstrap import Bootstrap

# from flask_sslify import SSLify
from flask.ext.track_usage import TrackUsage
from flask.ext.track_usage.storage.sql import SQLStorage
from flask_track_usage.storage.printer import PrintWriter

app = Flask(__name__)
Bootstrap(app)

# TODO open port 80 and redirect all request to HTTPS (443)
# sslify = SSLify(app)

login_manager = LoginManager()
sess = Session()

# from flask_analytics import Analytics
# TODO put this in templates to get client side analytics string {{ analytics }}

# TODO add google analytics
# Analytics(app)
# app.config['ANALYTICS']['GOOGLE_CLASSIC_ANALYTICS']['ACCOUNT'] = 'XXXXXXXX'

# TODO add self hosted clinet side analytics
# Analytics(app)
# app.config['ANALYTICS']['PIWIK']['BASE_URL'] = 'XXXXXXXXXXXXX'
# app.config['ANALYTICS']['PIWIK']['SITE_ID'] = 'XXXXXXXXXXXXX'

# TODO add self hosted serverside analytics
# TODO extend to username tracking using login: current_user server side
app.config['TRACK_USAGE_USE_FREEGEOIP'] = True
app.config['TRACK_USAGE_FREEGEOIP_ENDPOINT'] = 'http://extreme-ip-lookup.com/json/{ip}'
app.config['TRACK_USAGE_INCLUDE_OR_EXCLUDE_VIEWS'] = 'include'
tracker = TrackUsage(app, [
    PrintWriter(),
    # SQLStorage(db)
])

def prepare_app(environment='development', p_db=db):
    app.config.from_object(config_env_files[environment])
    login_manager.setup_app(app)
    login_manager.login_view = 'sign_in'
    p_db.init_app(app)
    sess.init_app(app)
    app.session_interface.db.create_all()
    from . import views
    return app


def save_and_commit(item):
    db.session.add(item)
    db.session.commit()
db.save = save_and_commit


@login_manager.user_loader
def user_loader(user_id):
    return User.query.get(user_id)


'''APP SPECIFIC'''

'''Define all the apps we can use on our imported services'''

#  TODO seperate between 'base' apps (free); 
# 'pro' apps (activate all with subscription)
# 'premium' apps (pay to activate)

from sms2fa_flask.apps import *
app.config['APPS'] = {
    'venmo-trail':{
        'icon': 'venmo-data.jpg',
        'name': 'Venmo Trail',
        'view': 'venmo_trail.html',
        'app': VenmoTrail,
        'requires': ['venmo']
    },
    'uber-tracks':{
        'icon': 'uber-data.jpg',
        'name': 'Uber Tracks',
        'view': 'uber_tracks.html',
        'app': UberTracks,
        'requires': ['uber']
    },
    'data-gram':{
        'icon': 'insta-analytics.png',
        'name': 'Data Gram',
        'short_description': 'Data Gram helps you ',
        'view': 'data_gram.html',
        'app': DataGram,
        'requires': ['instagram']
    },
    'snap-data-lens':{
        'icon': 'snap-analytics.jpg',
        'name': 'Snap Data Lens',
        'view': 'snap_data_lens.html',
        'app': SnapDataLens,
        'requires': ['snapchat']
    },
    'facebook-selfie':{
        'icon': 'facebook-data.jpg',
        'name': 'Facebook Data Selfie',
        'view': 'facebook_selfie.html',
        'app': FacebookSelfie,
        'requires': ['facebook']
    }
    # TODO add whats app and create (Facebook Family of App)
    # TODO add google
    # TODO create "Chatime" to track all your conversations (in convo apps) with people
}

'''Define how to import data from services'''

from sms2fa_flask.parser import *
app.config['SERVICES'] = {
    # 'venmo': {
    #     'icon':'venmo.jpeg',
    #     'name':'Venmo',
    #     'markdown': 'venmo.md',
    #     'parser': VenmoParser
    # }, 
    # 'uber': {
    #     'icon':'uber.jpeg',
    #     'name':'Uber',
    #     'markdown': 'uber.md',
    #     'parser': UberParser
    # }, 
    'instagram': {
        'icon':'instagram.jpeg',
        'name':'Instagram',
        'markdown': 'instagram.md',
        'parser': InstagramParser
    },
    'facebook': {
        'icon':'facebook.jpeg',
        'name':'Facebook',
        'markdown': 'facebook.md',
        'parser': FacebookParser
    },
    'snapchat': {
        'icon':'snapchat.jpeg',
        'name':'Snapchat',
        'markdown': 'snapchat.md',
        'parser': SnapchatParser
    }
}

app.config['UPLOAD_DIR'] = '../uploads'
app.config['PARSER_DIR'] = '../parser'
app.config['MAX_UPLOAD_LENGTH'] = 16 * 1024 * 1024 * 1024
ALLOWED_EXTENSIONS = set(['zip', 'tar.gz', 'gz'])
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
