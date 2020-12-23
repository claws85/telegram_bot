import datetime
import logging
import re
import requests
import shutil
import time

from config import (
    IMGFLIP_USERNAME,
    IMGFLIP_PASSWORD,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID
)

logging.basicConfig(filename='telegrambot.log', level=logging.INFO)

# TODO: Put IMGflip and Telegram functions into classes?

get_memes_url = 'https://api.imgflip.com/get_memes'
caption_image_url = 'https://api.imgflip.com/caption_image'

local_meme_filepath = './edited_meme.jpg'

telegram_url = 'https://api.telegram.org/bot{}/'.format(TELEGRAM_BOT_TOKEN)


def main():

    latest_update_id = None

    # listen for new messages
    while True:
        try:
            # return all available updates our bot has received
            updates = get_updates(latest_update_id)

            if len(updates['result']) > 0:

                latest_update_id = get_latest_update_id(updates)

                message_text = extract_update_text(updates, latest_update_id)

                # check request is to create a meme or return meme info
                if 'memelist' in message_text.lower():
                    meme_info = get_latest_meme_info()
                    meme_list = get_meme_list(meme_info)
                    send_text(meme_list)

                if 'makememe' in message_text.lower():
                    imgflip_params = parse_message(message_text)

                    meme_url = create_meme(
                        imgflip_params[0],
                        imgflip_params[1]
                    )

                    save_edited_meme(meme_url, local_meme_filepath)

                    send_photo(local_meme_filepath)

                latest_update_id = latest_update_id + 1

        except Exception as e:
            # reset out latest_update_id variable
            latest_update_id = None

            print(e)
            dt = datetime.datetime.now().strftime("%x %X")
            logging.error(
                "The following error occurred at {}:\n{}\n".format(dt, e)
            )
            try:
                send_text(
                    "Sorry, an error was encountered. Details will be "
                    "available in the logs file."
                )
            except Exception as e:
                logging.error("Unable to send error message to users "
                              "at {}\n".format(datetime))



def send_text(text):
    """Sends some text via our bot to the chosen group"""
    url = telegram_url + 'sendMessage'
    data = {'chat_id': TELEGRAM_CHAT_ID,
            'text': text}
    r = requests.post(url, data=data)
    if r.status_code == 200:
        dt = datetime.datetime.now().strftime("%x %X")
        logging.info("Text sent to group successfully at {}.\n".format(dt))



def send_photo(filepath):
    """Sends a picture via our bot to the chosen Telegram group."""
    url = telegram_url + 'sendPhoto'
    data = {'chat_id': TELEGRAM_CHAT_ID}
    files = {"photo": open(filepath, 'rb')}
    r = requests.post(url, data=data, files=files)
    if r.status_code == 200:
        dt = datetime.datetime.now().strftime("%x %X")
        logging.info("Image sent to group successfully at {}.\n".format(dt))


def get_updates(offset=None):
    """If no offset provided, will return all available updates
    sent to the bot. If offset is provided, then only messages equal to
    that offset will be returned. Date returned in json format"""
    url = telegram_url + 'getUpdates?timeout=1'
    if offset:
        url = url + '&offset={}'.format(offset)

    return requests.get(url).json()


def get_latest_update_id(updates):
    """Cycles through the json updates data and returns
    the id of the latest update."""

    ids = []
    for update in updates['result']:
        ids.append(update['update_id'])

    return max(ids)


def extract_update_text(updates, latest_update_id):
    """Returns the text included in the latest update"""
    message_text = ''

    for upd in updates['result']:
        if upd['update_id'] == latest_update_id:
            message_text = upd['message']['text']

    return message_text


def parse_message(message):
    """Extracts from the message text the meme template_id
    and list of meme box texts. Returns data in a tuple"""

    template_id = re.search(r'\d+', message)[0]

    texts = re.findall('“(.*?)”', message)

    return template_id, texts


def get_latest_meme_info():
    """Contacts Telegram api and returns json data listing
    the top memes currently available on imgflip"""
    r = requests.get(get_memes_url)
    if r.status_code == 200:
        dt = datetime.datetime.now().strftime("%x %X")
        logging.info("Meme list retrieved successfully at {}.\n".format(dt))
    return r.json()


def get_meme_list(meme_info):
    """Returns a string containing all meme names, ids and
    number of text boxes per meme. Newlines added so
    strings appear correctly when sent to user via Telegram"""
    meme_list = ''
    for meme in meme_info['data']['memes']:
        meme_list += meme['name'] + ': ' + meme['id'] \
                     + ', ' + str(meme['box_count']) + '\n'
    return meme_list


def create_meme(id, args):
    """Creates a meme by contacting the Telegram api and returns
    the url pointing to the jpg. Takes the meme template id as a
    positional arg and the message text as args"""
    data = {
        'username': IMGFLIP_USERNAME,
        'password': IMGFLIP_PASSWORD,
        'template_id': id
    }

    enum = enumerate(args)

    for tup in enum:
        data['boxes[{}][text]'.format(tup[0])] = tup[1]

    r = requests.post(
        caption_image_url,
        data=data
    )
    if r.status_code == 200:
        dt = datetime.datetime.now().strftime("%x %X")
        logging.info(
            "Meme with text '{}' created successfully "
            "at {}.\n".format(args, dt)
        )

    return r.json()['data']['url']


def save_edited_meme(url, filepath):
    """Takes the url where the image is located and saves it"""
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        dt = datetime.datetime.now().strftime("%x %X")
        logging.info(
            "New meme data retrieved successfully at {}.\n".format(dt)
        )

    with open(filepath, 'wb') as f:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, f)


if __name__ == '__main__':
    main()
