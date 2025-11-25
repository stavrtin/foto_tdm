# analyze_photos.py
import psycopg2
import json
import os
from datetime import datetime

import config
from truck_detector import TruckDetector
from telegram_bot import TelegramBot  # Импортируем новый класс
from test_tdm import initialize_tdm_bot, tdm_bot_instance  # Импортируем TDM бот


DB_CONFIG = config.DB_CONFIG
TELEGRAM_CONFIG = config.TELEGRAM_CONFIG  # Конфиг Telegram

# Инициализируем бота один раз
telegram_bot = TelegramBot(TELEGRAM_CONFIG['token'], TELEGRAM_CONFIG['chat_id'])
tdm_bot = initialize_tdm_bot()  # Инициализируем TDM бот

def find_file_case_insensitive(filename, directory):
    """Поиск файла без учета регистра"""
    if os.path.exists(os.path.join(directory, filename)):
        return os.path.join(directory, filename)

    for file in os.listdir(directory):
        if file.lower() == filename.lower():
            return os.path.join(directory, file)
    return None


def send_to_both_bots(image_with_boxes, caption):
    """
    Отправка изображения и текста в оба бота одновременно
    """
    # Отправка в Telegram
    telegram_success = telegram_bot.send_photo(image_with_boxes, caption)

    # Отправка в TDM
    tdm_success = tdm_bot.send_photo_with_caption(image_with_boxes, caption)

    return telegram_success, tdm_success



def analyze_photos():
    """Основная функция анализа фотографий"""

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Получаем необработанные фотографии
        cursor.execute("""
            SELECT filename FROM fotos_data 
            WHERE info_detect IS NULL OR info_detect = ''
        """)

        undetected_files = cursor.fetchall()

        if not undetected_files:
            print("✅ Все фотографии уже обработаны")
            return

        print(f"📷 Найдено {len(undetected_files)} необработанных фотографий")

        detector = TruckDetector()
        processed_count = 0
        base_dir = 'c:/Users/TurchinMV/Downloads/truck_foto/foto_catcher/'
        # base_dir = '/home/adm_1/foto_catcher/fc_media'

        for (filename,) in undetected_files:
            try:
                file_conn = psycopg2.connect(**DB_CONFIG)
                file_cursor = file_conn.cursor()

                # Поиск файла без учета регистра
                filepath = find_file_case_insensitive(filename, base_dir)

                if not filepath:
                    print(f"⚠️ Файл не найден: {filename} в директории {base_dir}")
                    file_cursor.close()
                    file_conn.close()
                    continue

                print(f"🔍 Анализируем: {os.path.basename(filepath)}")

                # Детекция объектов
                trucks, image_with_boxes = detector.detect_truck(filepath, conf_threshold=0.6)

                # Формируем результаты
                detection_results = [(truck['class'], float(truck['confidence'])) for truck in trucks]

                # Проверяем, есть ли грузовики
                has_truck = any(object[0] == 'truck' for object in detection_results)

                for object in detection_results:
                    if object[0] == 'truck':
                        print(f'truck = {object[1]}')

                # Получаем данные из БД
                cursor.execute(f"SELECT imei, time_accident FROM fotos_data WHERE filename = %s", (filename,))
                row_data_file = cursor.fetchall()

                # if row_data_file:
                output_message = f'В {row_data_file[0][1]} ловушкой {row_data_file[0][0]} был обнаружен объект "Грузовик"'
                #     # print(f'{output_message=}')

                # Отправляем сообщение в Telegram только если найден грузовик
                if has_truck:
                    # Отправляем текстовое сообщение
                    # telegram_bot.send_message(output_message)

                    # Отправляем изображение с bounding boxes
                    photo_caption = (f"Обнаружен грузовик\n"
                                     f"Время обнаружения: {row_data_file[0][1]}\n"
                                     f"Ловушка: {row_data_file[0][0]} \n"
                                     f"Файл: {filename}\n"
                                     # f"Время cjj,otybz : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                                     )

                    # telegram_bot.send_photo(image_with_boxes, photo_caption)
                    # Отправляем в оба бота одновременно
                    telegram_success, tdm_success = send_to_both_bots(image_with_boxes, photo_caption)


                # Обновляем запись в БД
                info_detect = {
                    'файл': filename,
                    'реальный_файл': os.path.basename(filepath),
                    'детекции': detection_results,
                    'время_анализа': datetime.now().isoformat()
                }

                file_cursor.execute(
                    "UPDATE fotos_data SET info_detect = %s WHERE filename = %s",
                    (json.dumps(info_detect, ensure_ascii=False), filename)
                )

                file_conn.commit()
                processed_count += 1
                print(f"✅ Обновлено: {filename} - найдено {len(detection_results)} объектов")

                file_cursor.close()
                file_conn.close()

            except Exception as e:
                print(f"❌ Ошибка при анализе {filename}: {e}")
                if 'file_conn' in locals():
                    file_cursor.close()
                    file_conn.close()
                continue

        print(f"🎉 Обработка завершена. Обработано {processed_count} фотографий")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()


if __name__ == "__main__":
    analyze_photos()