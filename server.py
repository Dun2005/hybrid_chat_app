# server.py
import socket, threading, json

HOST = "0.0.0.0"
PORT = 5036

clients = {}  # sock -> name
lock = threading.Lock()

def send(sock, payload: dict):
    try:
        sock.sendall((json.dumps(payload) + "\n").encode())
    except OSError:
        pass

def broadcast(payload: dict, exclude=None):
    with lock:
        dead = []
        for s in list(clients.keys()):
            if s is exclude:
                continue
            try:
                s.sendall((json.dumps(payload) + "\n").encode())
            except OSError:
                dead.append(s)
        for s in dead:
            name = clients.pop(s, None)
            try: s.close()
            except: pass

def handle_client(sock, addr):
    file = sock.makefile("r")
    name = None
    try:
        # Expect a join first: {"type":"join","name":"Alice"}
        line = file.readline()
        if not line:
            return
        msg = json.loads(line.strip() or "{}")
        if msg.get("type") != "join":
            send(sock, {"type": "error", "text": "Send join first"})
            return
        name = msg.get("name") or f"{addr[0]}:{addr[1]}"

        with lock:
            clients[sock] = name
        broadcast({"type":"info","text":f"{name} joined"})
        send(sock, {"type":"info","text":"Welcome! You are connected."})

        # Chat loop
        for line in file:
            try:
                m = json.loads(line.strip() or "{}")
            except json.JSONDecodeError:
                continue
            if m.get("type") == "chat":
                text = (m.get("text") or "").strip()
                if not text:
                    continue
                if text.lower() in {"/quit", "/exit"}:
                    break
                broadcast({"type":"chat","name":name,"text":text})
            else:
                # ignore unknown types
                pass
    finally:
        with lock:
            if sock in clients:
                clients.pop(sock, None)
                broadcast({"type":"info","text":f"{name or addr} left"})
        try: sock.close()
        except: pass

def main():
    print(f"Chat server on {HOST}:{PORT}")
    with socket.create_server((HOST, PORT), reuse_port=False) as srv:
        srv.listen(100)
        while True:
            sock, addr = srv.accept()
            t = threading.Thread(target=handle_client, args=(sock, addr), daemon=True)
            t.start()

if __name__ == "__main__":
    main()
