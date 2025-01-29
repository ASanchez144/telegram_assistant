import time
import asyncio
import re
from typing import Optional, Dict


def clean_text_and_split(text):
    """
    Divide el texto en párrafos formateados preservando los espacios originales.
    Detecta listas numeradas y separa cada elemento adecuadamente.
    """
    # Asegurar espacio después del número solo si no está seguido por '*' para no romper **bold**
    text = re.sub(r'(\d+)\.([^\s*])', r'\1. \2', text)  # Modificado para números múltiples y evitar *

    # Dividir usando números de lista con espacio opcional después del punto
    paragraphs = re.split(r'(\d+\.\s*\*\*[^:]+\*\*:)', text)  # \s* permite 0 o más espacios

    # Combinar encabezados de lista con su contenido
    combined_paragraphs = []
    buffer = ""
    for i, segment in enumerate(paragraphs):
        if re.match(r'\d+\.\s*\*\*[^:]+\*\*:', segment):
            if buffer:
                combined_paragraphs.append(buffer.strip())
            buffer = segment
        else:
            buffer += segment
    if buffer.strip():
        combined_paragraphs.append(buffer.strip())

    return [p for p in combined_paragraphs if p.strip()]


def add_spaces_to_fragment(chunk):
    """
    Añade espacios correctamente entre palabras y puntuación.
    Maneja fragmentos de texto sin dividir palabras incompletas.
    """
    # Si el chunk comienza con espacio, preservarlo (puede indicar nueva oración)
    if not chunk:
        return ""
    
    # Manejar espacios al inicio
    leading_space = ' ' if chunk[0].isspace() else ''
    chunk = chunk.strip()
    
    # Dividir en palabras/puntuación y unir con espacios adecuados
    parts = re.findall(r'(\w+|[.,!?;:]+)', chunk)
    if not parts:
        return leading_space + chunk  # Caso raro
    
    result = parts[0]
    for part in parts[1:]:
        if re.match(r'^[.,!?;:]$', part):
            result += part
        else:
            result += f' {part}'
    
    return leading_space + result


class AssistantHandler:
    def __init__(self, client, assistant_id):
        self.client = client
        self.assistant_id = assistant_id
        self.thread_id = None
        self.message_history = []
        self.threads: Dict[int, str] = {}  # Almacenar {group_id: thread_id} en memoria

    async def stream_response(self, group_id: int, message_str: str, send_to_telegram):
        """Envía un mensaje al asistente y transmite la respuesta al usuario."""
        thread_id = self.threads.get(group_id)

        if not thread_id:
            print(f"[DEBUG] No se encontró un thread_id para group_id: {group_id}, creando uno nuevo.")
            thread = self.client.beta.threads.create()
            if thread and hasattr(thread, 'id') and thread.id:
                self.threads[group_id] = thread.id
                thread_id = thread.id
                print(f"[DEBUG] Nuevo thread_id creado: {thread_id} para group_id: {group_id}")
            else:
                print(f"[ERROR] No se pudo crear un thread para group_id: {group_id}")
                return

        print(f"[DEBUG] Usando thread_id: {thread_id} para group_id: {group_id}")

        # Enviar el mensaje al asistente
        try:
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message_str
            )
            self.message_history.append({"role": "user", "content": message_str})
        except Exception as e:
            print(f"[ERROR] Error enviando mensaje al asistente: {e}")
            return

        try:
            with self.client.beta.threads.runs.create_and_stream(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
            ) as event_handler:
                buffer = ""
                for partial_text in event_handler.text_deltas:
                    chunk = add_spaces_to_fragment(partial_text)
                    buffer += chunk
                    paragraphs = clean_text_and_split(buffer)
                    for para in paragraphs[:-1]:
                        await send_to_telegram(para)
                        self.message_history.append({"role": "assistant", "content": para})
                    buffer = paragraphs[-1] if paragraphs else ""
                if buffer.strip():
                    final_paras = clean_text_and_split(buffer.strip())
                    for para in final_paras:
                        await send_to_telegram(para)
                        self.message_history.append({"role": "assistant", "content": para})
        except Exception as e:
            print(f"[ERROR] Error durante el streaming: {e}")

    def trim_message_history(self):
        """Mantiene el historial de mensajes limitado a los últimos 20 mensajes."""
        max_messages = 20
        if len(self.message_history) > max_messages:
            self.message_history = self.message_history[-max_messages:]

'''
    def get_answer(self, message_str):
        """Get answer from assistant."""
        # Create a thread if it doesn't exist
        print(f"Enviando mensaje al asistente: {message_str}")
        if not self.thread_id:
            thread = self.client.beta.threads.create()
            self.thread_id = thread.id

        # Add the user message to the history
        self.message_history.append({"role": "user", "content": message_str})

        # Send the user message to the thread
        self.client.beta.threads.messages.create(
            thread_id=self.thread_id, role="user", content=message_str
        )

        # Start a run for the assistant to process the thread
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread_id,
            assistant_id=self.assistant_id,
        )

        # Poll for the response
        while True:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread_id, run_id=run.id
            )
            if run.status == "completed":
                break
            time.sleep(1)

        # Retrieve the latest messages from the thread
        messages = self.client.beta.threads.messages.list(thread_id=self.thread_id)

        # Find the last assistant message
        # assistant_message = None
        # for message in reversed(messages.dict()["data"]):
        #     if message["role"] == "assistant":
        #         assistant_message = message["content"][0]["text"]["value"]
        #         break
        # import ipdb; ipdb.set_trace();
        assistant_message = messages.dict()['data'][0]["content"][0]["text"]["value"].strip()
        if not assistant_message:
            raise ValueError("No assistant response found in thread messages.")

        # Add the assistant's response to the history
        self.message_history.append({"role": "assistant", "content": assistant_message})

        # Manage message history to avoid exceeding token limits
        self.trim_message_history()

        return assistant_message


    def trim_message_history(self):
        """Trim history to maintain token limit."""
        max_messages = 20  # Adjust based on your token constraints
        if len(self.message_history) > max_messages:
            self.message_history = self.message_history[-max_messages:]
'''