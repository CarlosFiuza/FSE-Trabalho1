import RPi.GPIO as gpio
import sys
from time import sleep
import threading
import socket
import json
import adafruit_dht
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

            for obj in self.config["outputs"]:
                pin = obj["gpio"]
                gpio.setup(pin, gpio.OUT)
                gpio.output(pin, obj["value"])

            for obj in self.config["inputs"]:
                pin = obj["gpio"]
                gpio.setup(pin, gpio.IN)
                input_val = gpio.input(pin)
                obj["value"] = '1' if input_val else '0'
                if obj["type"] == "contagem":
                    gpio.add_event_detect(pin, gpio.RISING, bouncetime=200)
                else:
                    gpio.add_event_detect(pin, gpio.BOTH)

            self.dht = adafruit_dht.DHT22(self.config["sensor_temperatura"][0]["gpio"])

        except Exception as error:
            sys.stdout.write(f"Failed to initialize_gpio, error: {error}\n")
            self.stop()
    
    def get_obj_gpio(self, tag, type, key):
        if type:
            list = []
            for obj in self.config[key]:
                if type.index(obj["type"]):
                    list.append(obj)
            return list
        for obj in self.config[key]:
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

    def invert_value(self, value):
        if value == "1":
            return "0"
        return "1"

    def read_sensors(self):
        while True and self.alive:
            try:
                task = self.to_do.popleft()
                print(f"Doing this: {task}")
                if task["type"] == "output":
                    try:
                        if task.get("time", False):
                            if task["tag"] == 'lampada':
                                list_obj = self.get_obj_gpio(tag=None, type=["lampada"], key="outputs")
                                value = int(task["value"])
                                gpio.output([obj["gpio"] for obj in list_obj], value)
                                self.keep_lamp_on = (True, 15)
                                #Falta ver como que vai deixar as lampadas ligadas por esse tempo
                        else:
                            obj = self.get_obj_gpio(tag=task["tag"], type=None, key="outputs")
                            value = int(task["value"])
                            gpio.output(obj["gpio"], value)
                            obj["value"] = task["value"]

                        #self.send_feedback(task=task, success=True)
                    except Exception as error:
                        sys.stdout.write(f"Failed to {task}, error: {error}\n")
                        #self.send_feedback(task=task, success=False)
                        pass
                elif task["type"] == 'alarm_system':
                    types = ["presenca", "fumaca", "janela", "porta"]
                    list_obj = self.get_obj_gpio(tag=None, type=types, key="inputs")
                    for obj in list_obj:
                        if obj["value"] == '1':
                         #   self.send_feedback(task=task, success=False)
                            break
                    #self.send_feedback(task=task, success=True)
                elif task["tag"] == "Sensor de Temperatura e Umidade":
                    obj = self.get_obj_gpio(tag=task["tag"], type=None, key="sensor_temperatura")
                    humidity = float(obj["value_hum"])
                    temperature = float(obj["value_temp"])
                    count = 0
                    while count < 15:
                        try:
                            humidity = self.dht.humidity
                            temperature = self.dht.temperature
                        except RuntimeError:
                            sys.stdout.write("Failed to read humidity and temperature, trying again\n")
                            pass
                        count = count + 1
                    obj["value_hum"] = humidity
                    obj["value_temp"] = temperature

                presence = self.get_obj_gpio(tag="Sensor de Presença", type=None, key="inputs")
                if gpio.event_detected(presence["gpio"]):
                    presence["value"] = self.invert_value(presence["value"])
                fumaca = self.get_obj_gpio(tag="Sensor de Fumaça", type=None, key="inputs")
                if gpio.event_detected(fumaca["gpio"]):
                    fumaca["value"] = self.invert_value(fumaca["value"])
                janela = self.get_obj_gpio(tag="Sensor de Janela", type=None, key="inputs")
                if gpio.event_detected(janela["gpio"]):
                    janela["value"] = self.invert_value(janela["value"])
                porta = self.get_obj_gpio(tag="Sensor de Porta", type=None, key="inputs")
                if gpio.event_detected(porta["gpio"]):
                    porta["value"] = self.invert_value(porta["value"])

                contagem_up = self.get_obj_gpio(tag="Sensor de Contagem de Pessoas Entrada", type=None, key="inputs")
                if gpio.event_detected(contagem_up["gpio"]):
                    contagem_up["value"] = self.invert_value(contagem_up["value"])
                    self.config["num_pessoas"] = int(self.config["num_pessoas"]) + 1
                contagem_down = self.get_obj_gpio(tag="Sensor de Contagem de Pessoas Saida", type=None, key="inputs")
                if gpio.event_detected(contagem_down["gpio"]):
                    contagem_down["value"] = self.invert_value(contagem_down["value"])
                    self.config["num_pessoas"] = int(self.config["num_pessoas"]) - 1

                self.send_to_server()

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
