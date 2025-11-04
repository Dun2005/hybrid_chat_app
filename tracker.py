#intergrated in backend

import socket
from threading import Thread

class Tracker:
    def __init__(self, HOST, PORT):
        self.peer_list = {}
        
    def reg_peer(self, name, addr, port):
        if name not in self.peer_list:
            self.peer_list[name] = addr + ":" + str(port)
            print("[Tracker]Added user {}  with address {}".format(name, self.peer_list[name]))
            return True
        else:
            print("[Tracker]User name {} existed".format(name))
            return False

    def get_list(self):
        return self.peer_list

    