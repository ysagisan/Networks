import os
import socket
import sys

BUFFER_SIZE = 4096  # Размер буфера для отправки данных

def send_file(file_path, server_ip, server_port):
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((server_ip, server_port))
            
            # Отправка имени файла
            file_name_encoded = file_name.encode('utf-8')
            client_socket.sendall(len(file_name_encoded).to_bytes(4, 'big'))
            client_socket.sendall(file_name_encoded)
            
            # Отправка размера файла
            client_socket.sendall(file_size.to_bytes(8, 'big'))
            
            # Отправка содержимого файла
            with open(file_path, 'rb') as f:
                while chunk := f.read(BUFFER_SIZE):
                    client_socket.sendall(chunk)
            
            # Получение подтверждения от сервера
            response = client_socket.recv(7)  # "SUCCESS" или "FAILURE"
            if response == b'SUCCESS':
                print("Передача файла прошла успешно.")
            else:
                print("Ошибка при передаче файла.")
    
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Использование: python client.py <файл> <IP-адрес> <порт>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    server_ip = sys.argv[2]
    server_port = int(sys.argv[3])
    
    send_file(file_path, server_ip, server_port)
