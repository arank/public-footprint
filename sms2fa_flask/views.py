import os
import urllib
import json
import markdown
import datetime
import threading
from types import FunctionType
from flask import render_template, request, url_for, flash, redirect, session, send_from_directory
from flask import abort
from flask import Markup, jsonify
from flask.ext.login import login_required 
from flask.ext.login import login_user
from flask.ext.login import logout_user
from flask.ext.login import current_user
from sqlalchemy import exc
from werkzeug.utils import secure_filename
from . import * 
from .models import User, ServiceConnection, BillingConnection
from .forms import *
from .confirmation_sender import send_confirmation_code, send_mail
from .payment import create_stripe_customer, update_stripe_customer
from .storage import store_file, remove_file

# TODO add google re-captcha to sign in page

# TODO add chat microservice for intercom on landing page etc.

# TODO add all logged in features under account

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico')
@tracker.include
@app.route('/')
def root():
    # TODO redirect to footprint if logged in
    return render_template('index.html')

'''APP SPECIFIC'''


@tracker.include
@app.route('/footprint/<application>/<endpoint>')
@login_required
def application(application, endpoint):

    # See if the app exists
    if application not in app.config['APPS'].keys():
        return "App not found", 422

    # See if the endpoint is valid
    valid_functions = [x for x, y in app.config['APPS'][application]['app'].__dict__.items() if type(y) == FunctionType]
    valid_functions.append('main') # main is also valid
    if endpoint not in valid_functions:
        return "Invalid endpoint", 422

    # TODO make this lazy so no data required in memory
    data = {}
    for service in app.config['APPS'][application]['requires']:
        # get service connection and associated data
        conn = ServiceConnection.query.filter_by(owner=current_user.email, service=service).first()
        if conn is None:
            return "Required service "+service+" not found", 422
        data[service] = json.loads(conn.data)

    # Load the app object on the data
    loaded_app = app.config['APPS'][application]['app'](data)  
    
    # If this is main endpoint send the base HTML,CSS,JS package
    if endpoint == 'main':
        APP_ROOT = os.path.dirname(os.path.abspath(__file__))   # refers to application_top
        APP_STATIC = os.path.join(APP_ROOT, 'static/html/')
        with open(APP_STATIC+app.config['APPS'][application]['view']) as html:
            content = html.read()
        return render_template('app.html', app=app.config['APPS'][application], content=Markup(content))
    
    # If this is not the main endpoint request json data from the object
    else:
        args = request.args
        req_data = eval('loaded_app.'+endpoint+'(args)')
        return json.dumps(req_data), 200


@tracker.include
@app.route('/footprint')
@login_required
def footprint():
    services = []
    active_services = []   
    conns = ServiceConnection.query.filter_by(owner=current_user.email).all()
    for conn in conns:
        # Make sure this service isn't deprecated
        if conn.service in app.config['SERVICES'].keys():
            active_services.append(conn.service)
            services.append(app.config['SERVICES'][conn.service])

    apps = []
    for analytics_app in app.config['APPS'].keys():
        requirement_met = True
        for requirement in app.config['APPS'][analytics_app]['requires']:
            if requirement not in active_services:
                requirement_met = False
                break
        if requirement_met:
            app_data = {
                'name': app.config['APPS'][analytics_app]['name'],
                'icon': app.config['APPS'][analytics_app]['icon'],
                'id': analytics_app
            }
            apps.append(app_data)

    return render_template('footprint.html', apps=apps, services=services)

# this page can be to connect aws/gcp etc.
@tracker.include
@app.route('/services')
@login_required
def services():
    connected_services = []
    unconnected_services = []
    for service in app.config['SERVICES'].keys():
        service_data = {
            'id': service,
            'name': app.config['SERVICES'][service]['name'],
            'icon': app.config['SERVICES'][service]['icon']
        }
        connection = ServiceConnection.query.filter_by(owner=current_user.email, service=service).first()
        if connection is not None:
            connected_services.append(service_data)
        else:
            unconnected_services.append(service_data)

    return render_template('services.html', connected_services=connected_services, unconnected_services=unconnected_services)


# Add data to the service for the user
@tracker.include
@app.route('/connect/<service>/<endpoint>', methods=['POST'])
@login_required
def update_service(service, endpoint):
    # See if the service exists
    if service not in app.config['SERVICES'].keys():
        print("service")
        return "Service not found", 422

    # See if endpoint is valid
    valid_functions = [x for x, y in app.config['SERVICES'][service]['parser'].__dict__.items() if type(y) == FunctionType]
    if endpoint not in valid_functions:
        print("endpoint")
        return "Invalid endpoint", 422

    # Get the connection object
    conn = ServiceConnection.query.filter_by(owner=current_user.email, service=service).first()

    # Pull any stored data to init the parser
    stored_data = {}
    if conn is not None:
        stored_data = json.loads(conn.data)

    # Create a parser object for the data
    parser = app.config['SERVICES'][service]['parser'](stored_data)
    pulled = parser.parsed_data['pulled']
    args = request.get_json(force=True)
    req_data = eval('parser.'+endpoint+'(pulled, args)')

    if conn is None:
        conn = ServiceConnection.save(current_user.email, service)
        msg = 'Successfully connected '+app.config['SERVICES'][service]['name']
    else:
        msg = 'Successfully updated '+app.config['SERVICES'][service]['name']
    
    conn.set_data(parser.parsed_data, commit=True)
    return msg, 200



def upload_data(save_path, file_id, service, current_user_email):
    print('Starting background processing for '+service+' uploaded by '+current_user_email)
    # Write this to s3 and send s3 link to parser
    with open(save_path, 'rb') as f:
        file_bytes = f.read()
        stored_file = store_file(file_bytes, file_id=file_id)

    os.remove(save_path)

    # Parse the file with the right function
    parser = app.config['SERVICES'][service]['parser'](parser_dir=app.config['PARSER_DIR'])
    if parser.add_upload(stored_file):

        with app.app_context():
            # Get the connection object
            conn = ServiceConnection.query.filter_by(owner=current_user_email, service=service).first()

            # Try to create the service connection
            if conn is None:
                conn = ServiceConnection.save(current_user_email, service)
                msg = 'Successfully connected '+app.config['SERVICES'][service]['name']
            else:
                # Remove old remote file for this user's service
                last_stored = conn.data_path
                remove_file(last_stored)
                msg = 'Successfully updated '+app.config['SERVICES'][service]['name']
            
            # set this new remote file for this users service
            conn.set_data_path(stored_file, commit=True)

            # TODO figure a better way to store parsed data
            conn.set_data(parser.parsed_data, commit=True)

            print(msg)

    else:
        # remove the remote file if it fails to validate
        remove_file(stored_file)
        print('Unable to parse uploaded data for '+app.config['SERVICES'][service]['name'])


@tracker.include
@app.route('/connect/<service>', methods=['POST'])
@login_required
def upload_service(service):

    # See if the service exists
    if service not in app.config['SERVICES'].keys():
        return "Service not found", 422

    # check if the post request has the file part
    if 'file' not in request.files:
        return 'No valid file found', 422
    file = request.files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return 'No selected file', 422

    # Create unique & useful file id
    filename = secure_filename(file.filename)
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    file_id = str(current_user.email) + '_' + service
    save_path = os.path.join(app.config['UPLOAD_DIR'], file_id)

    # TODO check the size
    # if len(file_bytes) > app.config['MAX_UPLOAD_LENGTH']:
    #     return 'Uploaded file too large', 422

    # Upload multi-part file https://stackoverflow.com/questions/44727052/handling-large-file-uploads-with-flask
    current_chunk = int(request.form['dzchunkindex'])

    # If the file already exists it's ok if we are appending to it,
    # but not if it's new file that would overwrite the existing one so delete the old one
    if os.path.exists(save_path) and current_chunk == 0:
        os.remove(save_path)

    try:
        with open(save_path, 'ab') as f:
            f.seek(int(request.form['dzchunkbyteoffset']))
            f.write(file.stream.read())
    except OSError:
        return "Not sure why, but we couldn't write the file to disk", 500

    total_chunks = int(request.form['dztotalchunkcount'])

    if current_chunk + 1 == total_chunks:
        # This was the last chunk, the file should be complete and the size we expect
        if os.path.getsize(save_path) != int(request.form['dztotalfilesize']):
            return 'Size mismatch', 500
        else:
            # print('File has been uploaded successfully')
            file_id = now + '_' +str(current_user.email) + '_' + filename 

            # upload_data(save_path, file_id, service, current_user)
            upload_thread = threading.Thread(target=upload_data, args=(save_path, file_id, service, str(current_user.email)))
            upload_thread.start()
            return 'File has been uploaded successfully', 200
    else:
        print('Chunk '+str(current_chunk + 1)+' of '+str(total_chunks))

    return "Chunk upload successful", 200


@tracker.include
@app.route('/connect/<service>', methods=['GET'])
@login_required
def connect_service(service):
    # TODO maybe only allow this if email verified

    # See if the service exists
    if service not in app.config['SERVICES'].keys():
        return "Service not found", 422

    # if request.method == 'POST':

    #     # check if the post request has the file part
    #     if 'file' not in request.files:
    #         return 'No valid file found', 422
    #     file = request.files['file']
    #     # if user does not select file, browser also
    #     # submit an empty part without filename
    #     if file.filename == '':
    #         return 'No selected file', 422
        
    #     # check file size in memory
    #     # For Security File should NEVER touch disk
    #     # TODO update this for multi-part uploads
    #     file_bytes = file.read()
    #     if len(file_bytes) > app.config['MAX_UPLOAD_LENGTH']:
    #         return 'Uploaded file too large', 422
        
    #     if file and allowed_file(file.filename):
    #         # TODO make uploading & parsing a background task with spinner on UI

    #         # Create unique & useful file id
    #         filename = secure_filename(file.filename)
    #         now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    #         file_id = now + '_' +str(current_user.email) + '_' + filename     

    #         # TODO Replace with more secure data store
    #         # Write this to s3 and send s3 link to parser
    #         stored_file = store_file(file_bytes, file_id=file_id)

    #         # TODO Make this run as a remote secure job with gliai
    #         # Parse the file with the right function
    #         parser = app.config['SERVICES'][service]['parser']()
    #         if parser.add_upload(stored_file): # TODO parser.validate(stored_file)
    #             # Get the connection object
    #             conn = ServiceConnection.query.filter_by(owner=current_user.email, service=service).first()

    #             # Try to create the service connection
    #             if conn is None:
    #                 conn = ServiceConnection.save(current_user.email, service)
    #                 msg = 'Successfully connected '+app.config['SERVICES'][service]['name']
    #             else:
    #                 # Remove old remote file for this user's service
    #                 last_stored = conn.data_path
    #                 remove_file(last_stored)
    #                 msg = 'Successfully updated '+app.config['SERVICES'][service]['name']
                
    #             # set this new remote file for this users service
    #             conn.set_data_path(stored_file, commit=True)

    #             # TODO figure a better way to store parsed data
    #             # TODO parser.add_upload(stored_file, conn) do this in background
    #             conn.set_data(parser.parsed_data, commit=True)

    #             return msg, 200

    #         else:
    #             # remove the remote file if it fails to validate
    #             remove_file(stored_file)
    #             return 'Unable to parse uploaded data for '+app.config['SERVICES'][service]['name'], 422
        
    #     else:    
    #         return 'Incorrect file type, expected .zip .gz or .tar.gz extension', 422

    APP_ROOT = os.path.dirname(os.path.abspath(__file__))   # refers to application_top
    APP_STATIC = os.path.join(APP_ROOT, 'static/markdown/')
    with open(APP_STATIC+app.config['SERVICES'][service]['markdown']) as md:
        content = md.read()

    packet = {
        'id': service,
        'name': app.config['SERVICES'][service]['name'],
        'instructions': Markup(markdown.markdown(content)),
        'limit': app.config['MAX_UPLOAD_LENGTH']/1000
    }
    return render_template('upload.html', service=packet)


''' BASIC USER SECURITY HANDLING '''

@tracker.include
@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    form = SignUpForm()
    if form.validate_on_submit():
        try:
            user = User.save_from_dict(form.as_dict)
        except exc.IntegrityError as e:
            db.session.rollback()

            # If email not verified allow this as an update registration
            user = User.query.get(form.email.data)
            if user.phone_verified:
                flash('Account already registered & verified.', 'error')
                return redirect(request.url)
            else:
                db.session.rollback()
                user.update_from_dict(form.as_dict)

        # Send welcome mail
        msg = "Welcome to Footprint! We are happy to have you."
        send_mail(user.email, "Welcome to Footprint", html=msg)

        # Verify phone number
        session['user_email'] = user.email
        send_confirmation_code(user.international_phone_number)
        flash("Please verify your phone number to continue")
        return redirect(url_for('confirmation'))

    return render_template('signup.html', form=form)


@tracker.include
@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            user = User.query.get(form.email.data)

            if user and user.is_password_valid(form.password.data):
                session['user_email'] = user.email

                # check if login is stale and if it is 2FA
                if False:# TODO PUT THIS BACK user.stale:
                    send_confirmation_code(user.international_phone_number)
                    return redirect(url_for('confirmation'))
                else:
                    login_user(user)
                    return redirect(url_for('root'))
            flash('Wrong user/password.', 'error')

    return render_template('sign_in.html', form=form)


@tracker.include
@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

# See historical payments
@tracker.include
@app.route('/payment_history')
@login_required
def payment_history():
    return render_template('billing.html')

# Manage payment methods
@tracker.include
@app.route('/manage_payment', methods=['GET', 'POST'])
@login_required
def manage_payment():
    # TODO add support for wepay alipay idrb
    conn = BillingConnection.query.filter_by(
            owner=current_user.email, service='stripe').first()

    # Only allow adding payment if email verified
    if request.method == 'POST' and current_user.email_verified:
        stripe_data = json.loads(urllib.parse.unquote(request.form['stripeToken']))
        failed = False
        if conn is None:
            # Create a new conenction to stripe
            customer_id = create_stripe_customer(current_user.email, stripe_data['id'])
            if customer_id is not None:
                conn = BillingConnection.save(current_user.email, 'stripe', customer_id)
                flash("Payment method successfully added.")
            else:
                failed = True
                flash("Error adding payment method.", 'error')
        else:
            # Update existing connection with new card
            customer_id = conn.billing_id
            success = update_stripe_customer(customer_id, stripe_data['id'])
            if success:
                flash("Payment method successfully updated.")
            else:
                failed = True
                flash("Error updating payment method.", 'error')

        if not failed:
            # Set new card data
            conn.set_billing_info(stripe_data['card'], commit=True)
            
            # Set user's payment as active
            current_user.set_payment_active(True, commit=True)

            # Send card added message
            msg = "A new "+stripe_data['card']['brand']+" card ending in "+str(stripe_data['card']['last4'])+" and expiring "+str(stripe_data['card']['exp_month'])+"/"+str(stripe_data['card']['exp_year'])+" was added to your Footprint account."
            send_mail(current_user.email, "New Card Added to Footprint", html=msg)
       
    # Prepare card info for display
    card = None
    if conn is not None:
        card = json.loads(conn.billing_info)

    return render_template('payment.html', key=app.config['STRIPE_PUBLISHABLE_KEY'], card=card)

def authenticate_from_token(token):
    if token is None:
        return None
    user = User.verify_token(app.config['SECRET_KEY'], token)
    if user is not None:
        print("reset token authenticated "+user.email)
    return user

# Page to request a password reset link
@tracker.include
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ResetPassword(request.form) #form
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.get_token(app.config['SECRET_KEY'])
            # Send reset link email
            reset_url = app.config['URL_BASE']+'/reset_password?token='+token
            msg = "Please visit <a href='"+reset_url+"'> this link </a> or paste the URL below into yoru browser to reset your Footprint password: "+reset_url
            send_mail(email, "Footprint Password Reset Link", html=msg)
            flash('Password reset link sent.')

        else:
            flash('Email not found.', 'error')

    return render_template('forgot.html', form=form)

# Page to reset password
@tracker.include
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    # Get any submitted reset tokens
    token = request.args.get('token', None)
    form = ResetPasswordSubmit(request.form, token=token) #form
    
    if request.method == 'POST':
        if form.validate_on_submit():
            
            user = current_user
            # If not logged in a valid token is needed to update password
            if not current_user.is_authenticated:
                user = authenticate_from_token(form.token.data)
                if user is None:
                    flash("Please log in or provide a valid reset token to access this page.")
                    return redirect(url_for('sign_in')) 

            # send email to make sure password reset is ok
            msg = "Your Footprint password was just reset. If this wasn't you please email support@gliai.ai"
            send_mail(user.email, "Your Footprint Password Was Reset", text=msg)

            # update user password
            user.set_password(form.password.data, commit=True)

            # Set user to stale to make sure 2FA is needed on next login
            user.set_stale(True, commit=True)

            flash("Password reset")
            return redirect(request.url)


    # if not logged in a valid token is needed to access this page
    if not current_user.is_authenticated:
        user = authenticate_from_token(token)
        if user is None:
            flash("Please log in or provide a valid reset token to access this page.")
            return redirect(url_for('sign_in'))

    return render_template('password.html', form=form)

def send_confirm_email(user):
    token = user.get_token(app.config['SECRET_KEY']) # email confirm token
    confirm_url = app.config['URL_BASE']+'/email_confirmation?token='+token
    msg = "Please visit <a href='"+confirm_url+"'> this \
    link </a> or paste the URL below into your browser to \
    verify your Footprint email: "+confirm_url
    send_mail(user.email, "Verify Footprint Email", html=msg)

# Endpoint to Re-send email verify link
@tracker.include
@app.route('/send_confirmation_email')
@login_required
def send_confirmation_email():
    if not current_user.email_verified:
        send_confirm_email(current_user)
        flash("Verification email sent")
    else:
        flash("Email already verified", 'error')
    return redirect('/settings')

# Endpoint to confirm the email
@tracker.include
@app.route('/email_confirmation')
def email_confirmation():
    token = request.args.get('token', None)
    user = authenticate_from_token(token)
    if user is None:
        flash("Please provide a valid email verification token.")
        return redirect(url_for('sign_in'))

    # Set user email to verified
    user.set_email_verified(True, commit=True)
    flash('Email successfully verified.')    
    return redirect(url_for('root'))


# Page to verify 2FA phone number
@tracker.include
@app.route('/confirmation', methods=['GET', 'POST'])
def confirmation():
    user = User.query.get(session.get('user_email', '')) or abort(401)

    if request.method == 'POST':
        if request.form['verification_code'] == session['verification_code']:
            
            # Set stale to false
            user.set_stale(False, commit=True)

            # Set phone verified if not
            if not user.phone_verified:
                user.set_phone_verified(True, commit=True)
                flash('Phone number successfully verified.')    

                # If first phone verification send verification email as well
                send_confirm_email(user)

            login_user(user)
            return redirect(url_for('root'))
        flash('Wrong code. Please try again.', 'error')

    return render_template('confirmation.html', user=user)


@tracker.include
@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('root'))
