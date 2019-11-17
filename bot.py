#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import copy
import logging
import random
from aiohttp import web
import telebot
from functools import reduce
import json
from telebot import types
import config

API_TOKEN = config.API_TOKEN
bot = telebot.TeleBot(API_TOKEN)
app = web.Application()
admin = config.admin


def get_logger():
    logger = logging.getLogger(config.debug_path)
    logger.setLevel(logging.DEBUG)

    fhdebug = logging.FileHandler("debug.log")
    fmtdebug = '%(asctime)s  - %(message)s'
    formatterdebug = logging.Formatter(fmtdebug)
    fhdebug.setFormatter(formatterdebug)
    logger.addHandler(fhdebug)

    return logger


logger = get_logger()
logger.debug('Игра запущена')


def save_data():
    history = open('base.txt', 'w')
    json.dump(data, history, ensure_ascii=False)
    history.close()
    logger.debug('Data saved')


history = open('base.txt', 'r')
data = json.load(history)
history.close()
logger.debug('Данные загружены!')

# Process webhook calls
async def handle(request):
    #    if request.match_info.get('token') == bot.token:
    request_body_dict = await request.json()
    update = telebot.types.Update.de_json(request_body_dict)
    bot.process_new_updates([update])
    return web.Response()


app.router.add_post('/', handle)


# Handle '/start' and '/help'
@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    bot.reply_to(message, (
        """Здравствуй, внучка, а может быть внучек! Пришли мне, пожалуйста, свой адрес- ОБЯЗАТЕЛЬНО в нужном формате: 
        Имя, Фамилия, Улица, Дом, Квартира, Город, Индекс, номер телефона. И все это одним сообщением. """))


def r(prev: str, new: tuple):
    return prev + "\n" + str(new[0]) + ": " + str(new[1]["name"])


@bot.message_handler(commands=['list'])
def send_welcome(message):
    if message.chat.id == admin:
        bot.reply_to(message, reduce(r, data.items(), ''))
    else:
        bot.reply_to(message, 'А вам сюда не надо!')


@bot.message_handler(commands=['sort'])
def send_welcome(message):
    if message.chat.id == admin:
        for i in list(data.keys()):
            if not data[i]['approved']:
                del data[i]
                logger.debug('user %s deleted from base because "approved" is False' % data[i][name])
                save_data()
        users = list(data.keys())
        for santa in data.keys():
            try:
                grandchild = random.choice(list(filter(lambda a: a != santa, users)))
                data[santa]['grandchild'] = int(grandchild)
                data[grandchild]['santa'] = int(santa)
                users.remove(grandchild)
                logger.debug('Игроку %s назначен внучек %s' % (data[santa]['name'], data[grandchild]['name']))
                save_data()
            except IndexError:
                repl = random.choice(list(filter(lambda a: a != santa, list(data.keys()))))
                gr = copy.copy(data[repl]['grandchild'])
                data[santa]['grandchild'] = int(gr)
                data[gr]['santa'] = int(santa)
                data[repl]['grandchild'] = int(santa)
                data[santa]['santa'] = int(repl)
                logger.debug(
                    'Ой! У нас случился Коллапс Последнего Дедмороза. Сейчас мы это исправим. Забираем внучка у '
                    '%s, отдаем его бедняге %s, а самого Санту назначаем во внучки к ограбленному. Ура, '
                    'получилось.' % (data[repl]['name'], data[santa]['name']))
                save_data()

        for santa in data.keys():
            keyboard = types.InlineKeyboardMarkup()
            butt_sent = types.InlineKeyboardButton('Я отправил подарок!', callback_data='sent_%s' % message.chat.id)
            butt_receive = types.InlineKeyboardButton('Уииии! Я получил подарок!',
                                                      callback_data='receive_%s' % message.chat.id)
            keyboard.add(butt_sent, butt_receive)

            bot.send_message(santa, 'Дорогой %s' % data[santa]['name'] + ', адрес твоего получателя: ' +
                             data[data[santa]['grandchild']][
                                 'adr'] + '. Пожалуйста, будьте внимательны и аккуратны при '
                                          'заполнении почтового адреса ',
                             reply_markup=keyboard)
            logger.debug('Сообщение для %s отправлено' % data[santa]['name'])
            report = 'юзер ' + str(data[santa]['name']) + ' получил внучка ' + str(data[santa]['grandchild'])

            bot.send_message(admin, report)
        print('результат сортировки', data)
        logger.debug('Итоги сортировки: %s' % data)

    else:
        bot.reply_to(message, 'А вам сюда не надо!')


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    reply = call.data.split(sep='_', maxsplit=1)
    if reply[0] == "sent":
        bot.send_message(call.message.chat.id, 'Отлично! Ты - хороший Санта! А теперь пришли мне, пожалуйста, '
                                               'фото чека транспортной '
                                               'службы, где виден номер отправления. Спасибо!')
        data[call.message.chat.id]['sent'] = True
        logger.debug('%s отправил подарок!' % data[call.message.chat.id]['name'])
        bot.send_message(int(data[call.message.chat.id]['grandchild']), 'Ура! Твой Санта только-что отправил вам '
                                                                        'подарочек! Проверяй почтовый ящик, и не забудь '
                                                                        'нажать кнопочку "Получил", когда он дойдет до '
                                                                        'тебя!')

    if reply[0] == "receive":
        bot.send_message(call.message.chat.id, 'Замечательно! Надеюсь, подарочек тебе понравился и мы увидимся в '
                                               'следующем году! Счастливого нового года, дружище!')
        bot.send_message(int(data[call.message.chat.id]['santa']),
                         'Дорогой Санта! Твой подарочек только что был получен. '
                         'Ты - молодец!')
        data[call.message.chat.id]['received'] = True
        logger.debug('%s получил подарок!' % data[call.message.chat.id]['name'])
    if reply[0] == "yes":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="Пользователь %s теперь в игре! Ho-ho-ho!" % data[int(reply[1])]['name'])
        data[int(reply[1])]['approved'] = True
        bot.send_message(int(reply[1]), 'Ура! Вы в игре! Ho-ho-ho! Ожидайте адрес вашего внучка или внучки!')
        logger.debug('%s принят в игру администратором!' % data[call.message.chat.id]['name'])

    if reply[0] == "no":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="Пользователю %s отказано в участии." % data[int(reply[1])]['name'])
        bot.send_message(int(reply[1]), 'Администратор отказал вам в участии.'
                                        ' Возможно, вы заполнили адрес некорректно.')
        logger.debug('%s отказано в игре администратором!' % data[call.message.chat.id]['name'])
        del data[int(reply[1])]
    save_data()


@bot.message_handler(func=lambda message: True, content_types=['text'])
def process_msg(message):
    if message.chat.id not in list(data.keys()):
        print(list(data.keys()))
        data[message.chat.id] = {
            'adr': message.text,
            'name_tg': message.chat.username,
            'name': str(message.chat.first_name) + ' ' + str(message.chat.last_name).replace('None', ' '),
            'sent': False,
            'received': False,
            'santa': 0,
            'grandchild': 0,
            'approved': False
        }
        save_data()
        logger.debug('Игрок %s прислал заявку на участие.' % data[message.chat.id]['name'])
        keyboard = types.InlineKeyboardMarkup()
        butt_yes = types.InlineKeyboardButton('Принять', callback_data='yes_%s' % message.chat.id)
        butt_no = types.InlineKeyboardButton('Отказать', callback_data='no_%s' % message.chat.id)
        keyboard.add(butt_yes, butt_no)
        report = str(
            'Пользователь ' + data[message.chat.id]['name'] + ' хочет участвовать в игре и прислал контактные данные: '
            + data[message.chat.id]['adr'])

        bot.send_message(admin, report, reply_markup=keyboard)
        save_data()
    else:
        bot.send_message(message.chat.id, 'Вообще-то вы уже в игре')


@bot.message_handler(func=lambda message: True, content_types=['photo'])
def process_msg(message):
    bot.forward_message(admin, message.chat.id, message.message_id)
    logger.debug('%s отправил фото чека' % data[message.chat.id]['name'])

web.run_app(app, host='localhost', port=8081)
