from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import UserMixin
import phonenumbers
from passlib.hash import bcrypt
from phonenumbers import PhoneNumberFormat
import datetime
import json
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

db = SQLAlchemy()

class AppConnection(db.Model):
    owner = db.Column(db.String, db.ForeignKey('user.email'), primary_key=True, nullable=False)
    app = db.Column(db.String, primary_key=True)

    # Analytics
    created = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now)

class ServiceConnection(db.Model):
    owner = db.Column(db.String, db.ForeignKey('user.email'), primary_key=True, nullable=False)
    service = db.Column(db.String, primary_key=True)
    
    # Application sepecific
    data_path = db.Column(db.String)
    # TODO find better solution to store parsed data
    data = db.Column(db.Text) 

    # Analytics
    created = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now)

    @classmethod
    def save(cls, user, service):
        conn = ServiceConnection()
        conn.owner = user
        conn.service = service
        db.save(conn)
        return conn

    def set_data(self, data, commit=False):
        self.data = json.dumps(data)
        if commit:
            db.save(self)  

    def set_data_path(self, data_path, commit=False):
        self.data_path = data_path
        if commit:
            db.save(self)

class BillingConnection(db.Model):
    owner = db.Column(db.String, db.ForeignKey('user.email'), primary_key=True, nullable=False)
    service = db.Column(db.String, primary_key=True)

    # Application sepecific
    billing_id = db.Column(db.String)
    billing_info = db.Column(db.Text)

    # Analytics
    created = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now)

    @classmethod
    def save(cls, user, service, billing_id):
        conn = BillingConnection()
        conn.owner = user
        conn.service = service
        conn.billing_id = billing_id
        db.save(conn)
        return conn  

    def set_billing_info(self, data, commit=False):
        self.billing_info = json.dumps(data)
        if commit:
            db.save(self)


class User(db.Model, UserMixin):

    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    phone_number = db.Column(db.String)
    email = db.Column(db.String, primary_key=True)
    password = db.Column(db.String)
    
    # if the user info is verified
    phone_verified = db.Column(db.Boolean, default=False) 
    email_verified = db.Column(db.Boolean, default=False) 
    payment_active = db.Column(db.Boolean, default=False) 
    
    # if the login in stale and needs to be 2FA'd
    stale = db.Column(db.Boolean, default=True) 

    # Analytics
    created = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now)

    # App specific
    services = db.relationship('ServiceConnection', backref='user', lazy=True)
    billings = db.relationship('BillingConnection', backref='user', lazy=True)
    apps = db.relationship('AppConnection', backref='user', lazy=True)


    @classmethod
    def save_from_dict(cls, data):
        user = User(**data)
        user.set_password(data['password'])
        user.active = False
        db.save(user)
        return user

    def update_from_dict(self, data):
        self.first_name = data['first_name']
        self.last_name = data['last_name']
        self.set_password(data['password'])
        self.active = False
        self.phone_number = data['phone_number']
        self.set_phone_verified(False)
        self.set_stale(True)
        db.save(self)

    def is_password_valid(self, given_password):
        return bcrypt.verify(given_password, self.password)

    def set_password(self, new_password, commit=False):
        self.password = bcrypt.encrypt(new_password)
        if commit:
            db.save(self)

    def set_stale(self, stale, commit=False):
        self.stale = stale
        if commit:
            db.save(self)  
            
    def set_phone_verified(self, verified, commit=False):
        self.phone_verified = verified
        if commit:
            db.save(self)  

    def set_email_verified(self, verified, commit=False): 
        self.email_verified = verified
        if commit:
            db.save(self)

    def set_payment_active(self, active, commit=False): 
        self.payment_active = active
        if commit:
            db.save(self)

    @property
    def international_phone_number(self):
        parsed_number = phonenumbers.parse(self.phone_number)
        return phonenumbers.format_number(parsed_number,
                                          PhoneNumberFormat.INTERNATIONAL)

    # Password reset tokens
    def get_token(self, secret, expiration=1800):
        s = Serializer(secret, expiration)
        return s.dumps({'user': self.email}).decode('utf-8')

    @staticmethod
    def verify_token(secret, token):
        s = Serializer(secret)
        try:
            data = s.loads(token)
        except:
            return None
        id = data.get('user')
        if id:
            return User.query.get(id)
        return None

    # The methods below are required by flask-login
    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.email

    # App specific
    def is_service_connected(self, service):
        return

    def connect_service(self, service):
        return
