import sys
import socket
import selectors
import types
import json

sel = selectors.SelectSelector()

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

jsonExample = {
    "inputs": {
        "presence_sensor": "",  # 0 - vazio, 1 - alguém na sala
        "smoke_sensor": "",  # 0 - sem fumaça, 1 - com fumaça
        "window1": "",  # 0 - fechada, 1 - aberta
        "window2": "",  # 0 - fechada, 1 - aberta
        "count_people_in": "",  # ?
        "count_people_out": "",  # ?
    },
    "outputs": {
        "lamp1": "",  # 0 - desligada, 1 - acessa
        "lamp2": "",  # 0 - desligada, 1 - acessa
        "air": "",  # 0 - desligado, 1 - ligado
        "projector": "",  # 0 - desligado, 1 - ligado
        "buzzer": "",  # 0 - desligado, 1 - ligado
    },
    "wire": {
        "temp/umid": "",  # ?
    },
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
        print("Entradas:")
        for key, value in input.items():
            print(f"{key}: {value}")
        print("----------------------------")

    def outputs(_, output):
        print("Saidas:")
        for key, value in output.items():
            print(f"{key}: {value}")
        print("----------------------------")

    def temp(_, temp):
        print("Valor da temperatura e umidade: ")
        print(temp)
        print("----------------------------")

    def show(self):
        for key, value in self.rooms.items():
            if value:
                print(key)
                self.inputs(value["inputs"])
                self.outputs(value["outputs"])
                self.temp(value["wire"]["temp/umid"])


class Server:
    def __init__(self) -> None:
        self.host, self.port = sys.argv[1], int(sys.argv[2])
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.bind((self.host, self.port))
        self.lsock.listen()
        print(f"Listening on {(self.host, self.port)}")
        self.lsock.setblocking(False)
        sel.register(self.lsock, selectors.EVENT_READ, data=None)
        self.num_rooms = 0
        self.display = Display()

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        print(f"Accepted connection from {addr}")
        conn.setblocking(False)
        room = str(addr[0]) + "/" + str(addr[1])
        print(f"room: {room}")
        data = types.SimpleNamespace(
            addr=addr, room=roomsAux[self.num_rooms], json_in=b"", json_out=b""
        )  # addr[0] == addr, addr[1] == connid
        self.num_rooms = self.num_rooms + 1
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        sel.register(conn, events, data=data)

    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                data.json_in = recv_data
                self.display.set_room(key=data.room, value=json.loads(data.json_in))
                self.display.show()
            else:
                print(f"Closing connection to {data.addr}")
                sel.unregister(sock)
                sock.close()
                self.num_rooms = self.num_rooms - 1
        if mask & selectors.EVENT_WRITE:
            if data.json_out:
                print(f"Echoing {data.json_out!r} to {data.addr}")
                sent = sock.send(data.json_out)  # Should be ready to write
                data.json_out = data.json_out[sent:]


try:
    server = Server()
    while True:
        for key, mask in sel.select(timeout=None):
            if key.data is None:
                server.accept_wrapper(key.fileobj)
            else:
                server.service_connection(key, mask)
except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()
