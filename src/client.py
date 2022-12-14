import RPi.GPIO as gpio
import sys
from time import sleep
import threading
import socket
import json
from collections import deque


class Room:
    def __init__(self, config_file_path) -> None:
        try:
            config_file = open(config_file_path)
        except FileNotFoundError:
            sys.stdout.write("Config file path not found\n")
            exit(1)
        self.config = json.load(config_file)
        self.socket = self.connect_server()
        self.initialize_gpio()
        self.alive = True
        self.to_do = deque([])
        self.keep_lamp_on = (False, 0)

    def stop(self):
        self.alive = False
        gpio.cleanup()
        if hasattr(self, "socket"):
            self.socket.close()
        exit()

    def connect_server(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(
                (
                    self.config["ip_servidor_central"],
                    self.config["porta_servidor_central"],
                )
            )
            s.sendall(str(json.dumps(self.config)).encode())
            return s
        except (OSError, ConnectionRefusedError) as error:
            print(f"Failed to connect with server, error: {error}")
            self.stop()

    def initialize_gpio(self):
        try:
            gpio.setwarnings(False)
            gpio.setmode(gpio.BCM)

            output_pins = [(int(obj["gpio"]), int(obj["value"])) for obj in self.config["outputs"]]
            gpio.setup([pin for pin, _ in output_pins], gpio.OUT)

            for pin, value in output_pins:
                gpio.output(pin, value)

            input_pins = [int(obj["gpio"]) for obj in self.config["inputs"]]
            gpio.setup(input_pins, gpio.IN)


        except Exception as error:
            sys.stdout.write(f"Failed to initialize_gpio, error: {error}\n")
            self.stop()
    
    def get_obj_gpio(self, tag, type):
        if type:
            list = []
            for obj in self.config["outputs"]:
                if type.index(obj["type"]):
                    list.append(obj)
            return list
        for obj in self.config["outputs"]:
            if tag == obj["tag"]:
                return obj

    def send_to_server(self):
        string = json.dumps(self.config)
        print("Sending to server")
        print(str(string))
        self.socket.sendall(str(string).encode())

    def send_feedback(self, task, success):
        self.config["feedback_acionamentos"].append(dict(tag=task["tag"], value= 1 if success else 0))
        self.send_to_server()
        self.config["feedback_acionamentos"].clear()

    def read_sensors(self):
        while True and self.alive:
            try:
                task = self.to_do.popleft()
                print(f"Doing this: {task}")
                if task["type"] == "output":
                    try:
                        if task.get("time", False):
                            if task["tag"] == 'lampada':
                                list_obj = self.get_obj_gpio(tag=task["tag"], type=["lampada"])
                                value = int(task["value"])
                                gpio.output([obj["gpio"] for obj in list_obj], value)
                                self.keep_lamp_on = (True, 15)
                                #Falta ver como que vai deixar as lampadas ligadas por esse tempo
                        else:
                            obj = self.get_obj_gpio(tag=task["tag"], type=None)
                            value = int(task["value"])
                            gpio.output(obj["gpio"], value)
                            obj["value"] = task["value"]

                        self.send_feedback(task=task, success=True)
                    except Exception as error:
                        sys.stdout.write(f"Failed to {task}, error: {error}\n")
                        self.send_feedback(task=task, success=False)
                        pass
                elif task["type"] == 'alarm_system':
                    types = ["presenca", "fumaca", "janela", "porta"]
                    #le esses sensores e analisa resultado
                    self.send_feedback(task=task, success=True)
                #string = json.dumps(self.config)
                #print("Sending to server")
                #self.socket.sendall(str(string).encode())
            except IndexError:
                pass
            sleep(0.02)

    def manage_connection(self):
        while True and self.alive:
            data = self.socket.recv(2500)
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
