import os
import socket
import threading
import time
from pathlib import Path

BUFFER_SIZE = 4096  # Размер буфера для приема данных
UPLOAD_DIR = 'uploads'

def handle_client(client_socket, client_address):
    try:
        # Получение имени файла
        file_name_length = int.from_bytes(client_socket.recv(4), 'big')
        file_name = client_socket.recv(file_name_length).decode('utf-8')
        
        # Получение размера файла
        file_size = int.from_bytes(client_socket.recv(8), 'big')
        
        # Путь для сохранения файла
        upload_path = Path(UPLOAD_DIR) / file_name
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        received_bytes = 0
        start_time = time.time()
        last_report_time = start_time
        byte_rate_report_interval = 3  # 3 секунды
        
        # Прием файла
        with open(upload_path, 'wb') as f:
            while received_bytes < file_size:
                chunk = client_socket.recv(min(BUFFER_SIZE, file_size - received_bytes))
                if not chunk:
                    break
                f.write(chunk)
                received_bytes += len(chunk)
                
                # Вывод скорости приема данных
                current_time = time.time()
                if current_time - last_report_time >= byte_rate_report_interval:
                    elapsed_time = current_time - start_time
                    current_rate = received_bytes / (current_time - last_report_time)
                    average_rate = received_bytes / elapsed_time
                    print(f"{client_address}:\n\t Мгновенная скорость: {current_rate:.2f} Б/с, Средняя скорость: {average_rate:.2f} Б/с")
                    last_report_time = current_time
                    
         # Завершающий расчет скорости, если сеанс был менее 3 секунд
        total_time = time.time() - start_time
        if total_time < byte_rate_report_interval:
            final_rate = received_bytes / total_time if total_time > 0 else 0
            print(f"{client_address}:\n\t Конечная скорость (короткий сеанс): {final_rate:.2f} Б/с")
        
        # Проверка успешности передачи
        if received_bytes == file_size:
            client_socket.sendall(b'SUCCESS')
            print(f"{client_address}:\n\t Файл '{file_name}' успешно получен.")
        else:
            client_socket.sendall(b'FAILURE')
            print(f"{client_address}:\n\t Ошибка при получении файла '{file_name}'.")

    except Exception as e:
        print(f"{client_address}:\n\t Ошибка: {e}")
    finally:
        client_socket.close()
        print(f"{client_address}:\n\t Соединение закрыто.")

def start_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', port))
    server_socket.listen(5)
    print(f"Сервер слушает порт {port}")

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Новое соединение от {client_address}")
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
            client_thread.start()
    finally:
        server_socket.close()

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Использование: python server.py <порт>")
        sys.exit(1)

    port = int(sys.argv[1])
    start_server(port)
