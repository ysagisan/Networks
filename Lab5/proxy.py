import socket
import select
import threading


class SOCKS5Proxy:
    def __init__(self, host='127.0.0.1', port=9000):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        print(f"SOCKS5 Proxy server running on {self.host}:{self.port}")

    def resolve_domain(self, domain):
        """Функция для резолвинга доменных имен в IP-адреса."""
        try:
            result = socket.getaddrinfo(domain, None)
            for res in result:
                if res[1] == socket.SOCK_STREAM:
                    return res[4][0]
        except socket.gaierror:
            return None
        return None

    def handle_client(self, client_socket):
        try:
            # Аутентификация
            version, nmethods = client_socket.recv(2)

            methods = []
            for i in range(nmethods):
                methods.append(ord(client_socket.recv(1)))
            if methods != [0]:
                return

            client_socket.sendall(b'\x05\x00')  

            # Команда подключения
            request = client_socket.recv(4)
            if len(request) < 4:
                print("Invalid request received, closing connection.")
                client_socket.close()
                return

            if request[1] != 1: 
                client_socket.close()
                return

            addr_type = request[3]
            if addr_type == 1:  
                addr = socket.inet_ntoa(client_socket.recv(4))
            elif addr_type == 3:  
                domain_length = client_socket.recv(1)[0]
                domain = client_socket.recv(domain_length).decode()
                print(f"Attempting to connect to domain: {domain}") 
                addr = self.resolve_domain(domain) 
                if addr is None:
                    client_socket.sendall(b'\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00')
                    client_socket.close()
                    return
            elif addr_type == 4: 
                addr = socket.inet_ntop(socket.AF_INET6, client_socket.recv(16))
            else:
                client_socket.close()
                return

            port = int.from_bytes(client_socket.recv(2), 'big')

           
            try:
                if addr_type == 3: 
                    remote_address = (addr, port)
                else:
                    remote_address = (addr, port)

                remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote_socket.connect(remote_address)
                client_socket.sendall(b'\x05\x00\x00\x01' + socket.inet_aton(remote_address[0]) + port.to_bytes(2, 'big'))
            except Exception as e:
                print(f"Connection failed: {e}")
                client_socket.sendall(b'\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00')
                client_socket.close()
                return

            # Перенаправление данных между клиентом и удаленным сервером
            while True:
                r, _, _ = select.select([client_socket, remote_socket], [], [])
                if client_socket in r:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    remote_socket.sendall(data)
                if remote_socket in r:
                    data = remote_socket.recv(4096)
                    if not data:
                        break
                    client_socket.sendall(data)

        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()

    def start(self):
        while True:
            client_socket, addr = self.server.accept()
            print(f"Accepted connection from {addr}")
            client_handler = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_handler.start()


if __name__ == '__main__':
    proxy = SOCKS5Proxy()
    proxy.start()
