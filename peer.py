# pip install gradio
import json, socket, threading, queue
import gradio as gr

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000

# -------- live clients (not in gr.State) --------
CLIENTS: dict[str, "TCPClient"] = {}

class TCPClient:
    def __init__(self, name="user"):
        self.name = name
        self.sock = None
        self.file = None
        self.q = queue.Queue()
        self.running = False
        self.listen_thread = None

    def connect(self, host, port):
        if self.sock:
            return "Already connected"
        try:
            self.sock = socket.create_connection((host, int(port)), timeout=5)
            self.file = self.sock.makefile("r")
            self.running = True
            self._send({"type": "join", "name": self.name})
            self.listen_thread = threading.Thread(target=self._loop, daemon=True)
            self.listen_thread.start()
            return f"Connected to {host}:{port} as {self.name}"
        except OSError as e:
            self.sock = None
            self.file = None
            return f"Connect failed: {e}"

    def _send(self, payload):
        if not self.sock: return
        try:
            self.sock.sendall((json.dumps(payload) + "\n").encode())
        except OSError:
            self.running = False

    def send_chat(self, text): self._send({"type":"chat","text":text})

    def _loop(self):
        try:
            for line in self.file:
                if not self.running: break
                line = line.strip()
                if not line: continue
                try: msg = json.loads(line)
                except json.JSONDecodeError: continue
                t = msg.get("type")
                if t == "info":
                    self.q.put(("info", f"• {msg.get('text','')}"))
                elif t == "chat":
                    self.q.put(("chat", f"{msg.get('name','anon')}: {msg.get('text','')}"))
        except Exception:
            pass
        finally:
            self.running = False
            self.q.put(("info","• connection closed"))

    def drain(self, n=100):
        out=[]
        for _ in range(n):
            try: out.append(self.q.get_nowait())
            except queue.Empty: break
        return out

    def disconnect(self):
        self.running = False
        try:
            if self.sock:
                try: self.sock.shutdown(socket.SHUT_RDWR)
                except OSError: pass
                self.sock.close()
        finally:
            self.sock = None
            self.file = None

# --- helpers to fetch per-session client ---
def _get_client(request: gr.Request) -> TCPClient | None:
    return CLIENTS.get(request.session_hash)

def _ensure_client(request: gr.Request, name: str) -> TCPClient:
    c = CLIENTS.get(request.session_hash)
    if c is None:
        c = TCPClient(name=name or "user")
        CLIENTS[request.session_hash] = c
    else:
        c.name = name or c.name or "user"
    return c

# --- Gradio callbacks (State only holds simple data) ---
def do_connect(host, port, name, request: gr.Request):
    c = _ensure_client(request, name)
    msg = c.connect(host, port)
    return gr.update(value=msg, visible=True)

def do_disconnect(request: gr.Request):
    c = _get_client(request)
    if c: c.disconnect()
    return gr.update(value="Disconnected.", visible=True)

def send_message(user_msg, chat_history, name, request: gr.Request):
    user_msg = (user_msg or "").strip()
    if not user_msg: return "", chat_history
    c = _ensure_client(request, name)
    chat_history = chat_history + [(name or "me", user_msg)]
    c.send_chat(user_msg)
    return "", chat_history

def poll_server(chat_history, request: gr.Request):
    c = _get_client(request)
    if not c: return chat_history
    for kind, text in c.drain():
        if kind == "info":
            chat_history = chat_history + [("•", text)]
        else:
            who, msg = text.split(": ", 1) if ": " in text else ("", text)
            chat_history = chat_history + [(who, msg)]
    return chat_history

with gr.Blocks(title="Gradio Chat Client") as demo:
    gr.Markdown("## 🔌 Gradio Chat Client")
    with gr.Row():
        host = gr.Textbox(value=DEFAULT_HOST, label="Host", scale=0)
        port = gr.Textbox(value=str(DEFAULT_PORT), label="Port", scale=0)
        name = gr.Textbox(value="user", label="Name", scale=0)
        connect = gr.Button("Connect", variant="primary")
        disconnect = gr.Button("Disconnect")

    notice = gr.Markdown(visible=False)
    chat = gr.Chatbot(height=420, type="tuples")
    msg = gr.Textbox(placeholder="Type a message…", label=None)
    send = gr.Button("Send")

    connect.click(do_connect, inputs=[host, port, name], outputs=[notice])
    disconnect.click(do_disconnect, inputs=None, outputs=[notice])
    send.click(send_message, inputs=[msg, chat, name], outputs=[msg, chat])

    gr.Timer(0.1).tick(poll_server, inputs=[chat], outputs=[chat])

if __name__ == "__main__":
    # 1) python server.py
    # 2) python chat_gradio_fixed.py
    demo.queue().launch()
