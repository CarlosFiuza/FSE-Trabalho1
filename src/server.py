import sys
import socket
import selectors
import types
import json
import threading
import csv
import signal
from colorama import Fore, Style
from time import sleep
from os import system
from datetime import datetime

rooms = {
    "164.41.98.16/13508": "Sala 1",
    "164.41.98.26/13508": "Sala 2",
    "164.41.98.28/13508": "Sala 3",
    "164.41.98.15/13508": "Sala 4",
}


class Display:
    def __init__(self) -> None:
        self.rooms = {}

    def reset_style(_):
        sys.stdout.write(Style.RESET_ALL)

    def message_error(self, message):
        self.reset_style()
        sys.stdout.write(f"{Fore.RED}{message}")

    def message_server(self, message):
        self.reset_style()
        sys.stdout.write(f"{Fore.YELLOW}{message}")

    def message_room(self, message):
        self.reset_style()
        sys.stdout.write(f"{Fore.GREEN}{message}")

    def set_room(self, key, value):
        self.rooms[key] = value

    def alarm_system(self, is_alarm_system_on):
        message = "ligado" if is_alarm_system_on else "desligado"
        self.reset_style()
        sys.stdout.write(f"{Fore.CYAN}Sistema de alarme: {message}\n")

    def inputs(self, input):
        self.reset_style()
        sys.stdout.write(f"\n {Fore.CYAN}Status of inputs:\n")
        for obj in input:
            tag = obj["tag"]
            value = "desligado" if int(obj["value"]) == 0 else "ligado"
            sys.stdout.write(f"| {tag}: {value}\n")
            sys.stdout.write("|----------------------------\n")

    def outputs(self, output):
        self.reset_style()
        sys.stdout.write(f"\n {Fore.CYAN}Status of outputs:\n")
        for obj in output:
            tag = obj["tag"]
            value = "desligado" if int(obj["value"]) == 0 else "ligado"
            sys.stdout.write(f"| {tag}: {value}\n")
            sys.stdout.write("|----------------------------\n")

    def temp(self, obj):
        temp = obj["value_temp"]
        hum = obj["value_hum"]
        self.reset_style()
        sys.stdout.write(
            f"\n{Fore.CYAN}Valor da temperatura e umidade: {temp}°C {hum}%\n"
        )
        sys.stdout.write("----------------------------\n")

    def show_available_rooms(self):
        count = 1
        for key in self.rooms.keys():
            sys.stdout.write(f"   {count} - {key}\n")
            count = count + 1

    def show_number_persons(self, show_all, key):
        try:
            count = 0
            self.reset_style()
            if show_all:
                for room in self.rooms.values():
                    count = count + int(room["num_pessoas"])
                sys.stdout.write(
                    f"{Fore.MAGENTA}Número de pessoas no prédio: {count}\n"
                )
            else:
                sys.stdout.write(
                    f"{Fore.MAGENTA}Número de pessoas na sala: {self.rooms[key]['num_pessoas']}\n"
                )
        except:
            print("HEHEHEH")

    def show(self, idx):
        i = 1
        for key, room in self.rooms.items():
            if i == idx:
                value = room
                self.reset_style()
                sys.stdout.write(f"{Fore.CYAN}{key}\n")
                self.show_number_persons(show_all=False, key=key)
                self.inputs(value["inputs"])
                self.outputs(value["outputs"])
                self.temp(value["sensor_temperatura"][0])
                return
            i = i + 1
        self.message_error("Wrong function Display.show behavior\n")


class Logger:
    def __init__(self) -> None:
        try:
            self.file = open("logs.csv", "x")
        except FileExistsError:
            self.file = open("logs.csv", "w")
            pass
        self.header = ["action", "datetime"]
        self.writer = csv.writer(self.file)
        self.writer.writerow(self.header)

    def write_row(self, action):
        dt_string = datetime.now()
        row = [str(action), dt_string]
        self.writer.writerow(row)

    def close_file(self):
        self.file.close()


class Server:
    def __init__(self, ip_addr, port) -> None:
        try:
            self.host = ip_addr
            self.port = port
            self.display = Display()
            self.lsock = self.create_server_socket()
            self.sel = selectors.SelectSelector()
            self.sel.register(self.lsock, selectors.EVENT_READ, data=None)
            self.logger = Logger()
            self.num_rooms = 0
            self.alive = True
            self.alarm_system_on = False
            self.alarm_ring_on = False
            self.socketRoom = {}
        except Exception as error:
            self.display.message_error(f"Failed do create server, error: {error}\n")
            exit(1)

    def create_server_socket(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((self.host, self.port))
            s.listen()
            self.display.message_server(f"Listening on {(self.host, self.port)}\n")
            s.setblocking(False)
            return s
        except OSError as error:
            self.display.message_error(f"Failed do create socker, error: {error}\n")
            exit(1)

    def signal_int_handler(self, signum, stack_frame):
        self.display.message_server(f"\nCtrl-C pressed, exiting\n")
        self.alive = False
        self.logger.close_file()
        self.sel.close()
        self.lsock.close()
        exit(1)

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()
        self.display.message_server(f"Accepted connection from {addr}\n")
        conn.setblocking(False)
        data = types.SimpleNamespace(
            addr=addr, room="", json_in="", json_out=b"", keep_lamps_on=False
        )
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(conn, events, data=data)
        self.num_rooms = self.num_rooms + 1

    def subscribe_message_to_rooms(self, message, all_rooms, room):
        if not all_rooms:
            self.socketRoom[room].data.json_out += f"{message}*".encode()
            return
        for sock in self.socketRoom.values():
            if sock:
                sock.data.json_out += f"{message}*".encode()

    def check_sensors_input(self, data):
        json_in = data.json_in
        try:
            if self.alarm_system_on and not self.alarm_ring_on:
                sensors = ["presenca", "janela", "porta"]
                for sens in json_in["inputs"]:
                    try:
                        if sensors.index(sens["type"]) and int(sens["value"]) == 1:
                            message = json.dumps(
                                dict(type="output", tag="Sirene do Alarme", value=1)
                            )
                            self.subscribe_message_to_rooms(
                                message=message, all_rooms=True, room=None
                            )
                            self.logger.write_row(
                                f"Acionamento do alarme por {sens['type']} enquanto sistema de alarme ligado"
                            )
                            self.alarm_ring_on = True
                            break
                    except ValueError:
                        pass
            if not self.alarm_system_on:
                for sens in json_in["inputs"]:
                    if sens["type"] == "presenca":
                        if int(sens["value"]) == 1 and not data.keep_lamps_on:
                            message = json.dumps(
                                dict(type="output", tag="lampada", value=1, time=15)
                            )
                            self.subscribe_message_to_rooms(
                                message=message, all_rooms=False, room=json_in["nome"]
                            )
                            self.logger.write_row(
                                "Acionamento das lampadas por 15 segundos"
                            )
                            data.keep_lamps_on = True
                        elif int(sens["value"]) == 0 and data.keep_lamps_on:
                            data.keep_lamps_on = False
                        break
            if not self.alarm_ring_on:
                for sens in json_in["inputs"]:
                    if sens["type"] == "fumaca" and int(sens["value"]) == 1:
                        message = json.dumps(
                            dict(type="output", tag="Sirene do Alarme", value=1)
                        )
                        self.subscribe_message_to_rooms(
                            message=message, all_rooms=True, room=None
                        )
                        self.logger.write_row("Acionamento do alarme deteccao fumaca")
                        self.alarm_ring_on = True
                        break

            if len(json_in["feedback_acionamentos"]) > 0:
                for obj in json_in["feedback_acionamentos"]:
                    value = int(obj["value"])
                    success = int(obj["success"])
                    if obj["tag"] == "Try to turn on alarm system":
                        if success == 1:
                            message = "Alarm system on\n"
                            self.alarm_system_on = True
                        else:
                            message = f"There are input sensors indicating presence or smoke or window/door open in {json_in['nome']}\n"
                        self.display.message_room(message)
                        continue

                    if success == 1:
                        message = f"[Successful] to {obj['tag']} to value {value}\n"
                    else:
                        message = f"[Unsuccessful] to {obj['tag']} to value {value}\n"

                    if obj["tag"] == "Sirene do Alarme":
                        self.alarm_ring_on = True if value == 1 else False

                    self.display.message_room(message)
        except Exception as error:
            self.display.message_error(
                f"Failed in check_sensors_input, error: {error}\n"
            )
            pass

    def service_connection(self, key, mask):
        try:
            sock = key.fileobj
            data = key.data
            if mask & selectors.EVENT_READ:
                recv_data = sock.recv(2500)
                if recv_data:
                    aux_list = recv_data.decode().split("\n")
                    aux_list = aux_list[0]
                    try:
                        data.json_in = json.loads(aux_list)
                        if not data.room:
                            data.room = data.json_in["nome"]
                            self.socketRoom[data.room] = key
                        self.display.set_room(key=data.room, value=data.json_in)
                        self.check_sensors_input(data=data)
                    except json.decoder.JSONDecodeError as error:
                        self.display.message_error(f"JSONDecodeError, error: {error}\n")
                        pass
                else:
                    print(f"Closing connection to {data.room}")
                    self.sel.unregister(sock)
                    sock.close()
                    self.num_rooms = self.num_rooms - 1
                    self.socketRoom.pop(data.room)
            if mask & selectors.EVENT_WRITE:
                if data.json_out:
                    sock.send(data.json_out)
                    data.json_out = b""
        except (ConnectionResetError, OSError) as error:
            self.display.message_error(
                f"Failed to service_connection, error: {error}\n"
            )
            self.display.message_server(f"Closing connection to {key.data.room}\n")
            self.sel.unregister(key.fileobj)
            pass

    def input_user_display_room(self):
        self.display.alarm_system(self.alarm_system_on)
        self.display.show_number_persons(show_all=True, key=None)
        self.display.message_server("Press the number of the room or 0 to come back:\n")
        self.display.show_available_rooms()
        while True:
            self.display.reset_style()
            num_pressed = (sys.stdin.readline()).strip()
            if not num_pressed.isnumeric():
                self.display.message_server("<- Press a number, not string\n")
                continue
            num_pressed = int(num_pressed)
            if num_pressed == 0:
                break
            if num_pressed < 1 or num_pressed > self.num_rooms:
                self.display.message_server("<- Wrong number, press again\n")
            else:
                system("clear")
                self.display.show(num_pressed)
                break

    def input_user_enter_command(self):
        system("clear")
        self.display.message_server("Write: \n")
        self.display.message_server(
            "   <room> - <output> - <value> to send a command to room specific sensor\n"
        )
        self.display.message_server(
            "   'room lamps' - <room> - <value> to on/off all lamps in the room \n"
        )
        self.display.message_server(
            "   'room outputs' - <room> - <value> to on/off all the outputs (minus alarm) in the room\n"
        )
        self.display.message_server(
            "   'all lamps' - <value> to on/off all the lamps in all the rooms\n"
        )
        self.display.message_server(
            "   'all outputs' - <value> to on/off all the outputs (minus alarm) in all the rooms\n"
        )
        self.display.message_server(
            "   'alarm' to on/off alarm system\n"
        )  # or 0 to come back
        self.display.message_server("Obs: (value: 0 = off and 1 = on)\n")
        self.display.message_server("Or write 0 to come back\n")

        special_commands = ["room lamps", "all lamps", "room outputs", "all outputs"]

        while True:
            self.display.reset_style()
            command = sys.stdin.readline()
            if (command.strip()).isnumeric() and int(command.strip()) == 0:
                return

            elif command.strip() == "alarm":
                if self.alarm_system_on:
                    message = f"<- Turn off alarm system\n"
                    self.display.message_server(message)
                    self.alarm_system_on = False
                    break

                self.logger.write_row(f"Try to turn on alarm system")
                message = json.dumps(
                    dict(
                        type="alarm_system", tag="Try to turn on alarm system", value=1
                    )
                )
                self.subscribe_message_to_rooms(
                    message=message, all_rooms=True, room=None
                )
                break

            if command.split("-")[0].strip() in special_commands:
                params = command.split("-")
                comm = params[0].strip()
                if "room" in comm:
                    room = params[1].strip()
                    if (
                        not room in self.socketRoom.keys()
                        or len(params) != 3
                        or not params[2].strip() in ["0", "1"]
                    ):
                        self.display.message_server(
                            "<- Invalid room or value, write again\n"
                        )
                        continue
                    value = params[2].strip()
                    self.logger.write_row(f"{comm} to value {value} in room {room}")
                    message = json.dumps(
                        dict(type=comm, tag=f"{command.strip()}", value=value)
                    )
                    self.subscribe_message_to_rooms(
                        message=message, all_rooms=False, room=room
                    )
                    break
                else:
                    if not params[1].strip() in ["0", "1"]:
                        self.display.message_server("<- Invalid value, write again\n")
                        continue
                    value = params[1].strip()
                    self.logger.write_row(f"{comm} to value {value} in all rooms")
                    message = json.dumps(
                        dict(type=comm, tag=f"{command.strip()}", value=value)
                    )
                    self.subscribe_message_to_rooms(
                        message=message, all_rooms=True, room=None
                    )
                    break

            list_commands = command.split("-")
            if len(list_commands) != 3:
                self.display.message_server("<- Invalid inputs, write again\n")
                continue

            room = list_commands[0].strip()
            tag = list_commands[1].strip()
            value = int(list_commands[2].strip())

            if not room in self.socketRoom.keys():
                self.display.message_server("<- Invalid room, write again\n")
                continue

            if value != 0 and value != 1:
                self.display.message_server("<- Invalid value, write again\n")
                continue

            tag_finded = False
            for obj in self.socketRoom[room].data.json_in["outputs"]:
                if obj["tag"] == tag:
                    message = json.dumps(dict(type="output", tag=tag, value=value))
                    self.subscribe_message_to_rooms(
                        message=message, all_rooms=False, room=room
                    )
                    tag_finded = True
                    logger_message = f"{room} - {tag} - {value}"
                    self.logger.write_row(logger_message)
                    break

            if tag_finded:
                break
            else:
                self.display.message_server("<- Invalid tag, write again\n")

    def input_user(self):
        try:
            while True and self.alive:
                if self.num_rooms == 0:
                    self.display.message_server("<- No room connected\n")
                    sleep(2)
                    continue

                self.display.message_server(
                    "Press 1 to show room's info\n   2 to send a command\n   0 to quit\n"
                )
                self.display.reset_style()
                pressed = input()

                if not (pressed.strip()).isnumeric():
                    self.display.message_server("<- Wrong input\n")
                    continue

                pressed = int(pressed.strip())

                if pressed == 0:
                    self.alive = False
                    continue

                if pressed != 1 and pressed != 2:
                    self.display.message_server("<- Wrong input\n")
                    continue

                if pressed == 1:
                    system("clear")
                    self.input_user_display_room()
                else:
                    system("clear")
                    self.input_user_enter_command()

        except Exception as error:
            self.display.message_error(f"Error on input_user {error}\n")
            self.alive = False

    def request_temperature(self):
        try:
            message = json.dumps(
                dict(type="input", tag="Sensor de Temperatura e Umidade", value="1")
            )
            self.subscribe_message_to_rooms(message=message, all_rooms=True, room=None)
        except:
            self.display.message_error("Request_temperature Failed\n")
            self.alive = False

    def manage_connections(self):
        count = 0
        while True and self.alive:
            for key, mask in self.sel.select():
                if count == 10:
                    self.request_temperature()
                    count = 0
                if key.data is None:
                    server.accept_wrapper(key.fileobj)
                else:
                    server.service_connection(key, mask)
                sleep(0.2)
                count = count + 1

    def run(self):
        thread_input = threading.Thread(target=self.input_user)
        thread_input.daemon = True
        thread_input.start()
        self.manage_connections()
        self.logger.close_file()
        thread_input.join(0.1)
        self.sel.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Missing <ip address> <port>")
        exit()
    ip_address = sys.argv[1]
    port = int(sys.argv[2])
    server = Server(ip_address, port)
    signal.signal(signal.SIGINT, server.signal_int_handler)
    server.run()
