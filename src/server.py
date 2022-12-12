import sys
import socket
import selectors
import types
import json
import threading
from time import sleep
from os import system

rooms = {
    "164.41.98.16/13508": "Sala 1",
    "164.41.98.26/13508": "Sala 2",
    "164.41.98.28/13508": "Sala 3",
    "164.41.98.15/13508": "Sala 4",
}

roomsAux = {
    0: "Sala 1",
    1: "Sala 2",
    2: "Sala 3",
    3: "Sala 4",
}

socketRoom = {
    "Sala 1": None,
    "Sala 2": None,
    "Sala 3": None,
    "Sala 4": None,
}

info_display = {
    "Sala 1": {},
    "Sala 2": {},
    "Sala 3": {},
    "Sala 4": {},
}


class Display:
    def __init__(self) -> None:
        self.rooms = {}

    def set_room(self, key, value):
        self.rooms[key] = value

    def inputs(_, input):
        print("Inputs:")
        for obj in input:
            tag = obj["tag"]
            value = "desligado" if int(obj["value"]) == 0 else "ligado"
            print(f"{tag}: {value}")
            print("----------------------------")

    def outputs(_, output):
        print("Outputs:")
        for obj in output:
            tag = obj["tag"]
            value = "desligado" if int(obj["value"]) == 0 else "ligado"
            print(f"{tag}: {value}")
            print("----------------------------")

    def temp(_, obj):
        temp = obj["value_temp"]
        hum = obj["value_hum"]
        print(f"Valor da temperatura e umidade: {temp}°C {hum}%")
        print("----------------------------")

    def show(self):
        system('clear')
        for key, value in self.rooms.items():
            if value:
                print(key)
                self.inputs(value["inputs"])
                self.outputs(value["outputs"])
                self.temp(value["sensor_temperatura"][0])


class Server:
    def __init__(self, ip_addr, port) -> None:
        self.host = ip_addr
        self.port = port
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.bind((self.host, self.port))
        self.lsock.listen()
        print(f"Listening on {(self.host, self.port)}")
        self.lsock.setblocking(False)
        self.sel = selectors.SelectSelector()
        self.sel.register(self.lsock, selectors.EVENT_READ, data=None)
        self.num_rooms = 0
        self.display = Display()
        self.alive = True

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        print(f"Accepted connection from {addr}")
        conn.setblocking(False)
        room = str(addr[0]) + "/" + str(addr[1])
        print(f"room: {room}")
        data = types.SimpleNamespace(
            addr=addr, room=roomsAux[self.num_rooms], json_in="", json_out=b""
        )
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        socketRoom[roomsAux[self.num_rooms]] = self.sel.register(conn, events, data=data)
        self.num_rooms = self.num_rooms + 1

    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(2000)  # Should be ready to read
            if recv_data:
                data.json_in = json.loads(recv_data)
                self.display.set_room(key=data.room, value=data.json_in)
                self.display.show()
            else:
                print(f"Closing connection to {data.addr}")
                self.sel.unregister(sock)
                sock.close()
                self.num_rooms = self.num_rooms - 1
        if mask & selectors.EVENT_WRITE:
            if data.json_out:
                #print(f"Echoing {data.json_out} to {data.addr}")
                sent = sock.send(data.json_out)  # Should be ready to write
                data.json_out = data.json_out[sent:]

    def input_user(self):
        try:
            while True and self.alive:
                if self.num_rooms == 0:
                    sleep(0.2)
                    continue
                print('Write the <room> - <name> - <value> of the output')
                command = sys.stdin.readline()
                list_commands = command.split("-")
                if len(list_commands) != 3:
                    print("Invalid values")
                    continue

                room = list_commands[0].strip()
                tag = list_commands[1].strip()
                value = list_commands[2].strip()
       
                if not socketRoom[room]:
                    print("Invalid room")
                    continue
                tag_finded = False
 
                for obj in socketRoom[room].data.json_in["outputs"]:
                    if obj["tag"] == tag:
                        message = json.dumps(dict(tag=tag, value=value))
                        socketRoom[room].data.json_out += message.encode()
                        tag_finded = True
                if not tag_finded:
                    print("Invalid tag")
        except:
            print("Aoba")
            self.alive = False

    def request_temperature(self):
        try:
            message = json.dumps(dict(tag="Sensor de Temperatura e Umidade", value="1"))
            while True and self.alive:
                for room in socketRoom.values():
                    if room:
                        room.data.json_out += message.encode()
                sleep(2)
        except:
            print("request_temperature Failed")
            self.alive = False

    def manage_connections(self):
        while True and server.alive:
            for key, mask in self.sel.select(timeout=1000):
                if key.data is None:
                    server.accept_wrapper(key.fileobj)
                else:
                    server.service_connection(key, mask)
                sleep(0.2)

    def run(self):
        try:
            thread_input = threading.Thread(target=self.input_user)
            thread_req_temp = threading.Thread(target=self.request_temperature)
            thread_input.start()
            thread_req_temp.start()

            self.manage_connections()
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
            server.alive = False
            thread_input.join(0.1)
            thread_req_temp.join(0.1)
        finally:
            self.sel.close()

        thread_input.join(0.1)
        thread_req_temp.join(0.1)
        self.sel.close()

#Sala 1 - Lâmpada 01 - 1
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Missing <ip address> <port>")
        exit()
    ip_address = sys.argv[1]
    port = int(sys.argv[2])
    server = Server(ip_address, port)
    server.run()
