from twilio.rest import Client
from . import app
from flask import session
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_confirmation_code(to_number):
    verification_code = generate_code()
    send_sms(to_number, verification_code)
    session['verification_code'] = verification_code
    return verification_code


def generate_code():
    return str(random.randrange(100000, 999999))


# TODO make SMS templates
def send_sms(to_number, body):
    account_sid = app.config['TWILIO_ACCOUNT_SID']
    auth_token = app.config['TWILIO_AUTH_TOKEN']
    twilio_number = app.config['TWILIO_NUMBER']
    client = Client(account_sid, auth_token)
    client.api.messages.create(to_number,
                           from_=twilio_number,
                           body=body)


# TODO make email templates
def send_mail(to_email, subject, text='', html='',
              from_email='aran@gliai.ai'):

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(from_email, '07fU53SJzV@L')  # user & password
    # server.send_message(msg)msg.as_string()
    server.sendmail(from_email, to_email, msg.as_string())
    server.quit()