from abc import ABC, abstractmethod
import uuid
import zipfile
import os
import json
import shutil
import time
from .storage import retrieve_file
import geocoder
import urllib.request
import ssl
import bs4


class Parser(ABC):

    # default parser directory
    PARSER_DIR = '../parser'

    def __init__(self, parsed_data={}, parser_dir=None):
        super().__init__()
        if parser_dir is not None:
            self.PARSER_DIR = parser_dir
        self.parsed_data = parsed_data
        if 'pulled' not in self.parsed_data.keys():
            self.parsed_data['pulled']= {}

        self.uuid = str(uuid.uuid1())

    # Parse an upacked dump
    @abstractmethod
    def parse_upload(self, filepath):
        pass

    # Utility to unpack the dump so users don't have to
    def _unpack_data(self, stored_file_id):
        # Retrieve data from stored file_id
        download_path = retrieve_file(stored_file_id, local_path=self.PARSER_DIR)
        
        # Local path to upack to
        path = self.PARSER_DIR + '/'+ self.uuid

        # Unpack zipfile uploads
        if download_path.endswith('.zip'):
            with zipfile.ZipFile(download_path, "r") as zip_ref:
                zip_ref.extractall(path)

            # Remove the zipfile
            os.remove(download_path)

        return path

    def update_data(self, pulled):
        self.parsed_data['pulled'] = pulled

    # Create the parser from a dumpfile
    def add_upload(self, stored_dump_id):
        # unpack local data
        path = self._unpack_data(stored_dump_id)

        try:
            # parse local data
            parsed_data = self.parse_upload(path)

            # set the parsed data
            self.parsed_data['upload'] = parsed_data

            # remove local data once we finish parsing it
            shutil.rmtree(path)

            return True
            
        except Exception as e:
            print('error parsing data')
            print(e)
            
            # remove local data once we finish parsing it
            shutil.rmtree(path)

            return False


class UberParser(Parser):

    def __init__(self, parsed_data={}, parser_dir=None):
        super(UberParser, self).__init__(parsed_data, parser_dir=parser_dir)

    # TODO see if we can add the data via GDPR upload
    def parse_upload(self, path):
        data_dict = {}
        return data_dict

    # Add all data making sure not to duplicate
    def add_trip(self, pulled, args):

        pulled['total_trips'] = args['data']['trips']['count']

        if 'trips' not in pulled.keys():
            pulled['trips'] = {}

        for trip in args['data']['trips']['trips']:
            if trip['uuid'] not in pulled['trips'].keys():

                # Add geo-data to trips
                loc = geocoder.osm(trip['begintripFormattedAddress'])
                if loc is not None:
                    location = loc.json
                    trip['begintripLocation'] = location
                else:
                    trip['begintripLocation'] = None
                loc = geocoder.osm(trip['dropoffFormattedAddress'])
                if loc is not None:
                    location = loc.json
                    trip['dropoffLocation'] = location
                else:
                    trip['dropoffLocation'] = None

                pulled['trips'][trip['uuid']] = trip

        if 'drivers' not in pulled.keys():
            pulled['drivers'] = {}

        for driver in args['data']['drivers']:
            if driver['uuid'] not in pulled['drivers'].keys():
                pulled['drivers'][driver['uuid']] = driver

        self.update_data(pulled)


class VenmoParser(Parser):

    def __init__(self, parsed_data={}, parser_dir=None):
        super(VenmoParser, self).__init__(parsed_data, parser_dir=parser_dir)

    # TODO see if we can add the data via GDPR upload
    def parse_upload(self, path):
        data_dict = {}
        return data_dict

    # Add all ID'd transaction data making sure not to duplicate
    def add_transaction(self, pulled, args):
        if 'transactions' not in pulled.keys():
            pulled['transactions'] = {}

        for transaction in args['data']:
            if 'payment_id' in transaction.keys():
                if transaction['payment_id'] not in pulled['transactions'].keys():
                    pulled['transactions'][transaction['payment_id']] = transaction

        self.update_data(pulled)

    # Add all friends for a user page making sure not to duplicate
    def add_social_graph(self, pulled, args):

        if 'social_graph' not in pulled.keys():
            pulled['social_graph'] = {}

        if args['user'] not in pulled['social_graph'].keys():
            pulled['social_graph'][args['user']] = []

        for connection in args['connections']:
            if connection not in pulled['social_graph'][args['user']]:
                pulled['social_graph'][args['user']].append(connection)

        self.update_data(pulled)

    # sets the main users
    def set_user(self, pulled, args):
        pulled['main_user'] = args['user']
        self.update_data(pulled)



class InstagramParser(Parser):

    def __init__(self, parsed_data={}, parser_dir=None):
        super(InstagramParser, self).__init__(parsed_data, parser_dir=parser_dir)

    def parse_upload(self, path):
        data_dict = {}
        for file in os.listdir(path):
            if file.endswith('.json'):
                filepath = path+'/'+file
                with open(filepath) as fp:
                    data_dict[file.split('.')[0]] = json.load(fp)

        # Geocode uploaded ALL post data
        for post in data_dict['media']['photos']:
            location = None
            if 'location' in post.keys():
                print("pulling location "+post['location'])
                loc = geocoder.osm(post['location'])
                if loc is not None:
                    location = loc.json
            post['loaded_location'] = location

        for post in data_dict['media']['videos']:
            location = None
            if 'location' in post.keys():
                print("pulling location "+post['location'])
                loc = geocoder.osm(post['location'])
                if loc is not None:
                    location = loc.json
            post['loaded_location'] = location

        for post in data_dict['media']['stories']:
            location = None
            if 'location' in post.keys():
                print("pulling location "+post['location'])
                loc = geocoder.osm(post['location'])
                if loc is not None:
                    location = loc.json
            post['loaded_location'] = location

        # Pull data for all users we find in the dump
        users = set()
        users.add(data_dict['profile']['username'])
        for like in data_dict['likes']['media_likes']:
            users.add(like[1])
        for like in data_dict['likes']['comment_likes']:
            users.add(like[1])
        for user in users:
            self.pull_user(self.parsed_data['pulled'], {'user': user})
        
        return data_dict

    def pull_user(self, pulled, args):

        user = args['user']

        if 'users' not in pulled.keys():
            pulled['users'] = {}

        if user not in pulled['users'].keys():
            print("pulling user "+user)
            # TODO user more stable endpoints
            # https://i.instagram.com/api/v1/users/{user_id}/info/  257958069
            ssl._create_default_https_context = ssl._create_unverified_context
            fp = urllib.request.urlopen('https://codeofaninja.com/tools/find-instagram-id-answer.php?instagram_username='+user)
            user_bytes = fp.read()
            user_html = user_bytes.decode("utf8")
            fp.close()

            soup = bs4.BeautifulSoup(user_html, "html.parser")
            divs = soup.findAll("div", recursive=False)
            for div in divs:
                data = div.findAll("div")
                username = data[3].b.text
                if username not in pulled['users'].keys():
                    pulled['users'][username] = {
                        'name': data[4].b.text,
                        'id': data[2].b.text,
                        'picture': data[0].img['src']
                    }

        self.update_data(pulled)

    # TODO add extension scraper
    
    # def add_message(self, pulled, args):
    # check if messages already exists

    # def add_post(self, pulled, args):
    # check if post already exists

    # def add_post_likes(self, pulled, args):
    # check if post exists
    # check if post like already registered


class SnapchatParser(Parser):

    def __init__(self, parsed_data={}, parser_dir=None):
        super(SnapchatParser, self).__init__(parsed_data, parser_dir=parser_dir)

    def parse_upload(self, path):
        data_dict = {}
        path = path+'/json'
        for file in os.listdir(path):
            if file.endswith('.json'):
                filepath = path+'/'+file
                with open(filepath) as fp:
                    data_dict[file.split('.')[0]] = json.load(fp)

        # Geocode data upon ingestion
        for loc in data_dict['location_history']['Locations You Have Visited']:
            latlng = loc['Latitude, Longitude'].split(',')
            loc['lat'] = float(latlng[0].split('\u00b1')[0])
            loc['lng'] = float(latlng[1].split('\u00b1')[0])
            # This is really slow
            loaded = geocoder.osm([loc['lat'], loc['lng']], method='reverse')
            if loaded is not None:
                location = loaded.json
            loc['location'] = location

        return data_dict


class FacebookParser(Parser):

    def __init__(self, parsed_data={}, parser_dir=None):
        super(FacebookParser, self).__init__(parsed_data, parser_dir=parser_dir)

    def parse_upload(self, path):
        data_dict = {}
        rootdir = None
        for root, dirs, files in os.walk(path):
            # Set up inital root if this is the first pass
            if rootdir is None:
                rootdir = root.split('/')[-1]+'/'
                for file in files:
                    if file.endswith('.json'):
                        filepath = root+'/'+file
                        with open(filepath) as fp:
                            data_dict[file.split('.')[0]] = json.load(fp)
                continue
            
            # Create container for these json
            current_dir = root.split(rootdir)[-1].split('/')
            selected = data_dict
            for key in current_dir:
                if key not in selected.keys():
                    selected[key] = {}
                selected =  selected[key]
            
            # Put all json at this level in the container
            for file in files:
                if file.endswith('.json'):
                    filepath = root+'/'+file
                    with open(filepath) as fp:
                        selected[file.split('.')[0]] = json.load(fp)

        return data_dict

    # TODO add extension scraper from data selfie
    
    # def add_profile(self, pulled, args):

    # def add_message(self, pulled, args):
    
    # def add_post(self, pulled, args):







