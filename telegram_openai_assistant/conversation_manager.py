import time
import asyncio
from typing import Optional, Dict

class ConversationManager:
    """Manages global state and orchestrates bot-to-bot conversations."""
    def __init__(self):
        self.all_bots: Dict[str, 'Bot'] = {}  # Dictionary to hold all bots by name
        self.active_conversation: Dict[int, dict] = {}  # {group_id: conversation_state}
        self.bot_order: list[str] = []  # List of bot names in fixed order
        self.current_bot_index: int = 0  # Tracks the current bot in the rotation
        #self.group_id: Optional[int] = None  # Active group's ID
        self.last_assistant_response = None
        self.threads: Dict[int, str] = {}  # {group_id: thread_id} almacena los hilos en memoria
    def register_bots(self, bots: Dict[str, 'Bot']):
        """Registra los bots disponibles en la instancia de ConversationManager."""
        self.all_bots = bots
        print("[DEBUG] Bots registrados correctamente.")

    def is_active(self, group_id: int) -> bool:
        """Verifica si un group_id tiene una conversación activa."""
        return group_id in self.threads

    def get_thread_id(self, group_id: int) -> Optional[str]:
        """Obtiene el thread_id asociado a un group_id si existe."""
        return self.threads.get(group_id)

    def set_thread_id(self, group_id: int, thread_id: str):
        """Asocia un thread_id a un group_id en la memoria del proyecto."""
        if thread_id and isinstance(thread_id, str):  # Asegurar que el thread_id es válido antes de asignarlo
            self.threads[group_id] = thread_id
            print(f"[DEBUG] Se asoció thread_id: {thread_id} al group_id: {group_id}")
        else:
            print(f"[DEBUG] No se encontró un thread_id para group_id: {group_id}, creando uno nuevo.")
            next_bot = next(iter(self.all_bots.values()))
            thread = next_bot.assistant_handler.client.beta.threads.create()
            if thread and hasattr(thread, 'id') and thread.id:
                self.threads[group_id] = thread.id
                print(f"[DEBUG] Nuevo thread_id creado: {thread.id} para group_id: {group_id}")
            else:
                print(f"[ERROR] No se pudo crear un thread válido para group_id: {group_id}")

    def get_next_bot(self) -> Optional[str]:
        """Obtiene el siguiente bot disponible en la rotación para responder."""
        if not self.all_bots:
            return None
        return next(iter(self.all_bots.keys()))

    async def handle_turn(self, group_id: int, message: str) -> None:
        """Procesa un mensaje para el grupo correspondiente."""
        print(f"[DEBUG] Procesando mensaje para group_id: {group_id}")

        thread_id = self.get_thread_id(group_id)
        if not thread_id:
            self.set_thread_id(group_id, None)
            thread_id = self.get_thread_id(group_id)

        if not thread_id:
            print(f"[ERROR] No se pudo obtener o crear un thread_id válido para group_id: {group_id}")
            return

        print(f"[DEBUG] Usando thread_id: {thread_id} para group_id: {group_id}")

        next_bot_name = self.get_next_bot()
        if not next_bot_name:
            print("[ERROR] No hay bots disponibles para responder.")
            return

        next_bot = self.all_bots[next_bot_name]

        async def send_to_telegram(chunk):
            """Envía la respuesta del bot al usuario/grupo correcto."""
            try:
                await next_bot.application.bot.send_message(chat_id=group_id, text=chunk)
            except Exception as e:
                print(f"[ERROR] Error enviando mensaje a Telegram: {e}")

        try:
            await next_bot.assistant_handler.stream_response(group_id, message, send_to_telegram)
        except Exception as e:
            print(f"[ERROR] Error durante el procesamiento del mensaje: {e}")





