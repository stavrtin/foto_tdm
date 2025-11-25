import logging
import sys
import requests
from requests import get
from messenger_bot_api import *
import time

import arch_tdm.config

root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)
token = arch_tdm.config.TOKEN_TDM

workspace_id = arch_tdm.config.TARGET_WORKSPACE_ID
group_id = arch_tdm.config.TARGET_GROUPE_ID


rest = 'https://api.tdm.mos.ru'
sse = 'https://pusher.tdm.mos.ru'
file = 'https://fileupload.tdm.mos.ru'
logger = logging.getLogger('bot')
image_url = 'https://i.guim.co.uk/img/media/26392d05302e02f7bf4eb143bb84c8097d09144b/446_167_3683_2210/master/3683.jpg?width=1900&dpr=2&s=none'
image_response = requests.get(image_url)

def image_handler(event: MessageBotEvent):

    event.send_image_message(
                            # event.workspace_id,
                            workspace_id,
                            # arch_tdm.config.TARGET_GROUPE_ID,
                            group_id,
                            Image('3--6823.jpg', image_response.content),
    MessageRequest('Дата, время, ....'))

def main():
    bot = Application(token,
          {'api_base_url': rest,
                       'sse_base_url': sse,
                        'file_upload_base_url': file})

    bot.add_handler(CommandHandler('send_image', image_handler))
    # bot.add_handler(CommandHandler('send_video', video_handler))

    bot.start()
if __name__ == '__main__':
    main()

