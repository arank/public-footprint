RUN apt-get update
RUN apt-get install python3-pip
RUN git clone https://github.com/arank/footprint
WORKDIR ./footprint/website
RUN mkdir ../uploads
RUN mkdir ../parser
RUN pip3 install -r requirements.txt
RUN python3 manage.py runserver --host 0.0.0.0 --port 443

RUN rm -rf /footprint/website/sms2fa_flask/dev.sqlite
RUN python3 manage.py db upgrade
RUN python3 manage.py db upgrade
