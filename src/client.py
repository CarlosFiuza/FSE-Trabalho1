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
        self.keep_lamp_on_sec = 0
        self.count_lam_on = 0
        self.special_commands = [
            "room lamps",
            "all lamps",
            "room outputs",
            "all outputs",
        ]

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
                obj["value"] = "1" if input_val else "0"
                if obj["type"] == "contagem":
                    gpio.add_event_detect(pin, gpio.RISING, bouncetime=200)
                else:
                    gpio.add_event_detect(pin, gpio.BOTH)

            self.dht = adafruit_dht.DHT22(self.config["sensor_temperatura"][0]["gpio"])

        except Exception as error:
            sys.stdout.write(f"Failed to initialize_gpio, error: {error}\n")
            self.stop()

    def get_obj_gpio(self, tag, typeof, key):
        if typeof and isinstance(typeof, list):
            array = []
            for obj in self.config[key]:
                try:
                    if obj["type"] in typeof:
                        array.append(obj)
                except Exception:
                    pass
            return array
        for obj in self.config[key]:
            if tag == obj["tag"]:
                return obj

    def send_to_server(self):
        string = json.dumps(self.config)
        try:
            self.socket.sendall(str(string + "\n").encode())
        except (BrokenPipeError, ConnectionResetError) as error:
            sys.stdout.write(f"Failed to send_to_server, error: {error}\n")
            sys.stdout.write("exiting...\n")
            self.stop()

    def send_feedback(self, task, success):
        self.config["feedback_acionamentos"].append(
            dict(
                tag=task["tag"],
                success=1 if success else 0,
                value=1 if task["value"] == "1" or task["value"] == 1 else 0,
            )
        )
        self.send_to_server()
        self.config["feedback_acionamentos"].clear()

    def invert_value(self, value):
        if value == "1":
            return "0"
        return "1"

    def read_sensors(self):
        while True and self.alive:
            if self.keep_lamp_on_sec > 0 and self.count_lam_on >= self.keep_lamp_on_sec:
                list_obj = self.get_obj_gpio(
                    tag=None, typeof=["lampada"], key="outputs"
                )
                for obj in list_obj:
                    gpio.output(obj["gpio"], 0)
                    obj["value"] = 0
                self.keep_lamp_on_sec = 0
                self.count_lam_on = 0

            try:
                task = self.to_do.popleft()

                if task["type"] in self.special_commands:
                    value = int(task["value"])
                    if task["type"] in ["room lamps", "all lamps"]:
                        list_obj = self.get_obj_gpio(
                            tag=None, typeof=["lampada"], key="outputs"
                        )
                    else:
                        list_obj = self.get_obj_gpio(
                            tag=None,
                            typeof=["lampada", "projetor", "ar-condicionado"],
                            key="outputs",
                        )
                    value = int(task["value"])
                    for obj in list_obj:
                        gpio.output(obj["gpio"], value)
                        obj["value"] = value
                    self.send_feedback(task=task, success=True)

                if task["type"] == "output":
                    try:
                        if "time" in task:
                            if task["tag"] == "lampada":
                                list_obj = self.get_obj_gpio(
                                    tag=None, typeof=["lampada"], key="outputs"
                                )
                                for obj in list_obj:
                                    gpio.output(obj["gpio"], 1)
                                    obj["value"] = 1

                                self.keep_lamp_on_sec = 15
                        else:
                            obj = self.get_obj_gpio(
                                tag=task["tag"], typeof=None, key="outputs"
                            )
                            value = int(task["value"])
                            gpio.output(obj["gpio"], value)
                            obj["value"] = task["value"]

                        self.send_feedback(task=task, success=True)
                    except Exception as error:
                        sys.stdout.write(f"Failed to {task}, error: {error}\n")
                        self.send_feedback(task=task, success=False)
                        pass
                elif task["type"] == "alarm_system":
                    types = ["presenca", "fumaca", "janela", "porta"]
                    list_obj = self.get_obj_gpio(tag=None, typeof=types, key="inputs")
                    for obj in list_obj:
                        if obj["value"] == "1":
                            self.send_feedback(task=task, success=False)
                            break
                    self.send_feedback(task=task, success=True)
                elif task["tag"] == "Sensor de Temperatura e Umidade":
                    obj = self.get_obj_gpio(
                        tag=task["tag"], typeof=None, key="sensor_temperatura"
                    )
                    try:
                        humidity = float(obj["value_hum"])
                        temperature = float(obj["value_temp"])
                    except TypeError:
                        humidity = 0.0
                        temperature = 0.0
                        pass
                    count = 0
                    while count < 15:
                        try:
                            humidity = self.dht.humidity
                            temperature = self.dht.temperature
                            break
                        except (RuntimeError, OverflowError):
                            # sys.stdout.write(
                            #     "Failed to read humidity and temperature, trying again\n"
                            # )
                            pass
                        count = count + 1
                    obj["value_hum"] = humidity
                    obj["value_temp"] = temperature

                if self.keep_lamp_on_sec > 0:
                    self.count_lam_on = self.count_lam_on + 0.02
                sleep(0.02)

            except IndexError:
                presence = self.get_obj_gpio(
                    tag="Sensor de Presença", typeof=None, key="inputs"
                )
                if gpio.event_detected(presence["gpio"]):
                    presence["value"] = self.invert_value(presence["value"])
                fumaca = self.get_obj_gpio(
                    tag="Sensor de Fumaça", typeof=None, key="inputs"
                )
                if gpio.event_detected(fumaca["gpio"]):
                    fumaca["value"] = self.invert_value(fumaca["value"])
                janela = self.get_obj_gpio(
                    tag="Sensor de Janela", typeof=None, key="inputs"
                )
                if gpio.event_detected(janela["gpio"]):
                    janela["value"] = self.invert_value(janela["value"])
                porta = self.get_obj_gpio(
                    tag="Sensor de Porta", typeof=None, key="inputs"
                )
                if gpio.event_detected(porta["gpio"]):
                    porta["value"] = self.invert_value(porta["value"])

                contagem_up = self.get_obj_gpio(
                    tag="Sensor de Contagem de Pessoas Entrada",
                    typeof=None,
                    key="inputs",
                )
                if gpio.event_detected(contagem_up["gpio"]):
                    contagem_up["value"] = self.invert_value(contagem_up["value"])
                    self.config["num_pessoas"] = int(self.config["num_pessoas"]) + 1
                contagem_down = self.get_obj_gpio(
                    tag="Sensor de Contagem de Pessoas Saida", typeof=None, key="inputs"
                )
                if gpio.event_detected(contagem_down["gpio"]):
                    contagem_down["value"] = self.invert_value(contagem_down["value"])
                    self.config["num_pessoas"] = int(self.config["num_pessoas"]) - 1

                self.send_to_server()

                if self.keep_lamp_on_sec > 0:
                    self.count_lam_on = self.count_lam_on + 2
                sleep(2)

    def manage_connection(self):
        try:
            while True and self.alive:
                data = self.socket.recv(2500)
                if data:
                    aux = data.decode()
                    data = aux.split("*")
                    try:
                        for jsn in data:
                            if jsn and jsn != "":
                                message = json.loads(jsn)
                                self.to_do.append(message)
                    except json.decoder.JSONDecodeError as error:
                        # sys.stdout.write(f"JSONDecodeError, error: {error}\n")
                        pass
        except ConnectionResetError as error:
            sys.stdout.write(f"Failed to service_connection, error: {error}\n")
            self.stop()

    def run(self):
        try:
            thread_read_sensors = threading.Thread(target=self.read_sensors)
            thread_read_sensors.start()

            self.manage_connection()
        except Exception as error:
            sys.stdout.write(f"Failed to run, error: {error}\n")
            self.stop()


try:
    if len(sys.argv) != 2:
        print("Missing config_file_path in argv")
        exit()
    room = Room(sys.argv[1])
    sleep(0.5)
    room.run()
except KeyboardInterrupt:
    exit()
