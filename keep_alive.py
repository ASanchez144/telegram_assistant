import os
import threading
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is still running!", 200

def start_keep_alive():
    port = os.environ.get("PORT")
    
    if port is None:
        print("⚠️ No se encontró la variable de entorno PORT, usando 10000")
        port = 10000
    else:
        port = int(port)
    
    print(f"🚀 KeepAlive ejecutándose en el puerto {port}")  # 🔍 Verifica qué puerto se usa
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    threading.Thread(target=start_keep_alive, daemon=True).start()

