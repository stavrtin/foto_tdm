# telegram_bot.py
import requests
import io
from PIL import Image
import numpy as np

import logging

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token, chat_id):
        """
        Инициализация телеграм бота

        Args:
            token (str): Токен вашего бота (получить у @BotFather)
            chat_id (str): ID чата для отправки сообщений
        """
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        logger.info("TelegramBot инициализирован")


    def send_photo(self, image_array, caption=""):
        """
        Отправка фото с bounding boxes

        Args:
            image_array (numpy.array): Изображение в формате numpy array
            caption (str): Подпись к фото
        """
        logger.info(f"Отправка фото в Telegram, caption: {caption[:15]}...")

        try:
            # Конвертируем numpy array в PIL Image
            pil_image = Image.fromarray(image_array)

            # Сохраняем изображение в буфер
            img_buffer = io.BytesIO()
            pil_image.save(img_buffer, format='JPEG')
            img_buffer.seek(0)

            url = f"{self.base_url}/sendPhoto"

            files = {'photo': ('detection.jpg', img_buffer, 'image/jpeg')}
            data = {
                'chat_id': self.chat_id,
                'caption': caption
            }

            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            print("✅ Фото отправлено в Telegram")
            logger.info("✅ Фото успешно отправлено в Telegram")
            return True

        except Exception as e:
            print(f"❌ Ошибка отправки фото в Telegram: {e}")
            logger.error(f"❌ Ошибка отправки фото в Telegram: {e}")
            return False

