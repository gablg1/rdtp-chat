from chat.chat_client import ChatClient
from functools import wraps
import requests
import sys

def check_session(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if args[0].session is None:
            print "No current session. Please, login to perform this action."
            return 1

        return f(*args, **kwargs)
    return wrapper

class RESTClient(ChatClient):
    def __init__(self, host, port):
        ChatClient.__init__(self, host, port)
        self.username = None
        self.session = None
        self.base_url = 'http://' + host + ':' + str(port)

    ###########
    ## USERS ##
    ###########

    def create_account(self, username, password):
        """Instructs server to create an account with given username and password."""
        credentials = {'username': username, 'password': password}

        response = requests.post(self.base_url + '/users', json=credentials)
        r = response.json()

        if 'errors' in r:
            return self.__handle_error(r)

        return 0

    def login(self, username, password):
        """Login with given username and password.
        Returns boolean."""
        # First logout of current account
        if self.session is not None:
            self.logout

        self.session = requests.Session()

        # Login with new account
        self.session.auth = (username, password)
        response = self.session.post(self.base_url + '/login')
        r = response.json()

        if 'errors' in r:
            return self.__handle_error(r)

        try:
            self.username = r['data']['user']['username']
            self.session.auth = ('TOK', r['data']['user']['session_token'])
        except:
            return 1

        return 0

    @check_session
    def logout(self):
        """Logout of http-sucks-chat.
        Returns boolean."""
        if self.session is None:
            return 1

        response = self.session.post(self.base_url + '/logout')
        r = response.json()

        if 'errors' in r:
            return self.__handle_error(r)

        self.username = None
        self.session_token = None

        return 0

    @check_session
    def delete_account(self):
        response = self.session.delete(self.base_url + '/users/' + self.username)
        r = response.json()

        if 'errors' in r:
            return self.__handle_error(r)

        return 0

    @check_session
    def send_user(self, username, message):
        msg = {'data': {'message': message}}
        response = self.session.post(self.base_url + '/users/' + username + '/messages', json=msg)
        r = response.json()

        if 'errors' in r:
            return self.__handle_error(r)

        return 0

    @check_session
    def fetch(self):
        """Fetch new messages from the server."""
        response = self.session.get(self.base_url + '/users/' + self.username + '/messages')
        r = response.json()

        if 'errors' in r:
            return self.__handle_error(r)

        messages = r['data']['messages']

        if messages == []:
            return "No new messages."

        try:
            ret = []
            for msg in messages:
                if msg['from_group_name'] is None:
                    ret.append(msg['from_username'] + ' >>> ' + msg['message'])
                else:
                    ret.append(msg['from_username'] + ' @ ' + msg['from_group_name'] + ' >>> ' + msg['message'])
        except:
            return 2

        return '\n'.join(ret)

    ############
    ## GROUPS ##
    ############

    @check_session
    def create_group(self, group_name):
        """Instructs server to create an account with some group_id."""
        data = {'data': {'group_name': group_name}}
        response = self.session.post(self.base_url + '/groups', json=data)
        r = response.json()

        if 'errors' in r:
            return self.__handle_error(r)

        return 0

    @check_session
    def add_user_to_group(self, username, group_name):
        """Instructs server to add a user to a group."""
        data = {'data': {'username': username}}
        response = self.session.post(self.base_url + '/groups/' + group_name + '/users', json=data)
        r = response.json()

        if 'errors' in r:
            return self.__handle_error(r)

        return 0

    @check_session
    def send_group(self, group_name, message):
        msg = {'data': {'message': message}}
        response = self.session.post(self.base_url + '/groups/' + group_name + '/messages', json=msg)
        r = response.json()

        if 'errors' in r:
            return self.__handle_error(r)

        return 0

    @check_session
    def get_groups(self, wildcard):
        wildcard = {'wildcard': wildcard}
        response = self.session.get(self.base_url + '/groups', params=wildcard)
        r = response.json()

        if 'errors' in r:
            return self.__handle_error(r)

        try:
            groups = r['data']['groups']
        except:
            return 2

        return '\n'.join(groups)

    @check_session
    def get_users(self, wildcard):
        wildcard = {'wildcard': wildcard}
        response = self.session.get(self.base_url + '/users', params=wildcard)
        r = response.json()

        if 'errors' in r:
            return self.__handle_error(r)

        try:
            users = r['data']['users']
        except:
            return 2

        return '\n'.join(users)

    ############
    ## HELPER ##
    ############
    def __handle_error(self, r):
        try:
            status_code = r['errors']['status_code']
        except:
            return 2

        if status_code == 401:
            return 1

        # 200 here means a conflict: create_group or create_account
        if status_code == 200:
            return 2

        return 2

