import hashlib
import socket
import sys
import threading
import time


class NcBot:
    def __init__(self, server_address, nick, secret):
        self.server_address = server_address
        self.nick = nick
        self.secret = secret
        self.seen_nonces = set()
        self.command_count = 0
        self.socket = None
        self.running = True
        
    def connect(self):
        host, port = self.server_address.split(':')
        port = int(port)
        
        while self.running:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((host, port))
                print("Connected.")
                self.send_message(f"-joined {self.nick}")
                return True
            except (socket.error, ConnectionRefusedError):
                print("Failed to connect.")
                time.sleep(5)
        return False
    
    def reconnect(self):
        if self.socket:
            self.socket.close()
        print("Disconnected.")
        self.connect()
    
    def send_message(self, message):
        try:
            self.socket.sendall((message + "\n").encode())
            return True
        except (socket.error, BrokenPipeError):
            self.reconnect()
            return False
    
    def compute_mac(self, nonce):
        data = f"{nonce}{self.secret}".encode()
        return hashlib.sha256(data).hexdigest()[:8]
    
    def authenticate_command(self, nonce, mac, command_parts):
        if nonce in self.seen_nonces:
            return False
        
        computed_mac = self.compute_mac(nonce)
        if computed_mac != mac:
            return False
        
        self.seen_nonces.add(nonce)
        return True
    
    def handle_command(self, command):
        parts = command.strip().split()
        if len(parts) < 3:
            return
        
        nonce, mac, cmd = parts[0], parts[1], parts[2]
        args = parts[3:] if len(parts) > 3 else []
        
        if not self.authenticate_command(nonce, mac, cmd):
            return
        
        self.command_count += 1
        
        if cmd == "status":
            self.send_message(f"-status {self.nick} {self.command_count}")
        elif cmd == "shutdown":
            self.send_message(f"-shutdown {self.nick}")
            self.running = False
        elif cmd == "attack" and len(args) == 1:
            self.handle_attack(nonce, args[0])
        elif cmd == "move" and len(args) == 1:
            self.send_message(f"-move {self.nick}")
            self.server_address = args[0]
            self.reconnect()
    
    def handle_attack(self, nonce, target):
        try:
            host, port = target.split(':')
            port = int(port)
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect((host, port))
                s.sendall(f"{self.nick} {nonce}\n".encode())
            
            self.send_message(f"-attack {self.nick} OK")
        except socket.timeout:
            self.send_message(f"-attack {self.nick} FAIL timeout")
        except ConnectionRefusedError:
            self.send_message(f"-attack {self.nick} FAIL connection refused")
        except Exception as e:
            self.send_message(f"-attack {self.nick} FAIL {str(e)}")
    
    def run(self):
        while self.running:
            if not self.socket:
                if not self.connect():
                    continue
            
            try:
                data = self.socket.recv(4096)
                if not data:
                    raise ConnectionError("Connection closed by server")
                
                for line in data.decode().splitlines():
                    self.handle_command(line)
            except (socket.error, ConnectionError):
                self.reconnect()

def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <hostname>:<port> <nick> <secret>")
        sys.exit(1)
    
    server_address = sys.argv[1]
    nick = sys.argv[2]
    secret = sys.argv[3]
    
    bot = NcBot(server_address, nick, secret)
    bot.run()

if __name__ == "__main__":
    main()