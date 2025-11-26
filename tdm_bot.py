# tdm_bot.py
import logging
import sys
import os
import requests
from messenger_bot_api import *
import config
import io
# from PIL import Image
from PIL import Image as PILImage
from datetime import datetime

# Настройка логирования
root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)


class TDMBot:
    def __init__(self):
        self.token = config.TOKEN_TDM
        self.workspace_id = config.TARGET_WORKSPACE_ID
        self.group_id = config.TARGET_GROUPE_ID

        self.rest = 'https://api.tdm.mos.ru'
        self.sse = 'https://pusher.tdm.mos.ru'
        self.file = 'https://fileupload.tdm.mos.ru'

        self.bot = Application(self.token, {
            'api_base_url': self.rest,
            'sse_base_url': self.sse,
            'file_upload_base_url': self.file
        })

        self.logger = logging.getLogger('tdm_bot')

    def send_photo_with_caption(self, image_path, caption):
        """
        Отправка фото с подписью в TDM

        Args:
            image_path (str): путь к файлу изображения
            caption (str): текст подписи

        Returns:
            bool: успешность отправки

        """
        # Конвертируем numpy array в PIL Image
        # pil_image = Image.fromarray(image_path)
        #
        # # Сохраняем изображение в буфер
        # img_buffer = io.BytesIO()
        # pil_image.save(img_buffer, format='JPEG')
        # img_buffer.seek(0)

        try:
            self.logger.info(f"🔄 Попытка отправки фото в TDM")

            # Конвертируем numpy array в PIL Image
            pil_image = PILImage.fromarray(image_path)

            # Сохраняем изображение в буфер
            img_buffer = io.BytesIO()
            pil_image.save(img_buffer, format='JPEG')
            img_data = img_buffer.getvalue()
            img_buffer.close()

            # Создаем объект Image для messenger_bot_api
            image_obj = Image(f"detected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg", img_data)
            # Читаем файл изображения
            # with open(image_path, 'rb') as f:
            #     image_data = f.read()
            #
            # # Создаем объект Image
            # image = Image(os.path.basename(image_path), image_data)

            # Отправляем сообщение
            self.bot._request.send_image_message(
                self.workspace_id,
                self.group_id,
                image_obj,
                MessageRequest(caption)
            )

            self.logger.info(f"✅ Фото отправлено в TDM: {os.path.basename(image_path)}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки в TDM: {e}")
            return False

    def start_bot(self):
        """Запуск бота (для асинхронной работы)"""
        self.bot.start()


# Создаем глобальный экземпляр бота
tdm_bot_instance = TDMBot()


def initialize_tdm_bot():
    """Инициализация TDM бота"""
    return tdm_bot_instance