import socket
import sys
import select
from chat_client import ChatClient
import thread
import Queue
import sys

import rdtp_common

MAX_RECV_LEN = 1024

class BadMessageFormat(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return "The following message was received from the server in bad format: {}.".format(message)

class RDTPClient(ChatClient):
    def __init__(self, host, port):
        ChatClient.__init__(self, host, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = None
        self.session_token = None

        # This is synchronized which is cool since we
        # want to use it across two different threads below
        self.response_queue = Queue.Queue()


    ##################################
    ### Connectivity
    ##################################

    def connect(self):
        self.socket.connect((self.host, self.port))

        # fork thread that will print received messages
        thread.start_new_thread(self.listener, ())

    # Right now, the client only supports two types of actions. 'C' or 'M'
    def listener(self):
        while 1: # listen forever
            action, status, args = rdtp_common.recv(self.socket)
            if action:
                if action == "R": # Response
                    self.response_queue.put((status, args))
                elif action == "M": # Message
                    message = args[0]
                    sys.stdout.write("\n" + message + "\n")
                else:
                    raise BadMessageFormat(message)

    def getNextMessage(self):
        try:
            status, response = self.response_queue.get(block=True, timeout=3)
            return status, response
        except Queue.Empty:
            print 'Server did not respond. Are you connected?'
            return None, None

    def close(self):
        self.socket.close()

    ##################################
    ### Abstract Method Implementation
    ##################################

    def send(self, action_name, *args):
        rdtp_common.send(self.socket, action_name, 0, *args)

    # request is of type () ->
    def request_handler(self, callback, *args):
        self.send(*args)
        status, response = self.getNextMessage()
        return callback(status, response)

    # A request handler that just returns the status of the request
    def status_request_handler(self, *args):
        return self.request_handler(lambda x, _: x, *args)

    # A request handler that just returns the response as an array
    # whatever it is. It also assumes that the status is 0,
    # asserting it.
    def response_request_handler(self, *args):
        return self.request_handler(lambda _, y: y, *args)

    def username_exists(self, username):
        """Check if username already exists.
        Returns boolean."""
        return self.status_request_handler('username_exists', username)

    def create_account(self, username, password):
        """Instructs server to create an account with given username and password."""
        return self.status_request_handler('create_account', username, password)

    def create_group(self, group_id):
        """Instructs server to create an account with some group_id."""
        return self.status_request_handler('create_group', group_id)

    def add_user_to_group(self, username, group_id):
        """Instructs server to add a user to a group."""
        return self.status_request_handler('add_to_group', username, group_id)

    def users_online(self):
        """Returns list of users logged into http-sucks-chat."""
        return self.response_request_handler('users_online')

    def get_users_in_group(self, group):
        """Returns list of users in some group (including possible wildcard characters)."""
        return self.response_request_handler('get_users_in_group', group)

    def send_user(self, user_id, message):
        return self.status_request_handler('send_user', self.session_token, user_id, message)

    def send_group(self, group_id, message):
        return self.status_request_handler('send_group', self.session_token, group_id, message)

    def fetch(self):
        """Fetch new messages from the server."""
        return self.response_request_handler('fetch', self.session_token)

    def login(self, username, password):
        """Login with given username and password.
        Returns boolean."""
        # First logout of current account
        if self.session_token:
            self.logout

        # Login with new account
        # This logic should be moved to chat_client
        self.send('login', username, password)
        status, response = self.getNextMessage()
        if status == 1:
            return False
        elif status == 0:
            self.username = username
            self.session_token = response[0]
            return True

    def logout(self):
        """Logout of http-sucks-chat.
        Returns boolean."""
        if not self.session_token:
            return False
        self.send('logout', self.session_token)
        status, response = self.getNextMessage()
        if status == 1:
            return False
        elif status == 0:
            self.username = None
            self.session_token = None
            return True

