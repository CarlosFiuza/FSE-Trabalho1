import sys
from time import sleep
import threading
import socket
import json
from collections import deque

class Room:
    def __init__(self, config_file_path) -> None:
        config_file = open(config_file_path)
        self.config = json.load(config_file)
        self.socket = self.connect_server()
        self.initialize_gpio()
        self.alive = True
        self.to_do = deque([])

    def stop(self):
        self.alive = False
        self.socket.close()
        exit()

    def connect_server(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.config["ip_servidor_central"], self.config["porta_servidor_central"]))
            return s
        except:
            print("Failed to connect with server")
            self.stop()

    def initialize_gpio(self):
        print("Initialize gpio")

    def read_sensors(self):
        while True and self.alive:
            try:
                task = self.to_do.popleft()
                print(f"Doing this: {task}")
                string = json.dumps(self.config)
                self.socket.sendall(str(string).encode())
            except IndexError:
                pass
            sleep(0.2)


    def manage_connection(self):
        while True and self.alive:
            data = self.socket.recv(2000)
            message = json.loads(data)
            self.to_do.append(message)

    def run(self):
        try:
            thread_read_sensors = threading.Thread(target=self.read_sensors)
            thread_read_sensors.start()

            self.manage_connection()
        except:
            print("Failed run")
            self.stop()

try:
    if len(sys.argv) != 2:
        print("Missing config_file_path in argv")
        exit()
    room = Room(sys.argv[1])
    room.run()
except KeyboardInterrupt:
    exit()