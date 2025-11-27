from ultralytics import YOLO
import cv2
import os
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import logging

# Настройка логирования
logger = logging.getLogger(__name__)


class TruckDetector:
    # def __init__(self, model_path='yolov8n.pt'):  # -------------- разные модели
    # def __init__(self, model_path='yolov8s.pt'):    #--------------- ПОКА круче других -----
    # def __init__(self, model_path='yolov8m.pt'):
    def __init__(self, model_path='yolov8l.pt'):
        """
        Инициализация детектора.
        При первом запуске модель 'yolov8n.pt' будет автоматически скачана.
        """
        logger.info(f"Инициализация детектора с моделью: {model_path}")
        self.model = YOLO(model_path)  # Загрузка предобученной модели

    def detect_truck(self, image_path, conf_threshold=0.8):
        """
        Обнаруживает грузовики на изображении.

        Args:
            image_path (str): Путь к файлу изображения.
            conf_threshold (float): Порог уверенности (от 0.0 до 1.0).

        Returns:
            list: Список результатов обнаружения.
            PIL.Image: Изображение с нарисованными bounding boxes.
        """
        logger.info(f"Начало детекции: {image_path}, порог: {conf_threshold}")

        try:
            # Выполнение inference (предсказания)
            results = self.model.predict(source=image_path, conf=conf_threshold, save=False, verbose=False)

            # Открываем изображение с помощью Pillow для последующей отрисовки
            image = Image.open(image_path)
            # Конвертируем в RGB (если это не так)
            image_rgb = image.convert('RGB')
            # Конвертируем в формат OpenCV (BGR) для отрисовки
            image_cv = cv2.cvtColor(np.array(image_rgb), cv2.COLOR_RGB2BGR)

            # Список для хранения найденных грузовиков
            found_trucks = []

            # Обрабатываем результаты (предполагаем, что обрабатываем одно изображение)
            for result in results:
                # Проверяем, есть ли обнаруженные объекты
                if result.boxes is not None:
                    # Получаем bounding boxes, confidence scores и class IDs
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy().astype(int)

                    # Получаем имена классов из модели
                    class_names = result.names

                    for box, conf, class_id in zip(boxes, confidences, class_ids):
                        class_name = class_names[class_id]

                        # Проверяем, является ли объект грузовиком
                        # В COCO dataset (на котором обучена YOLO) класс 'truck' имеет id 7.
                        # Также можно искать по имени: 'truck', 'car', 'bus' и т.д.
                        # if class_name.lower() in ['truck', 'lorry', 'car', 'bus']:  # Можно расширить список
                        if class_name.lower() in ['truck', 'lorry',]:  # Можно расширить список
                        # if class_name.lower() in ['bus']:  # Можно расширить список
                        # if class_id == 7: # Альтернативный вариант: проверка по ID класса 'truck' в COCO
                            label = f"{class_name} {conf:.2f}"

                            # Рисуем bounding box и label на изображении
                            x1, y1, x2, y2 = map(int, box)
                            # cv2.rectangle(image_cv, (x1, y1), (x2, y2), (0, 255, 0), 2) #--------- зелен
                            cv2.rectangle(image_cv, (x1, y1), (x2, y2), (0, 0, 255), 5)
                            cv2.putText(image_cv, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 5)

                            found_trucks.append({
                                "class": class_name,
                                "confidence": float(conf),
                                "bbox": [int(x1), int(y1), int(x2), int(y2)]
                            })

            # Конвертируем обратно в RGB для отображения через matplotlib
            image_with_boxes = cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB)
            return found_trucks, image_with_boxes

        except Exception as e:
            logger.error(f"Ошибка при детекции {image_path}: {e}")
            raise

    def show_result(self, image_with_boxes):
        """Показывает результат с помощью matplotlib."""
        try:
            plt.figure(figsize=(10, 10))
            plt.imshow(image_with_boxes)
            plt.axis('off')
            plt.show()
            logger.debug("Результат детекции отображен")
        except Exception as e:
            logger.error(f"Ошибка при отображении результата: {e}")

def load_file_jpg():
    '''Сбор в список файлов jpg из folder_path'''

    # folder_path = 'c:/Users/TurchinMV/Downloads/truck_foto'
    folder_path = '/home/adm_1/foto_catcher/fc_media'
    logger.info(f"Сканирование директории: {folder_path}")

    jpg_files = []
    try:
        with os.scandir(folder_path) as entries:
            for entry in entries:
                if entry.is_file() and entry.name.lower().endswith('.jpg'):
                    jpg_files.append(entry.name)
        logger.info(f"Найдено {len(jpg_files)} JPG файлов")
    except Exception as e:
        logger.error(f"Ошибка при сканировании директории: {e}")

    return jpg_files

# Пример использования
if __name__ == "__main__":
    # Инициализация логирования
    from logging_config import setup_logging

    setup_logging()

    detector = TruckDetector()
    file_list = load_file_jpg()

    for i_foto in file_list:
        image_path = f'/home/adm_1/foto_catcher/fc_media/{i_foto}'
        trucks, annotated_image = detector.detect_truck(image_path, conf_threshold=0.6)

        if trucks:
            logger.info(f"Файл {i_foto}: найдено {len(trucks)} грузовиков/машин")
            for i, truck in enumerate(trucks, 1):
                logger.info(f"Объект {i}: {truck['class']} (уверенность: {truck['confidence']:.2f})")
        else:
            logger.info(f"Файл {i_foto}: грузовики не обнаружены")

