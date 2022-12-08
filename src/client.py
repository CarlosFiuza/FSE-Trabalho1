# import sys
# import socket
# from time import sleep
# import threading

# HOST, PORT = sys.argv[1], int(sys.argv[2])

# # HOST = "127.0.0.1"  # The server's hostname or IP address
# # PORT = 65432  # The port used by the server

# # with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
# #     s.connect((HOST, PORT))
# #     s.sendall(b"Hello, world")
# #     data = s.recv(1024)

# # print(f"Received {data!r}")


# class Client:
#     def __init__(self) -> None:
#         HOST, PORT = sys.argv[1], int(sys.argv[2])
#         self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.lsock.connect((HOST, PORT))

#     def write_to_server(self):
#         while True:
#             a = sys.stdin.readline().encode()
#             self.lsock.sendall(a)

#     def read_from_server(self):
#         while True:
#             recv_data = self.lsock.recv(1024)
#             print(recv_data.decode())

#     def run(self):
#         try:
#             while True:
#                 thread = threading.Thread(target = self.write_to_server)
#                 thread.start()
#                 self.read_from_server()
#                 thread.join()
#         except KeyboardInterrupt:
#             print("Caught keyboard interrupt, exiting")
#         finally:
#             exit()

# if __name__ == '__main__':
#     try:
#         client = Client()
#         client.run()
#     except:
#         print("Falha na criação do cliente")
#     finally:
#         exit()


# # lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# # lsock.connect((HOST, PORT))

# # try:
# #     thread = threading.Thread()

# #     while True:
# #         a = sys.stdin.readline().encode()
# #         lsock.sendall(a)
# # except KeyboardInterrupt:
# #     print("Caught keyboard interrupt, exiting")
# # finally:
# #     exit()

import socket
import json

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 3211  # The port used by the server

jsonExample = {
    "inputs": {
        "presence_sensor": "0",  # 0 - vazio, 1 - alguém na sala
        "smoke_sensor": "1",  # 0 - sem fumaça, 1 - com fumaça
        "window1": "1",  # 0 - fechada, 1 - aberta
        "window2": "0",  # 0 - fechada, 1 - aberta
        "count_people_in": "1",  # ?
        "count_people_out": "1",  # ?
    },
    "outputs": {
        "lamp1": "0",  # 0 - desligada, 1 - acessa
        "lamp2": "0",  # 0 - desligada, 1 - acessa
        "air": "1",  # 0 - desligado, 1 - ligado
        "projector": "1",  # 0 - desligado, 1 - ligado
        "buzzer": "1",  # 0 - desligado, 1 - ligado
    },
    "wire": {
        "temp/umid": "1",  # ?
    },
}

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    string = json.dumps(jsonExample)
    print(string)
    s.sendall(str(string).encode())
    data = s.recv(1024)

print(f"Received {data!r}")