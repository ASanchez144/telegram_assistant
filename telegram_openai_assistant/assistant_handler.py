import time
import asyncio

class AssistantHandler:
    def __init__(self, client, assistant_id):
        self.client = client  # Cliente ya inicializado y configurado fuera de esta clase
        self.assistant_id = assistant_id
        self.thread_id = None
        self.message_history = []

    async def stream_response(self, message_str, send_to_telegram):
        """
        Envía un mensaje al asistente y transmite la respuesta en tiempo real,
        adaptado al flujo síncrono de AssistantStreamManager.
        """
        print(f"[DEBUG] Enviando mensaje al asistente (stream): {message_str}")
        start_time = time.time()

        # 1. Crear el hilo si no existe
        if not self.thread_id:
            thread = self.client.beta.threads.create()
            self.thread_id = thread.id

        # 2. Añadir el mensaje del usuario al historial
        self.message_history.append({"role": "user", "content": message_str})

        # 3. Enviar el mensaje al hilo
        self.client.beta.threads.messages.create(
            thread_id=self.thread_id,
            role="user",
            content=message_str
        )

        try:
            # 4. Usar `create_and_stream` como context manager SÍNCRONO
            with self.client.beta.threads.runs.create_and_stream(
                thread_id=self.thread_id,
                assistant_id=self.assistant_id,
            ) as event_handler:
                # 5. Iterar sobre los fragmentos de texto usando `for`
                for partial_text in event_handler.text_deltas:
                    chunk = partial_text.strip()
                    if chunk:
                        print(f"[DEBUG] Streaming chunk: {chunk}")
                        # Usar asyncio para llamar a funciones asíncronas dentro del flujo síncrono
                        await send_to_telegram(chunk)
                        self.message_history.append({"role": "assistant", "content": chunk})

        except Exception as e:
            print(f"[ERROR] Error during streaming: {e}")

        # 6. Calcular el tiempo de respuesta
        response_time = time.time() - start_time
        print(f"Respuesta completa recibida en {response_time:.2f} segundos")

        # 7. Recortar el historial para evitar excesos
        self.trim_message_history()

    def trim_message_history(self):
        """Recorta el historial de mensajes para mantener un tamaño razonable."""
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