# analyze_photos.py

# Импортируем настройку логирования
from logging_config import setup_logging

import psycopg2
import json
import os
from datetime import datetime

import config
from truck_detector import TruckDetector
from telegram_bot import TelegramBot  # Импортируем новый класс
from tdm_bot import initialize_tdm_bot  # Импортируем TDM бот

from config import TDM_DICT

# Настраиваем логирование  ОДИН РАЗ в главном скрипте
setup_logging()
import logging
logger = logging.getLogger(__name__)

DB_CONFIG = config.DB_CONFIG
TELEGRAM_CONFIG = config.TELEGRAM_CONFIG  # Конфиг Telegram

# Инициализируем бота один раз
telegram_bot = TelegramBot(TELEGRAM_CONFIG['token'], TELEGRAM_CONFIG['chat_id'])
tdm_bot = initialize_tdm_bot()  # Инициализируем TDM бот

# def find_file_case_insensitive(filename, directory):
#     """Поиск файла без учета регистра"""
#     logger.debug(f"Поиск файла {filename} в {directory}")
#
#     if os.path.exists(os.path.join(directory, filename)):
#         return os.path.join(directory, filename)
#
#     for file in os.listdir(directory):
#         if file.lower() == filename.lower():
#             return os.path.join(directory, file)
#
#     logger.warning(f"Файл {filename} не найден в {directory}")
#
#     return None


def send_to_both_bots(image_path, caption, id_foto_catch):
    """
    Автоматическая отправка изображения и текста в оба бота одновременно
    """
    logger.info(f"Отправка в боты: {caption[:15]}...")

    results = []

    # Отправка в Telegram
    try:
        telegram_success = telegram_bot.send_photo(image_path, caption)
        results.append(("Telegram", telegram_success))
        if telegram_success:
            print("✅ Сообщение отправлено в Telegram")
            logger.info("✅ Сообщение отправлено в Telegram")
        else:
            print("❌ Не удалось отправить в Telegram")
            logger.warning("❌ Не удалось отправить в Telegram")
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")
        logger.error(f"❌ Ошибка отправки в Telegram: {e}")
        results.append(("Telegram", False))

    # Отправка в TDM (упрощенная версия)

    try:
        # tdm_success = tdm_simple_bot.send_photo_with_caption(image_path, caption)
        # tdm_success = tdm_bot.send_photo_with_caption(image_path, caption)

        # -------- выбираем из словаря ОКРУГОВ тот округ (калал ТЛМ), в котором стоит ловушка (по ID)
        group_id = None
        for i in TDM_DICT.keys():
            if id_foto_catch in TDM_DICT.get(i):
                group_id = i
                break

        if group_id is None:
            logger.warning(f"❌ Не найден group_id для ID ловушки: {id_foto_catch}")
            results.append(("TDM", False))
        else:
            tdm_success = tdm_bot.send_photo_with_caption(
                group_id=group_id,
                image_path=image_path,
                caption=caption
            )
            results.append(("TDM", tdm_success))
            if tdm_success:
                logger.info("✅ Сообщение отправлено в TDM")
            else:
                logger.warning("❌ Не удалось отправить в TDM")

    except Exception as e:
        logger.error(f"❌ Ошибка отправки в TDM: {e}")
        results.append(("TDM", False))

    return results



def analyze_date():
    """ функция анализа данных БД (память, батарея, неполучение фото более 3ч)"""
    logger.info("🚀 Запуск анализа фотографий")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Получаем необработанные фотографии
        cursor.execute(f"""
            SELECT 
                subject,
                time_accident,
                filename,
                date,
                battery,
                free_space,
                imei
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY imei ORDER BY date::date DESC, time_accident::time DESC) as row_num
                FROM fotos_data
            ) ranked
            WHERE row_num = 1
            AND CAST(REPLACE(free_space, 'M', '') AS INTEGER) < 4 * {config.FREE_MEMORY};
            """)

        list_device_of_low_memory = cursor.fetchall()

        # if not undetected_files:
        #     logger.info("✅ Все фотографии уже обработаны")
        #     return

        logger.info(f"📷 Найдено {len(list_device_of_low_memory)} устройств с критически низким объемом памяти")

        # detector = TruckDetector()
        # processed_count = 0
        # # base_dir = 'c:/Users/TurchinMV/Downloads/truck_foto/foto_catcher/'
        # base_dir = './fc_media/'
        # # base_dir = '/home/adm_1/foto_catcher/fc_media'

        for item_ in list_device_of_low_memory:
            date_last = item_[3]
            imei_id = item_[6]


            group_id = None
            for i in TDM_DICT.keys():
                if imei_id in TDM_DICT.get(i):
                    group_id = i
                    break

            tdm_success = tdm_bot.send_info_message(
                group_id=group_id,
                caption=f'В ловушке {imei_id} осталось места менне чем на {config.FREE_MEMORY} фото'
            )

            logger.info(f"Результаты отправки: {tdm_success}")


            # try:
            #     file_conn = psycopg2.connect(**DB_CONFIG)
            #     file_cursor = file_conn.cursor()
            #
            #     # Поиск файла без учета регистра
            #     filepath = find_file_case_insensitive(filename, base_dir)
            #
            #     if not filepath:
            #         print(f"⚠️ Файл не найден: {filename} в директории {base_dir}")
            #         logger.warning(f"⚠️ Файл не найден: {filename} в директории {base_dir}")
            #         file_cursor.close()
            #         file_conn.close()
            #         continue
            #
            #     print(f"🔍 Анализируем: {os.path.basename(filepath)}")
            #     logger.info(f"🔍 Анализируем: {os.path.basename(filepath)}")
            #
            #     # Детекция объектов
            #     trucks, image_with_boxes = detector.detect_truck(filepath, conf_threshold=0.6)
            #
            #     # Формируем результаты
            #     detection_results = [(truck['class'], float(truck['confidence'])) for truck in trucks]
            #
            #     # Проверяем, есть ли грузовики
            #     has_truck = any(object[0] == 'truck' for object in detection_results)
            #
            #     for object in detection_results:
            #         if object[0] == 'truck':
            #             print(f'truck = {object[1]}')
            #
            #     # Получаем данные из БД
            #     # cursor.execute(f"SELECT imei, time_accident, date FROM fotos_data WHERE filename = %s", (filename,))
            #     cursor.execute(
            #         "SELECT time_accident, date, imei FROM fotos_data WHERE filename = %s AND imei = %s",
            #         (filename, imei_id)
            #                     )
            #     row_data_file = cursor.fetchall()
            #
            #     # if row_data_file:
            #     output_message = f'В {row_data_file[0][1]} ловушкой {row_data_file[0][0]} был обнаружен объект "Грузовик"'
            #     #     # print(f'{output_message=}')
            #
            #     # Отправляем сообщение в Telegram только если найден грузовик
            #     if has_truck:
            #         # Отправляем текстовое сообщение
            #         # telegram_bot.send_message(output_message)
            #         # Отправляем изображение с bounding boxes
            #         photo_caption = (f"Локация:\t'----'\n"
            #                          f"Дата:\t\t{row_data_file[0][1]}\n"
            #                          f"Время:\t\t{row_data_file[0][0]}\n"
            #                          f"ID ловушки:\t{row_data_file[0][2][-4:]} - {filename}")
            #
            #         # ----- id ЛОВУШКИ ----------------
            #         id_foto_catch = row_data_file[0][2]
            #
            #         # telegram_bot.send_photo(image_with_boxes, photo_caption)
            #         # Отправляем в оба бота одновременно
            #         send_results = send_to_both_bots(image_with_boxes, photo_caption, id_foto_catch)
            #         logger.info(f"Результаты отправки: {send_results}")
            #
            #
            #     # Обновляем запись в БД
            #     info_detect = {
            #         'файл': filename,
            #         'реальный_файл': os.path.basename(filepath),
            #         'детекции': detection_results,
            #         'время_анализа': datetime.now().isoformat()
            #     }
            #
            #     file_cursor.execute(
            #         "UPDATE fotos_data SET info_detect = %s WHERE filename = %s",
            #         (json.dumps(info_detect, ensure_ascii=False), filename)
            #     )
            #
            #     file_conn.commit()
            #     processed_count += 1
            #     print(f"✅ Обновлено: {filename} - найдено {len(detection_results)} объектов")
            #     logger.info(f"✅ Обновлено: {filename} - найдено {len(detection_results)} объектов")
            #
            #     file_cursor.close()
            #     file_conn.close()

            # except Exception as e:
            #     logger.error(f"❌ Ошибка при анализе {filename}: {e}")
            #     if 'file_conn' in locals():
            #         file_cursor.close()
            #         file_conn.close()
            #     continue

        # print(f"🎉 Обработка завершена. Обработано {processed_count} фотографий")
        # logger.info(f"🎉 Обработка завершена. Обработано {processed_count} фотографий")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()


if __name__ == "__main__":
    analyze_date()