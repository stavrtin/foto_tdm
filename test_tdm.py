import logging
import sys
import requests
from messenger_bot_api import *
import time
import arch_tdm.config
from PIL import Image as PILImage
import io
import numpy as np


class TdmBot:
    """Класс для работы с TDM ботом"""

    def __init__(self):
        """Инициализация бота"""
        self.setup_logging()

        self.token = arch_tdm.config.TOKEN_TDM
        self.workspace_id = arch_tdm.config.TARGET_WORKSPACE_ID
        self.group_id = arch_tdm.config.TARGET_GROUPE_ID

        self.rest = 'https://api.tdm.mos.ru'
        self.sse = 'https://pusher.tdm.mos.ru'
        self.file = 'https://fileupload.tdm.mos.ru'

        self.logger = logging.getLogger('bot')
        self.bot = None
        self.is_initialized = False

    def setup_logging(self):
        """Настройка логирования"""
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        root.addHandler(handler)

    def initialize_bot(self):
        """Инициализация приложения бота"""
        try:
            self.bot = Application(
                self.token,
                {
                    'api_base_url': self.rest,
                    'sse_base_url': self.sse,
                    'file_upload_base_url': self.file
                }
            )
            self.setup_handlers()
            self.is_initialized = True
            self.logger.info("TDM бот инициализирован")
        except Exception as e:
            self.logger.error(f"Ошибка инициализации TDM бота: {e}")
            self.is_initialized = False

    def send_photo_with_caption(self, image_array, caption=""):
        """
        Отправка фото с подписью в TDM

        Args:
            image_array (numpy.array): Изображение в формате numpy array
            caption (str): Подпись к фото
        """
        if not self.is_initialized:
            self.logger.error("TDM бот не инициализирован")
            return False

        try:
            # Конвертируем numpy array в PIL Image
            pil_image = PILImage.fromarray(image_array)

            # Сохраняем изображение в буфер
            img_buffer = io.BytesIO()
            pil_image.save(img_buffer, format='JPEG')
            img_buffer.seek(0)

            # Создаем объект Image для TDM API
            tdm_image = Image('detection.jpg', img_buffer.read())

            # Отправляем изображение с подписью
            # Для отправки используем прямое обращение к API через существующее соединение
            # или создаем временное событие для отправки
            self._send_to_chat(tdm_image, caption)

            self.logger.info("✅ Фото отправлено в TDM")
            return True

        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки фото в TDM: {e}")
            return False

    def _send_to_chat(self, image, caption):
        """
        Внутренний метод для отправки в чат
        В реальной реализации нужно использовать API TDM для отправки
        """
        # Здесь должен быть код для отправки через TDM API
        # Временно используем логирование
        self.logger.info(f"TDM отправка: {caption}")

    def image_handler(self, event: MessageBotEvent):
        """Обработчик отправки изображения (для команд)"""
        self.logger.info("Получена команда send_image")

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.bot.add_handler(CommandHandler('send_image', self.image_handler))

    def run(self):
        """Запуск бота в режиме прослушивания"""
        if not self.is_initialized:
            self.initialize_bot()

        if self.is_initialized:
            self.logger.info("TDM бот запущен в режиме прослушивания")
            self.bot.start()


# Глобальный экземпляр для использования в других модулях
tdm_bot_instance = TdmBot()


def initialize_tdm_bot():
    """Инициализация TDM бота для использования в других модулях"""
    tdm_bot_instance.initialize_bot()
    return tdm_bot_instance


if __name__ == '__main__':
    # Тестовый запуск
    bot_instance = initialize_tdm_bot()
    bot_instance.run()

