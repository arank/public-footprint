from abc import ABC, abstractmethod
import uuid 

# TODO figure out better data storage than in memory JSON
class App(ABC):
    def __init__(self, data):
        super().__init__()
        self.uuid = str(uuid.uuid1())
        self.data = data

    def main(self):
        print("Please do NOT override main. This is RESERVED")

from datetime import datetime

class DataGram(App):
    def __init__(self, data):
        super(DataGram, self).__init__(data)

    # TODO this is a hack to view all data each app has access to
    def all(self, args):
        return self.data      

    def posts(self, args):
        data =  self.data
        posts = []
        for post in data['instagram']['upload']['media']['stories']:
            posts.append(post)

        for post in data['instagram']['upload']['media']['photos']:
            posts.append(post)

        for post in data['instagram']['upload']['media']['videos']:
            posts.append(post)
       
        return posts

    def likes(self, args):
        data =  self.data
        likes = []
        for like in data['instagram']['upload']['likes']['media_likes']:
            like.append('POST')
            likes.append(like)

        for like in data['instagram']['upload']['likes']['comment_likes']:
            like.append('COMMENT')
            likes.append(like)
        
        # Attach user info
        for like in likes:
            like.append(self.user({'user': like[1]}))

        return likes

    def messages(self, args):
        data = self.data
        # TODO user info load in loader
        
        messages = []
        for message in data['instagram']['upload']['messages']:
            # Attach user info
            message['users'] = []
            for user in message['participants']:
                message['users'].append(self.user({'user': user}))
            messages.append(message)

        return messages

    def comments(self, args):
        data = self.data
        # TODO user info load in loader

        comments = []
        for comment in data['instagram']['upload']['comments']['media_comments']:
            comment.append('POST')
            comments.append(comment)

        for comment in data['instagram']['upload']['comments']['live_comments']:
            comment.append('LIVE')
            comments.append(comment)
        
        # Attach user info
        for comment in comments:
            comment.append(self.user({'user': comment[2]}))

        return comments

    def follows(self, args):
        data = self.data['instagram']['upload']['connections']
        follows = {
            'followers': [[k, v] for k, v in data['followers'].items()],
            'follow_requests': [[k, v] for k, v in data['follow_requests_sent'].items()],
            'following': [[k, v] for k, v in data['following'].items()],
            'following_hashtags': [[k, v] for k, v in data['following_hashtags'].items()],
            'blocked': [[k, v] for k, v in data['blocked_users'].items()]
        }
        # TODO attach user info & load in loader
        return follows

    def searches(self, args):
        data = self.data
        # TODO attach user info & load in loader
        return data['instagram']['upload']['searches']

    def user(self, args):
        data =  self.data
        user = args['user']
        # If this user doesn't exist/is deleted throw up empty
        if user not in data['instagram']['pulled']['users'].keys():
            return {'name': None,'id': None,'picture': "https://scontent-sjc3-1.xx.fbcdn.net/v/t1.0-1/c94.0.320.320/p320x320/10645251_10150004552801937_4553731092814901385_n.jpg?_nc_cat=1&_nc_ht=scontent-sjc3-1.xx&oh=1b5788a7c0f27062cc676f926761f99e&oe=5C70B7BD"}
        
        return data['instagram']['pulled']['users'][user]

    def main_user(self, args):
        data = self.data
        return data['instagram']['upload']['profile']


class FacebookSelfie(App):
    def __init__(self, data):
        super(FacebookSelfie, self).__init__(data)    
    
    # TODO this is a hack to view all data each app has access to
    def all(self, args):
        return self.data['facebook']['upload']

    def friends(self, args):
        data =  self.data
        # TODO handle multiple address books and figure out what this data is because FB sucks it up
        # friend_list = data['facebook']['upload']['about_you']['your_address_books']['address_book']['address_book']
        return data['facebook']['upload']['friends']['friends']['friends']

    def friending_actions(self, args):
        data =  self.data
        actions = {} 
        actions['sent_requests'] = data['facebook']['upload']['friends']['sent_friend_requests']['sent_requests']
        actions['rejected_requests'] = data['facebook']['upload']['friends']['rejected_friend_requests']['rejected_requests']        
        actions['deleted_friends'] = data['facebook']['upload']['friends']['removed_friends']['deleted_friends']        
        return actions

    def chats(self, args):
        data =  self.data
        return data['facebook']['upload']['messages']
 
    def messages(self, args):
        data =  self.data
        ret = []
        for thread in data['facebook']['upload']['messages'].keys():
            if 'message' not in data['facebook']['upload']['messages'][thread].keys():
                continue
            
            for message in data['facebook']['upload']['messages'][thread]['message']['messages']:
                message['timestamp'] = message['timestamp_ms']/1000
                message['chat_id'] = thread
                ret.append(message)
        
        return ret

    def apps(self, args):
        data =  self.data
        app_data =  data['facebook']['upload']['apps_and_websites']['apps_and_websites']['installed_apps']
        for app in app_data:
            app['timestamp'] = app['added_timestamp']
        return app_data

    def likes(self, args):
        data =  self.data
        ret = {}
        ret['external_likes'] = data['facebook']['upload']['likes_and_reactions']['likes_on_external_sites']['other_likes']
        ret['page_likes'] = data['facebook']['upload']['likes_and_reactions']['pages']['page_likes']
        ret['post_likes'] = data['facebook']['upload']['likes_and_reactions']['posts_and_comments']['reactions']
        return ret
        
    def comments(self, args):
        data =  self.data
        ret = {}
        ret['comments'] = data['facebook']['upload']['comments']['comments']['comments']
        ret['group_comments'] = data['facebook']['upload']['groups']['your_posts_and_comments_in_groups']['group_posts']
        return ret

    def searches(self, args):
        data =  self.data
        return data['facebook']['upload']['search_history']['your_search_history']['searches']

    def posts(self, args):
        data =  self.data
        return data['facebook']['upload']['posts']['your_posts']['status_updates']

    def posts_on_my_timeline(self, args):
        data =  self.data
        return data['facebook']['upload']['posts']["other_people's_posts_to_your_timeline"]['wall_posts_sent_to_you']

    def groups(self, args):
        data = self.data
        return data['facebook']['upload']['groups']['your_group_membership_activity']['groups_joined']

    def pokes(self, args):
        data = self.data
        return data['facebook']['upload']['other_activity']['pokes']['pokes']

    def follows(self, args):
        data =  self.data
        ret = {}
        ret['people'] = data['facebook']['upload']['following_and_followers']['following']['following']
        ret['pages'] = data['facebook']['upload']['following_and_followers']['followed_pages']['pages_followed']
        return ret

    def logins(self, args):
        data =  self.data
        ret = {}
        ret['activity'] = data['facebook']['upload']['security_and_login_information']['account_activity']['account_activity']
        ret['logins'] = data['facebook']['upload']['security_and_login_information']['logins_and_logouts']['account_accesses']
        ret['ips'] = data['facebook']['upload']['security_and_login_information']['login_protection_data']['login_protection_data']
        return ret

    def profile_updates(self, args):
        data =  self.data
        return data['facebook']['upload']['profile_information']['profile_update_history']['profile_updates']

    def ad_profile(self, args):
        data =  self.data
        ret = {}
        ret['peer_category'] = data['facebook']['upload']['about_you']['friend_peer_group']
        ret['profile_information'] =  data['facebook']['upload']['profile_information']['profile_information']
        ret['ad_interests'] = data['facebook']['upload']['ads']['ads_interests']
        ret['ad_targeted_by'] = data['facebook']['upload']['ads']['advertisers_who_uploaded_a_contact_list_with_your_information']
        return ret

    def ad_interactions(self, args):
        data =  self.data
        return data['facebook']['upload']['ads']["advertisers_you've_interacted_with"]['history']


class UberTracks(App):
    def __init__(self, data):
        super(UberTracks, self).__init__(data)

    # TODO this is a hack to view all data each app has access to
    def all(self, args):
        return self.data

    # Serve additional endpoints here
    def trips(self, args):
        data =  self.data
        # time_from = args['from']
        # time_to = args['to']

        trips = []
        for trip_id in data['uber']['pulled']['trips'].keys():
            trip_data = {}
            trip = data['uber']['pulled']['trips'][trip_id]
            trip_data['status'] = trip['status']
            trip_data['fare'] = trip['clientFare']
            trip_data['currency'] = trip['currencyCode']
            trip_data['surge'] = trip['isSurgeTrip']
            trip_data['start_time'] = trip['requestTime']
            trip_data['end_time'] =  trip['dropoffTime']

            # Pull trips in range
            start = datetime.strptime(trip['requestTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
            end = datetime.strptime(trip['dropoffTime'], "%Y-%m-%dT%H:%M:%S.%fZ")

            # Add geo-data to trips
            trip_data['start_address'] = trip['begintripFormattedAddress']
            trip_data['end_address'] = trip['dropoffFormattedAddress']
            # trip_data['start_location'] = trip['begintripLocation']
            # trip_data['end_location'] = trip['dropoffLocation']

            # TODO move to loader
            import geocoder
            loc = geocoder.osm(trip['begintripFormattedAddress'])
            if loc is not None:
                location = loc.json
                trip_data['start_location'] = location
            else:
                continue
            loc = geocoder.osm(trip['dropoffFormattedAddress'])
            if loc is not None:
                location = loc.json
                trip_data['end_location'] = location
            else:
                continue

            trips.append(trip_data)

        # return pulled_trips
        return {'total_trips': data['uber']['pulled']['total_trips'], 'trips':trips}


class VenmoTrail(App):
    def __init__(self, data):
        super(VenmoTrail, self).__init__(data)

    # TODO this is a hack to view all data each app has access to
    def all(self, args):
        return self.data

    # Unpack list of transactions by user
    def transactions(self, args):
        data =  self.data
        user = args['user']

        txns = data['venmo']['pulled']['transactions']
        pulled_txns = []
        for txn_id in txns.keys():
            txn = txns[txn_id]
            txn_time = datetime.strptime(txn['created_time'], "%Y-%m-%dT%H:%M:%SZ")

            if txn['actor']['username'] == user:
                pulled_txns.append(txn)
                continue

            for payment in txn['transactions']:
                if payment['target']['username'] == user:
                    pulled_txns.append(txn)
                    continue       

        return pulled_txns

    # Get the users seen from list of loaded transactions
    def users(self, args):
        data =  self.data
        txns = data['venmo']['pulled']['transactions']
        pulled_users = {}
        for txn_id in txns.keys():
            txn = txns[txn_id]

            if txn['actor']['username'] not in pulled_users.keys():
                pulled_users[txn['actor']['username']] = txn['actor']

            for payment in txn['transactions']:
                if payment['target']['username'] not in pulled_users.keys():
                    pulled_users[payment['target']['username']] = payment['target']
                     
        return pulled_users

    def main_user(self, args):
        data =  self.data

        # TODO remove
        if 'main_user' not in data['venmo']['pulled'].keys(): 
            data['venmo']['pulled']['main_user'] = 'Gita-Bhattacharya'

        all_users = self.users({})
        for user in all_users.keys():
            if all_users[user]['username'] == data['venmo']['pulled']['main_user']:
                return all_users[user]

    def social_graph(self, args):
        data =  self.data
        return data['venmo']['pulled']['social_graph']


class SnapDataLens(App):
    # Snap ghost for profile
    # https://assets.b9.com.br/wp-content/uploads/2015/07/snapchat-logo-thumbnail.jpg

    def __init__(self, data):
        super(SnapDataLens, self).__init__(data)

    # TODO this is a hack to view all data each app has access to
    def all(self, args):
        return self.data

    def main_user(self, args):
        data = self.data
        ret = {}
        ret['account'] = data['snapchat']['upload']['account']
        ret['account_history'] = data['snapchat']['upload']['account_history']
        return ret

    def chats(self, args):
        data = self.data
        ret = []
        for i in data['snapchat']['upload']['snap_history']['Received Snap History']:
            i['type'] = 'SNAP'
            # ret['recieved'].append(i)
            ret.append(i)

        for i in data['snapchat']['upload']['chat_history']['Received Chat History']:
            i['type'] = 'CHAT'
            # ret['recieved'].append(i)            
            ret.append(i)

        for i in data['snapchat']['upload']['snap_history']['Sent Snap History']:
            i['type'] = 'SNAP'
            # ret['sent'].append(i)        
            ret.append(i)

        for i in data['snapchat']['upload']['chat_history']['Sent Chat History']:
            i['type'] = 'CHAT'
            # ret['sent'].append(i)  
            ret.append(i)

        return ret

    def locations(self, args):
        data = self.data
        return data['snapchat']['upload']['location_history']['Locations You Have Visited']

    def ad_profile(self, args):
        data = self.data
        ret = {}
        ret['content_interest'] = data['snapchat']['upload']['ranking']['Content Interests']
        ret['category_interest'] = data['snapchat']['upload']['user_profile']['Interest Categories']
        ret['ad_interactions'] = data['snapchat']['upload']['user_profile']['Ads You Interacted With']
        return ret   
