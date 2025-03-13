import time
import asyncio
import re
import os
from typing import Optional, Dict
from telegram.constants import ParseMode

class ConversationManager:
    """Manages global state and orchestrates bot-to-bot conversations."""
    def __init__(self):
        self.all_bots: Dict[str, 'Bot'] = {}  # Dictionary to hold all bots by name
        self.active_conversation: Dict[int, dict] = {}  # {group_id: conversation_state}
        self.bot_order: list[str] = []  # List of bot names in fixed order
        self.current_bot_index: int = 0  # Tracks the current bot in the rotation
        self.last_assistant_response = None
        self.threads: Dict[int, str] = {}  # {group_id: thread_id} almacena los hilos en memoria
        self.user_data: Dict[int, Dict[str, str]] = {}  # Almacena información de usuarios {group_id: {name: nombre, ...}}
    
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

    def prepare_text_for_html(self, text):
        """
        Prepara el texto para ser enviado con formato HTML a Telegram.
        Convierte markdown básico a HTML y hace las sustituciones necesarias.
        """
        # Hacer un escape general de caracteres HTML
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Eliminar espacios antes de los dos puntos
        text = re.sub(r'\s+:', r':', text)
        
        # Detectar y formatear elementos de lista numerada (1. Título: Contenido)
        text = re.sub(r'(\d+)\.\s+([^:]+):', r'\1. <b>\2</b>:', text)
        
        # Convertir **texto** o *texto* a <b>texto</b> (negrita)
        text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*([^*]+)\*', r'<b>\1</b>', text)
        
        # Convertir _texto_ a <i>texto</i> (cursiva)
        text = re.sub(r'_([^_]+)_', r'<i>\1</i>', text)
        
        # Restaurar las etiquetas HTML que necesitamos (deshacer los escapes para etiquetas que queremos permitir)
        text = text.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
        text = text.replace('&lt;i&gt;', '<i>').replace('&lt;/i&gt;', '</i>')
        
        return text

    def save_user_info(self, group_id: int, name: str):
        """Guarda información del usuario para personalizar respuestas."""
        if group_id not in self.user_data:
            self.user_data[group_id] = {}
        self.user_data[group_id]['name'] = name
        print(f"[DEBUG] Guardada información del usuario {name} para group_id: {group_id}")

    def get_user_name(self, group_id: int) -> str:
        """Obtiene el nombre del usuario si está disponible."""
        if group_id in self.user_data and 'name' in self.user_data[group_id]:
            return self.user_data[group_id]['name']
        return ""

    async def handle_turn(self, group_id: int, message: str) -> None:
        """Procesa un mensaje para el grupo correspondiente."""
        print(f"[DEBUG] Procesando mensaje para group_id: {group_id}")

        # Extraer información del usuario si está en el formato esperado
        user_name_match = re.search(r'\[INFORMACIÓN DEL USUARIO: Nombre=([^\]]+)\]', message)
        if user_name_match:
            user_name = user_name_match.group(1)
            self.save_user_info(group_id, user_name)
            # Eliminar la etiqueta de información del usuario del mensaje
            message = re.sub(r'\[INFORMACIÓN DEL USUARIO: Nombre=[^\]]+\]\s*\n*', '', message)
            print(f"[DEBUG] Mensaje procesado para {user_name}: {message}")

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
        user_name = self.get_user_name(group_id)

        async def send_to_telegram(chunk):
            """Envía la respuesta del bot al usuario/grupo correcto con formato HTML."""
            try:
                # Personalizar la respuesta con el nombre del usuario si está disponible
                if user_name:
                    # Añadir personalización inteligente - solo si la respuesta parece apropiada
                    if re.search(r'^(hola|buenos días|buenas tardes|buenas noches)', chunk.lower()):
                        chunk = chunk.replace('Hola', f'Hola {user_name}', 1)
                    elif 'espero' in chunk.lower() and '!' in chunk:
                        chunk = chunk.replace('!', f", {user_name}!", 1)
                
                # Convertir texto a formato HTML para mejor compatibilidad
                html_text = self.prepare_text_for_html(chunk)
                await next_bot.application.bot.send_message(
                    chat_id=group_id, 
                    text=html_text,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                # Si falla con HTML, intentar con Markdown
                print(f"[WARN] Error enviando mensaje con HTML: {e}")
                try:
                    await next_bot.application.bot.send_message(
                        chat_id=group_id, 
                        text=chunk,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    # Si falla con Markdown, intentar sin formato
                    print(f"[WARN] Error enviando mensaje con Markdown: {e}")
                    try:
                        await next_bot.application.bot.send_message(
                            chat_id=group_id, 
                            text=chunk
                        )
                    except Exception as e:
                        print(f"[ERROR] Error enviando mensaje a Telegram: {e}")

        try:
            await next_bot.assistant_handler.stream_response(group_id, message, send_to_telegram)
        except Exception as e:
            print(f"[ERROR] Error durante el procesamiento del mensaje: {e}")
    
    async def handle_image(self, group_id: int, message: str, image_base64: str, image_path: str) -> None:
        """Procesa un mensaje que contiene una imagen."""
        print(f"[DEBUG] Procesando imagen para group_id: {group_id}")
        
        # Extraer información del usuario
        user_name_match = re.search(r'\[INFORMACIÓN DEL USUARIO: Nombre=([^\]]+)\]', message)
        if user_name_match:
            user_name = user_name_match.group(1)
            self.save_user_info(group_id, user_name)
            # Eliminar la etiqueta de información del usuario del mensaje
            message = re.sub(r'\[INFORMACIÓN DEL USUARIO: Nombre=[^\]]+\]\s*\n*', '', message)
            
        thread_id = self.get_thread_id(group_id)
        if not thread_id:
            self.set_thread_id(group_id, None)
            thread_id = self.get_thread_id(group_id)
            
        if not thread_id:
            print(f"[ERROR] No se pudo obtener o crear un thread_id válido para group_id: {group_id}")
            return
            
        next_bot_name = self.get_next_bot()
        if not next_bot_name:
            print("[ERROR] No hay bots disponibles para responder.")
            return
            
        next_bot = self.all_bots[next_bot_name]
        user_name = self.get_user_name(group_id)
        
        # Mismo callback de envío que en handle_turn
        async def send_to_telegram(chunk):
            try:
                # Personalizar la respuesta con el nombre del usuario si está disponible
                if user_name:
                    # Añadir personalización inteligente - solo si la respuesta parece apropiada
                    if re.search(r'^(hola|buenos días|buenas tardes|buenas noches)', chunk.lower()):
                        chunk = chunk.replace('Hola', f'Hola {user_name}', 1)
                    elif 'espero' in chunk.lower() and '!' in chunk:
                        chunk = chunk.replace('!', f", {user_name}!", 1)
                
                # Convertir texto a formato HTML para mejor compatibilidad
                html_text = self.prepare_text_for_html(chunk)
                await next_bot.application.bot.send_message(
                    chat_id=group_id, 
                    text=html_text,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                print(f"[WARN] Error enviando mensaje con HTML: {e}")
                try:
                    await next_bot.application.bot.send_message(
                        chat_id=group_id, 
                        text=chunk,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    try:
                        await next_bot.application.bot.send_message(
                            chat_id=group_id, 
                            text=chunk
                        )
                    except Exception as e:
                        print(f"[ERROR] Error enviando mensaje a Telegram: {e}")
        
        try:
            # Llamar al método específico para imágenes en AssistantHandler
            await next_bot.assistant_handler.stream_image_response(
                group_id, message, image_base64, image_path, send_to_telegram
            )
        except Exception as e:
            print(f"[ERROR] Error durante el procesamiento de la imagen: {e}")
            # Intentar enviar un mensaje de error
            try:
                await next_bot.application.bot.send_message(
                    chat_id=group_id,
                    text=f"⚠️ Lo siento, hubo un problema al procesar la imagen. Error: {str(e)}",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass  # Si esto también falla, lo dejamos pasar
            
    def end_conversation(self, group_id: int) -> bool:
        """Finaliza una conversación activa."""
        if group_id in self.threads:
            del self.threads[group_id]
            # No eliminamos los datos del usuario para mantener la personalización
            return True
        return False