import imaplib
import email
from email.header import decode_header
import base64
from bs4 import BeautifulSoup
import re
import pandas as pd
import os
from sqlalchemy import create_engine, inspect
import paramiko
from paramiko import SFTPClient
from email.utils import parsedate_to_datetime
import logging
from config import DB_CONFIG
import config

''' Файл для сбора данных из почтового ящика .... '''

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/fotocatcher/mail_pusher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)



class Camera_trap:

    def __init__(self, login, password, imap_server):
        self.login = login
        self.password = password
        self.mail = imaplib.IMAP4_SSL(imap_server, 993)

    def get_connection_folder(self, mailbox):
        try:
            self.mail.login(self.login, self.password)
            self.mail.select(mailbox)
            logger.info(f"Успешное подключение к папке: {mailbox}")
        except Exception as e:
            logger.error(f"Ошибка подключения к папке {mailbox}: {e}")
            raise

    def get_letters(self):
        statuses, messages = self.mail.uid('search', None, 'UNSEEN')
        email_uids = messages[0].split()
        msg_data_all = []
        for email_uid in email_uids:
            status, msg_data = self.mail.uid('fetch', email_uid, '(RFC822)')  # Получаем письмо по UID
            msg_data_all.append(msg_data[0])
        return msg_data_all

    def get_time_getting(self, msg_data_all):  # доп
        time_get = []
        for response in msg_data_all:
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])
                date_str = msg['Date']
                dt = parsedate_to_datetime(date_str)
                time_only = dt.time()
                time_get.append(time_only)
        return time_get

    def get_subjects(self, msg_data_all):
        subjects_all = []
        times = []
        for response in msg_data_all:
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])
                subject, encoding = decode_header(msg['Subject'])[0] if msg['Subject'] else ('Без темы',
                                                                                             None)  # Получаем информацию о письме
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8')
                subjects_all.append(subject)
                # pattern = r'\d{2}:\d{2}:\d{2}'
                pattern = r'\d+:\d{2}:\d{2}'
                time = re.search(pattern, subject)
                time = time.group()
                times.append(time)

        return subjects_all, times

    def download_attachments(self, msg_data_all, remote_folder, ssh_host, ssh_username, ssh_password, ssh_port):
        filenames = []
        filepathes = []

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(
            hostname=ssh_host,
            username=ssh_username,
            password=ssh_password,
            port=ssh_port
        )
        sftp = ssh.open_sftp()
        sftp.chdir(remote_folder)

        for response in msg_data_all:
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])
                if msg.get_content_maintype() == 'multipart':
                    for part in msg.walk():
                        if part.get_content_maintype() == 'multipart':
                            continue
                        if part.get('Content-Disposition') is None:
                            continue

                        filename = part.get_filename()  # Получаем имя файла
                        if filename:
                            # Декодируем имя файла
                            decoded_name = decode_header(filename)[0][0]
                            if isinstance(decoded_name, bytes):
                                filename = decoded_name.decode()
                            else:
                                filename = decoded_name
                            filenames.append(filename)

                            # filepath = os.path.join(remote_folder, filename)  # Сохраняем файл
                            filepath = f"{remote_folder}/{filename}"

                            if any(ext in filename.lower() for ext in
                                   ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.mp4', '.avi', '.mov',
                                    '.doc']):  # Проверяем тип файла
                                with sftp.file(filepath, 'wb') as f:
                                    f.write(part.get_payload(decode=True))
                            filepathes.append(filepath)
        sftp.close()
        return filenames, filepathes

    def get_text_letters(self, msg_data_all):
        text_all = []
        for response in msg_data_all:
            text_content = ''
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])
                if msg.get_content_maintype() == 'multipart':
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                text_content += payload.decode('utf-8')

                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        text_content = payload.decode('utf-8')
                text_all.append(text_content)
        return text_all


def parse_device_data(text_data):
    data = {}

    # Регулярные выражения для извлечения данных
    patterns = {
        'date': r'Date:([^\n]+)',
        'signal': r'Signal:([^\n]+)',
        'battery': r'Battery:([^\n]+)',
        'temperature': r'Temperature:([^\n]+)',
        'total_photos': r'Total photos:(\d+)',
        'total_videos': r'Total videos:(\d+)',
        'total_space': r'Total space:(\d+M)',
        'free_space': r'Free space:(\d+M)',
        'imei': r'IMEI/MEID:(\d+)'
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text_data)
        if match:
            data[key] = match.group(1).strip()

    return data

class Transfer:

    def __init__(self, dataframe, table_name, db_connection_string):
        self.dataframe = dataframe
        self.table_name = table_name
        self.db_connection_string = db_connection_string
        self.engine = create_engine(self.db_connection_string)

    def get_old_data_count(self):
        inspector = inspect(self.engine)
        table_exists = self.table_name in inspector.get_table_names()

        if table_exists:
            query = f"SELECT COUNT(*) as count FROM {self.table_name}"
            result = pd.read_sql(query, self.engine)
            return result['count'].iloc[0]
        else:
            return 0

    def to_database(self):
        try:
            self.dataframe.to_sql(
                self.table_name,
                self.engine,
                if_exists='append',
                index=False,
                method='multi'
            )
            logger.info("Данные успешно записаны в БД")
        except Exception as e:
            logger.error(f"Ошибка записи в БД: {e}")
            raise
        # Получаем новое количество записей
        new_count = self.get_old_data_count()
        added_count = new_count - self.old_count
        print(f"Добавлено {added_count} записей в таблицу {self.table_name}")

    def make(self):
        self.old_count = self.get_old_data_count()
        self.to_database()


if __name__ == "__main__":
    logger.info("Запуск скрипта проверки почты")
    
    ssh_host = DB_CONFIG['host']
    ssh_username = config.SSH_USERNAME
    ssh_password = config.SSH_PASSWORD
    ssh_port = 22
    remote_folder = '/home/adm_1/foto_catcher/fc_media'

    try:
#        test = Camera_trap(login=config.LOGIN_MAIL, password=config.PASSWORD_MAIL, imap_server="imap.yandex.ru")
#        test = Camera_trap(login=config.LOGIN_MAIL, password=config.PASSWORD_MAIL, imap_server="imap.mail.ru")
        test = Camera_trap(login=config.LOGIN_MAIL, password=config.PASSWORD_MAIL, imap_server="owa.mos.ru")


        test.get_connection_folder('foto_catch')
        letters = test.get_letters()
        
        logger.info(f"Найдено новых писем: {len(letters)}")
        
        if letters:
            logger.info("Обработка писем...")
            subjects, time = test.get_subjects(letters)
            time_get = test.get_time_getting(letters)
            filename, filepath = test.download_attachments(letters, remote_folder, ssh_host, ssh_username, ssh_password,
                                                           ssh_port)
            text = test.get_text_letters(letters)
            
            df = pd.DataFrame({
                'subject': subjects,
                'time_accident': time,
                'time_getting': time_get,
                'filename': filename,
                'filepath': filepath,
                'text': text
            })

            parsed_df = df['text'].apply(parse_device_data).apply(pd.Series)
            df = pd.concat([df, parsed_df], axis=1)
            df['info_detect'] = None

            # в базу данных
            db_connection = f'postgresql://{DB_CONFIG["user"]}:{DB_CONFIG["password"]}@{DB_CONFIG["host"]}:{DB_CONFIG["port"]}/{DB_CONFIG["database"]}'
            table_name = 'fotos_data'

            foto = Transfer(df, table_name, db_connection)
            foto.make()
            
            logger.info(f"Успешно добавлено {len(df)} записей в БД")
        else:
            logger.info("Новых писей не найдено")
            
    except Exception as e:
        logger.error(f"Ошибка при выполнении скрипта: {e}")
        raise