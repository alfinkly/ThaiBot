import asyncio
import logging

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from environs import Env


class TelegramBot:
    def __init__(self, telegram_token: str, openai_api_key: str, prompt_file: str):
        """
        Инициализация бота.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.telegram_token = telegram_token
        self.openai_api_key = openai_api_key
        self.prompt_file = prompt_file
        self.prompt = self.load_prompt()
        self.bot = Bot(token=self.telegram_token)
        self.dispatcher = Dispatcher()
        self.setup_handlers()
        self.logger.info("Бот успешно инициализирован.")

    def load_prompt(self) -> str:
        """
        Загрузка промпта из текстового файла.
        """
        try:
            with open(self.prompt_file, 'r', encoding='utf-8') as file:
                prompt = file.read()
            self.logger.info(f"Промпт загружен из файла {self.prompt_file}")
            return prompt
        except FileNotFoundError:
            self.logger.error(f"Файл {self.prompt_file} не найден.")
            return ""

    def setup_handlers(self):
        """
        Настройка обработчиков сообщений.
        """
        self.dispatcher.message.register(self.handle_message)

    async def handle_message(self, message: Message):
        """
        Обработка входящих сообщений от пользователя.
        """
        self.logger.info(f"Получено сообщение от {message.from_user.id}: {message.text}")
        user_input = message.text
        wrapped_input = f"{self.prompt}\n{user_input}"
        response = await self.send_to_openai(wrapped_input)
        await message.answer(response)
        self.logger.info(f"Отправлен ответ пользователю {message.from_user.id}")

    async def send_to_openai(self, text: str) -> str:
        """
        Отправка сообщения в OpenAI API и получение ответа.
        """
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.openai_api_key}',
        }
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": text}],
            "max_tokens": 150,
            "n": 1,
            "stop": None,
            "temperature": 1.0,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as resp:
                response_text = await resp.text()
                if resp.status == 200:
                    result = await resp.json()
                    self.logger.info("Успешно получен ответ от OpenAI API")
                    return result['choices'][0]['message']['content']
                else:
                    error_message = f"Ошибка при обращении к OpenAI API. Статус: {resp.status}"
                    self.logger.error(f"{error_message}\nОтвет сервера: {response_text}")
                    return "Извините, возникла ошибка при обработке вашего запроса."

    async def start(self):
        """
        Запуск бота.
        """
        self.logger.info("Бот запущен и начинает опрос.")
        await self.dispatcher.start_polling(self.bot)


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # Настройка логирования для aiogram
    logging.getLogger('aiogram').setLevel(logging.INFO)

    # Настройка переменных окружения
    env = Env()
    env.read_env()

    try:
        TELEGRAM_TOKEN = env.str('TELEGRAM_TOKEN')
        OPENAI_API_KEY = env.str('OPENAI_API_KEY')
        PROMPT_FILE = env.str('PROMPT_FILE', default='prompt.txt')
    except Exception as e:
        logging.error(f"Ошибка при загрузке переменных окружения: {e}")
        exit(1)

    bot = TelegramBot(TELEGRAM_TOKEN, OPENAI_API_KEY, PROMPT_FILE)
    asyncio.run(bot.start())
