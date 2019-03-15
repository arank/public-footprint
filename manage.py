from flask.ext.script import Manager, Server
from flask.ext.migrate import Migrate, MigrateCommand
from flask_migrate import upgrade as upgrade_database
from sms2fa_flask import db, prepare_app

app = prepare_app(environment='development')
migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)
manager.add_command('runserver', Server(host="localhost",
                                        port="5000", # "443" #ssl_context='adhoc')) 
                                        ssl_context=("cert.pem", "key.pem")))

# from sms2fa_flask.server import GunicornServer
# manager.add_command("gunicorn", GunicornServer(host="localhost",
#                                         port="5000", #ssl_context='adhoc'))
#                                         ssl_crt="cert.pem", ssl_key="key.pem"))

@manager.command
def test():
    """Run the unit tests."""
    import sys
    import unittest
    prepare_app(environment='test')
    upgrade_database()
    tests = unittest.TestLoader().discover('.', pattern="*_tests.py")
    test_result = unittest.TextTestRunner(verbosity=2).run(tests)

    if not test_result.wasSuccessful():
        sys.exit(1)


@manager.command
def dbseed():
    pass

if __name__ == "__main__":
    manager.run() 

# https://blog.miguelgrinberg.com/post/running-your-flask-application-over-https
# app.run(ssl_context='adhoc')
# ssl_crt=None, ssl_key=None
