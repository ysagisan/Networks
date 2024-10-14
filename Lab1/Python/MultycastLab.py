import socket
import struct
import threading
import time
import sys
from ipaddress import ip_address, IPv4Address, IPv6Address

MULTICAST_TTL = 2  # Время жизни пакета
HEARTBEAT_INTERVAL = 2  # Интервал между сообщениями
TIMEOUT = 5  # Время ожидания для удаления мертвых копий

class MulticastListener:
    def __init__(self, multicast_group, port=50000):
        self.multicast_group = multicast_group
        self.port = port
        self.is_ipv6 = isinstance(ip_address(multicast_group), IPv6Address)
        self.alive_copies = {}
        self.lock = threading.Lock()


    def start(self):
        # Создаем поток для прослушивания мультикаст сообщений
        listener_thread = threading.Thread(target=self.listen_multicast)
        listener_thread.daemon = True
        listener_thread.start()

        # Создаем поток для отправки сообщений
        sender_thread = threading.Thread(target=self.send_multicast)
        sender_thread.daemon = True
        sender_thread.start()

        # Основной цикл для проверки активных копий
        while True:
            time.sleep(1)
            self.check_alive_copies()


    def listen_multicast(self):
        # Создаем сокет для прослушивания мультикаст сообщений
        if self.is_ipv6:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        # Разрешаем повторное использование адреса
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Привязываем сокет к мультикаст группе и порту
        if self.is_ipv6:
            sock.bind(('', self.port))
            group = socket.inet_pton(socket.AF_INET6, self.multicast_group)
            mreq = group + struct.pack('@I', 0)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
        else:
            sock.bind(('', self.port))
            group = socket.inet_aton(self.multicast_group)
            mreq = struct.pack('4sL', group, socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        print(f"Listening for multicast messages on {self.multicast_group}:{self.port}")

        while True:
            data, addr = sock.recvfrom(1024)
            message = data.decode('utf-8')

            if message == 'ALIVE':
                with self.lock:
                    self.alive_copies[addr[0]] = time.time()


    def send_multicast(self):
        # Создаем сокет для отправки мультикаст сообщений
        if self.is_ipv6:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            addr = (self.multicast_group, self.port, 0, 0)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            addr = (self.multicast_group, self.port)

        # Устанавливаем TTL для мультикаст пакетов
        sock.setsockopt(socket.IPPROTO_IP if not self.is_ipv6 else socket.IPPROTO_IPV6, 
                        socket.IP_MULTICAST_TTL, MULTICAST_TTL)

        while True:
            # Отправляем сообщение "ALIVE" в сеть
            sock.sendto(b'ALIVE', addr)
            time.sleep(HEARTBEAT_INTERVAL)


    def check_alive_copies(self):
        current_time = time.time()
        with self.lock:
            # Удаляем те копии, которые не ответили в течение TIMEOUT секунд
            inactive_copies = [ip for ip, last_seen in self.alive_copies.items() if current_time - last_seen > TIMEOUT]
            for ip in inactive_copies:
                del self.alive_copies[ip]

            # Выводим список активных копий
            if inactive_copies or len(self.alive_copies) > 0:
                print("Active copies:", list(self.alive_copies.keys()))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <multicast_group>")
        sys.exit(1)

    multicast_group = sys.argv[1]

    # Создаем и запускаем приложение
    listener = MulticastListener(multicast_group)
    listener.start()