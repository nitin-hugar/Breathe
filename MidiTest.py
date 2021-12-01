import socket

HOST = '0.0.0.0'  # Standard loopback interface address (localhost)
PORT = 58299        # Port to listen on (non-privileged ports are > 1023)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    conn, addr = s.accept()

    try:
        with conn:
            print('Connected by', addr)
            while True:
                data = conn.recv(1024).decode()
                if data:
                    print(data)
    except KeyboardInterrupt:
        s.shutdown(1)
        s.close()
        print('Exiting...')
