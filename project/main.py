import telebot
import logging
from telebot.types import Message, BotCommand
from CONSTS import (
    MAX_TOKENS_PER_DAY,
    API_TOKEN,
    LOGS,
    TRANSLATE,
    DEFAULT_MODEL,
    VALUES
)
from threading import Thread
from datetime import datetime
from settings_manager import load_settings, dump_settings
from weather import get_weather
from chat_manager import create_database, add_message, get_history, count_tokens, reset_tokens
from ai import ask_gpt, transcript_audio
from keyboard import create_keyboard
import os


bot = telebot.TeleBot(API_TOKEN)


def register_comands():
    comm = [
        BotCommand("start", "Начать сессию"),
        BotCommand("help", "Помощь"),
        BotCommand("feedback", "Оставить отзыв"),
        BotCommand("settings", "Изменить/посмотреть настройки")]
    bot.set_my_commands(comm)


def reset_users_tokens():
    reset_day = datetime.now().day
    while True:
        c_day = datetime.now().day

        if c_day != reset_day:
            reset_tokens()


def add_user(user_id):
    global settings
    settings[str(user_id)] = {'model': DEFAULT_MODEL,
                              'system_prompt': 'По умолчанию'}


@bot.message_handler(commands=['feedback'])
def get_feedback(msg: Message):
    user_id = msg.from_user.id
    bot.send_message(user_id, 'Теперь ты можешь написать отзыв о боте!')
    bot.register_next_step_handler(msg, write_feedback)


def write_feedback(msg):
    user_id = msg.from_user.id
    with open('creds/feedback.txt', 'a') as f:
        f.write(f'{user_id}: {msg.text}\n')
        bot.send_message(user_id, 'Спасибо за отзыв!')


@bot.message_handler(commands=['start'])
def send_welcome(msg: Message):
    bot.reply_to(msg, "Привет! Я бот с нейросетью, но я также могу говорить погоду в городах. Напиши /help, "
                 "чтобы узнать список команд!")
    add_user(user_id=msg.chat.id)
    register_comands()


@bot.message_handler(commands=['help'])
def send_help(msg: Message):
    if not settings.get(str(msg.chat.id)):
        send_welcome(msg)
        return
    bot.reply_to(msg, "Список команд:\n"
                 "/weather - узнать погоду в городе\n"
                 "/settings - настройки\n"
                 "/feedback - оставить отзыв\n")


@bot.message_handler(commands=['weather'])
def weather(msg: Message):
    user_id = msg.chat.id
    if not settings.get(str(user_id)):
        send_welcome(msg)
        return
    bot.send_message(user_id, "Хорошо! Отправь название своего города, а я отправлю тебе погоду!")
    bot.register_next_step_handler(msg, send_weather)


def send_weather(msg: Message):
    user_id = msg.chat.id
    responce, e = get_weather(msg.text)
    if e:
        bot.send_message(user_id, f'Ошибка: {e}')
    else:
        bot.send_message(user_id, responce)


@bot.message_handler(commands=['settings'])
def show_settings(msg: Message):
    user_id = msg.chat.id
    if not settings.get(str(user_id)):
        add_user(user_id)
    usr_st = ''
    for k, v in settings[str(user_id)].items():
        k = TRANSLATE[k]
        v = TRANSLATE[v] if TRANSLATE.get(v) else v
        usr_st += f'\n{k} - {v}'
    bot.send_message(user_id, f'Ваши настройки: {usr_st}', reply_markup=create_keyboard(('Изменить настройки',)))
    bot.register_next_step_handler(msg, change_settings_handler_1)


def change_settings_handler_1(msg: Message):
    user_id = msg.chat.id

    if msg.text == 'Изменить настройки':
        bot.send_message(user_id, 'Выбери, какую настройку изменить:',
                         reply_markup=create_keyboard((TRANSLATE[i] for i in settings[str(user_id)])))
        bot.register_next_step_handler(msg, change_settings_handler_2)
    else:
        handle_text(msg)


def change_settings_handler_2(msg: Message):
    user_id = msg.chat.id

    try:
        TRANSLATE[msg.text]

    except Exception as e:
        logging.info(e)
        bot.send_message(user_id, 'Что-то я не понял. Давай по новой:')
        bot.send_message(user_id, 'Выбери, какую настройку изменить:',
                         reply_markup=create_keyboard((TRANSLATE[i] for i in settings[str(user_id)])))
        bot.register_next_step_handler(msg, change_settings_handler_2)
        return

    if TRANSLATE[msg.text] in settings[str(user_id)].keys():
        bot.send_message(user_id, f'Выбери значение для параметра {msg.text}',
                         reply_markup=create_keyboard(VALUES[msg.text]))
        bot.register_next_step_handler(msg, set_settings, msg.text)


def set_settings(msg: Message, param):
    user_id = msg.chat.id

    if msg.text in VALUES[param]:
        settings[str(user_id)][TRANSLATE[param]] = msg.text
        bot.send_message(user_id, f'Значение {param} успешно заменено на {msg.text}')
        dump_settings(settings)

    else:
        bot.send_message(user_id, 'Ты написал какую-то билеберду. Давай еще раз:')
        bot.send_message(user_id, f'Выбери значение для параметра {param}',
                         reply_markup=create_keyboard(VALUES[param]))
        bot.register_next_step_handler(msg, set_settings, param)


@bot.message_handler(content_types=['audio'])
def handle_audio(msg):
    bot.send_message(msg.chat.id, "Классная музыка... Добавлю в свой плейлист!")


@bot.message_handler(content_types=['document'])
def handle_document(msg):
    bot.send_message(msg.chat.id, "Чтож, это документ. Спасибо.")


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_message(message.chat.id, "Вау, вот это фоторграфия! Когда мой разработчик научит меня видеть "
                                      "изображения, я смогу поговорить о ней с тобой.")


@bot.message_handler(content_types=['sticker'])
def handle_sticker(message):
    bot.send_message(message.chat.id, "Прикольный стикер! Добавлю в избранное.")


@bot.message_handler(content_types=['video'])
def handle_video(message):
    bot.send_message(message.chat.id, "Это видео квадратное!")


@bot.message_handler(content_types=['video_note'])
def handle_video_note(message):
    bot.send_message(message.chat.id, "Это видео круглое!")


@bot.message_handler(content_types=['location'])
def handle_location(message):
    bot.send_message(message.chat.id, "Красивое место, я бы хотел там отдохнуть.")


@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    bot.send_message(message.chat.id, "Я обязательно ему напишу!")


@bot.message_handler(content_types=['text', 'voice'])
def handle_text(msg: Message):
    user_id = msg.from_user.id
    if not settings.get(str(user_id)):
        send_welcome(msg)
        return

    if msg.voice:
        f_id = msg.voice.file_id
        f_path = bot.get_file(f_id).file_path
        f_d = bot.download_file(f_path)
        with open(f'voice_{f_id}.ogg', 'ab') as f:
            f.write(f_d)

        with open(f'voice_{f_id}.ogg', 'rb') as f:
            msg.text = transcript_audio(f)

        os.remove(f'voice_{f_id}.ogg')

    if count_tokens(user_id) >= MAX_TOKENS_PER_DAY:
        bot.send_message(user_id, 'Извините, бесплатные токены на сегодня закончились, '
                                  'но они начислятся в 00:00 по Москве!')
        return

    if msg.text[0] == '/':
        bot.send_message(user_id, "К сожалению, такой команды у нас еще нет. Вот список команд:\n"
                         "/weather - узнать погоду в городе\n"
                         "/settings - настройки\n"
                         "/feedback - оставить отзыв\n")
        return

    add_message(user_id, (msg.text, 'user', 0))
    chat_history = get_history(user_id)

    status, answer, answer_tokens = ask_gpt(chat_history, settings[str(user_id)]['model'],
                                            settings[str(user_id)]['system_prompt'])

    if status:
        bot.send_message(user_id, answer + f"\n(Потрачено токенов: {answer_tokens})" +
                         (f'\nВы сказали: {msg.text}' if msg.voice else ''))
        add_message(user_id, (answer, 'assistant', answer_tokens))
    else:
        bot.send_message(user_id, 'Извините, что-то пошло не так')


if __name__ == '__main__':
    register_comands()
    Thread(target=reset_users_tokens).start()
    settings = load_settings()
    create_database()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H",
        filename=LOGS,
        filemode="a",
        encoding="utf-8",
        force=True)
    bot.infinity_polling()
