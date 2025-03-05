from app import socketio

@socketio.on("connect")
def handle_connect():
    print("Client connecté")

@socketio.on("disconnect")
def handle_disconnect():
    print("Client déconnecté")

def emit_new_email(email):
    socketio.emit("new_email", email)
