import os
import threading
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is still running!", 200

def start_keep_alive():
    port = int(os.environ.get("PORT", 8080))  # ⬅ Aquí usamos el puerto dinámico de Render
    print(f"🚀 KeepAlive ejecutándose en el puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=start_keep_alive, daemon=True).start()
