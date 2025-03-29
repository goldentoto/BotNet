import socket
import threading

def handle_client(client_socket, addr, active_bots):
    try:
        while True:
            data = client_socket.recv(1024).decode().strip()
            if not data:
                break
            
            print(f"Received: {data} from {addr}")
            parts = data.split()
            
            if len(parts) < 2:
                continue
            
            command, bot_name = parts[0], parts[1]
            
            if command == "-joined":
                active_bots.add(bot_name)
                print(f"Bot {bot_name} joined.")
            elif command == "-status":
                print(f"Bot {bot_name} status updated.")
            elif command == "-shutdown":
                active_bots.discard(bot_name)
                print(f"Bot {bot_name} shut down.")
            elif command == "-attack":
                print(f"Bot {bot_name} performed an attack.")
            elif command == "-move":
                active_bots.discard(bot_name)
                print(f"Bot {bot_name} moved to another server.")
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        client_socket.close()
        print(f"Connection with {addr} closed.")

def start_botmonitor(host, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    print(f"BotMonitor listening on {host}:{port}")
    
    active_bots = set()
    
    while True:
        client_socket, addr = server.accept()
        print(f"New connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket, addr, active_bots))
        client_handler.start()

if __name__ == "__main__":
    start_botmonitor("0.0.0.0", 12345)
