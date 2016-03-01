import socket
import sys
import select
from chat_client import ChatClient
import thread
from Queue import Queue
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
        self.messageQ = Queue()


    ##################################
    ### Connectivity
    ##################################

    def connect(self):
        self.socket.connect((self.host, self.port))

        # fork thread that will print received messages
        #thread.start_new_thread(self.listener, ())

    # Right now, the client only supports two types of actions. 'C' or 'M'
    def listener(self):
        while 1: # listen forever
            message = self.rdtp_recv()
            if message:
                if message[0] == "C": # Command
                    self.messageQ.put(message[1:])
                elif message[0] == "M": # Message
                    sys.stdout.write("\nNEW MESSAGE RECEIVED: " + message[1:] + "\n> ")
                else:
                    raise BadMessageFormat(message)

    def getNextMessage(self):
        while 1: # block until we recieve something on the messageQ
            if not self.messageQ.empty():
                return self.messageQ.get()

    def close(self):
        self.socket.close()

    ##################################
    ### Abstract Method Implementation
    ##################################

    def send(self, action_name, *args):
        rdtp_common.send(self.socket, action_name, ':'.join(args))

    def username_exists(self, username):
        """Check if username already exists.
        Returns boolean."""

        self.send('username_exists',  username)
        response = self.getNextMessage()

        return response == '1'

    def create_account(self, username, password):
        """Instructs server to create an account with given username and password."""
        self.send('create_account', username, password)
        response = self.getNextMessage()
        return response == '1'


    def create_group(self, group_id):
        """Instructs server to create an account with some group_id."""
        self.send('create_group', group_id)
        response = self.getNextMessage()
        return response == '1'

    def add_user_to_group(self, username, group_id):
        """Instructs server to add a user to a group."""
        self.send('add_to_group', username, group_id)
        response = self.getNextMessage()
        return response == '1'

    def login(self, username, password):
        """Login with given username and password.
        Returns boolean."""
        # First logout of current account
        if self.session_token:
            self.logout

        # Login with new account
        # This logic should be moved to chat_client
        self.send('login', username, password)
        response = self.getNextMessage()
        if response == "0":
            return False
        else:
            self.username = username
            self.session_token = response
            return True

    def logout(self):
        """Logout of http-sucks-chat.
        Returns boolean."""
        if not self.session_token:
            return False
        self.send('logout', self.session_token)
        response = self.getNextMessage()
        if response == "0":
            return False
        else:
            self.username = None
            self.session_token = None
            return True

    def users_online(self):
        """Returns list of users logged into http-sucks-chat."""
        self.send('users_online')
        response = self.getNextMessage()
        if response == "0":
            return []
        return response.split(':')

    def get_users_in_group(self, group):
        """Returns list of users in some group (including possible wildcard characters)."""
        self.send('get_users_in_group', group)
        response = self.recv()
        if response == '0':
            return []
        return response.split(':')

    def send_user(self, user_id, message):
        self.send('send_user', self.session_token, user_id, message)
        response = self.getNextMessage()
        if response == "0":
            print "Your session has expired."
        elif response == "2":
            print "Could not send message to " + user_id + "."

    def send_group(self, group_id, message):
        self.send('send_group', self.session_token, group_id, message)
        response = self.recv()
        if response == "0":
            print "Your session has expired."
        elif response == "1":
            print "Could not send message to group " + group_id + "."

    def fetch(self):
        """Fetch new messages from the server."""
        self.send('fetch', self.session_token)
        return self.recv()

    def sendToGroup(self, group_id, message):
        try:
            self.send('send:' + group_id + ':' + message)
        except:
            print "Couldn't send message. Assuming server disconnected."
            self.close()
