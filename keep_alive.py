import os
import threading
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!", 200

def start_keep_alive():
    port = int(os.environ.get("PORT", 5000))  # Render asigna un puerto automáticamente
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=start_keep_alive).start()  # Ejecutar el servidor en segundo plano
