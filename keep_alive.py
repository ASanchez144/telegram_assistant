import os
import threading
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!", 200

def start_keep_alive():
    """Ejecuta Flask en segundo plano sin bloquear el bot"""
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 KeepAlive ejecutándose en el puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ✅ Ejecuta el servidor en un hilo separado para evitar bloqueos
keep_alive_thread = threading.Thread(target=start_keep_alive, daemon=True)
keep_alive_thread.start()
