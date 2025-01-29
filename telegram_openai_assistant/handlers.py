from telegram.ext import CallbackContext
from telegram import Update


class BotHandlers:
    def __init__(self, bot_name: str, assistant_id: str, telegram_id: str, manager):
        self.assistant_id = assistant_id
        self.telegram_id = telegram_id
        self.bot_name = bot_name
        self.manager = manager

    async def start(self, update: Update, context: CallbackContext) -> None:
        """Envía un mensaje de bienvenida e inicia preguntas para conocer al usuario."""
        
        welcome_message = (
            "👶✨ ¡Bienvenido/a a tu Asistente Familiar! 🤰🤱\n\n"
            "Hola, soy tu asistente virtual diseñado para ayudarte en cada etapa del embarazo y la crianza de tu bebé. 💙\n\n"
            "📌 ¿Tienes dudas sobre el embarazo, el parto o el cuidado de tu peque? Estoy aquí para responderlas.\n"
            "📌 ¿Necesitas consejos sobre alimentación, sueño o desarrollo infantil? ¡Pregúntame!\n\n"
            "Antes de empezar, me gustaría conocerte mejor para ofrecerte la mejor ayuda posible. 😊\n\n"
            "📋 *Por favor, responde a estas preguntas:*"
        )

        await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message)

        # Preguntas personalizadas para el usuario
        questions = [
            "1️⃣ ¿Cuál es tu edad? 🎂",
            "2️⃣ ¿Eres hombre o mujer? ⚤",
            "3️⃣ ¿Estás embarazada? 🤰 (Sí/No)",
            "4️⃣ ¿Tienes hijos? 👶 (Sí/No)",
            "5️⃣ Si tienes hijos, ¿cuántos tienes y qué edades tienen? 🧒👧"
        ]

        for question in questions:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=question)

    async def help_command(self, update: Update, context: CallbackContext) -> None:
        """Sends a help message to the user."""
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Just send me a question and I'll try to answer it.",
        )

    async def process_message(self, update: Update, context: CallbackContext) -> None:
        """Handles incoming messages and delegates to ConversationManager."""
        group_id = update.effective_chat.id
        message = update.message.text
        print(f"Mensaje recibido de {update.message.from_user.username}: {message}")
        # Verificar si el mensaje proviene de un bot


        if update.message.from_user.is_bot:
            print("El mensaje proviene de un bot, ignorando...")
            return  # Ignora mensajes enviados por bots
        
        
        print("Estoy aquí")
        if update.message is None:
            return  # No message to process

        chat_type = update.effective_chat.type
        group_id = update.effective_chat.id
        message_text = update.message.text
        print(f"Mensaje recibido de {update.message.from_user.username}: {message_text}")

        if chat_type == "private":
            # No verificar menciones en chats privados
            if not self.manager.is_active(group_id):
                if group_id in self.manager.active_conversation:
                    await context.bot.send_message(
                        chat_id=group_id,
                        text="Estoy procesando tu solicitud, un momento por favor..."
                    )
            await self.manager.handle_turn(group_id, update.message.text)
        else:
            # Solo procesar mensajes en grupos si el bot está mencionado
            if update.message.entities:
                for entity in update.message.entities:
                    if entity.type == 'mention' and '@' + context.bot.username in message_text[entity.offset:entity.offset + entity.length]:
                        if not self.manager.is_active(group_id):
                            if self.manager.active_conversation(group_id, self.bot_name):
                                await context.bot.send_message(
                                    chat_id=group_id,
                                    text=f"Conversación iniciada por {self.bot_name} en el grupo {group_id}. Usa /end para terminar."
                                )
                        await self.manager.handle_turn(group_id, update.message.text)

    async def end_conversation(self, update: Update, context: CallbackContext) -> None:
        """Ends the active conversation."""
        group_id = update.effective_chat.id
        if self.manager.end_conversation(group_id):
            await context.bot.send_message(
                chat_id=group_id,
                text=f"Conversation ended by {self.bot_name}."
            )
        else:
            await context.bot.send_message(
                chat_id=group_id,
                text="No active conversation in this group to end."
            )