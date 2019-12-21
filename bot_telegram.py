# Бот игры "Как стать миллионером",
# Автор - А.Натальченко, Version 1.2
# Bot name -- natalchenko_bot

# pip install pysocks -- установка библиотеки для работы с сокетами

import telebot
import requests
import random
from settings import TOKEN


users_scores = {}  # Storage for users scores
users_states = {}  # Storage for users states
users_questions = {}  # Storage for users questions
users_complexity = {}  # Storage for users complexity


# Константы названий состяний конечного автомата
MAIN_STATE = 'main'
QUESTION_STATE = 'question'

# URL используемого API
BASE_URL = 'https://stepik.akentev.com/api/millionaire'

# Константа определяет необходимость вывода правильного варианта ответа пользователю в случае неудачи
SHOW_RIGHT_ANSWER = True

bot = telebot.TeleBot(TOKEN)
telebot.apihelper.proxy = {'https': 'socks5://stepik.akentev.com:1080'}


# Получение через API нового вопроса для вывода пользователю
def get_new_question(user_id):

    params = {'complexity': str(users_complexity.get(user_id))}

    if params['complexity'] in ('1', '2', '3'):
        new_question = requests.get(BASE_URL, params).json()
    else:
        new_question = requests.get(BASE_URL,).json()

    right_answer = new_question['answers'][0]  # Сохраняем правильный ответ, изначально он всегда с 0-вым индексом
    random.shuffle(new_question['answers'])  # Перемешиваем список

    # Для удобство дальнейшего сравнения сохраним индекс+1 правильного ответа в перемешанном множестве
    # ответов в виде числа в строковом виде
    new_question['right_answer_index'] = str(new_question['answers'].index(right_answer)+1)
    # Служебый список для простой проверки того, что пользователь ввел индекс одного из возможных вариантов ответа
    new_question['answers_indexes'] = [str(x+1) for x in range(len(new_question['answers']))]

    return new_question


# Процедура обновляет счет по id пользователя. Входные параметры:
# user_id - ID пользоватля (ключ в словаре)
# right_answer_flag - булево значение, определяет правильно пользователь
#                     ответил на заданный вопрос или нет
def change_user_score(user_id, right_answer_flag):
    if user_id in users_scores:  # В словаре уже есть запись счета для user_id?
        # Обновим существующую запись о счете
        users_scores[user_id]['victories'] += int(right_answer_flag)
        users_scores[user_id]['defeats'] += int(not right_answer_flag)
    else:
        # Добавим запись о счете для пользователя
        users_scores[user_id] = {'victories': int(right_answer_flag), 'defeats': int(not right_answer_flag)}


# Функция возвращает словарь со счетам заданного пользователя
def get_user_score(user_id):
    return users_scores.get(user_id, {'victories': 0, 'defeats': 0})


# Вспомогательный вывод данных на экран о текущей активности бота
def log(message):
    print("\n ------")
    from datetime import datetime
    print(datetime.now())
    print("Сообщение от {0} {1}. (id = {2}) \nТекст = {3}".format(message.from_user.first_name,
                                                                  message.from_user.last_name,
                                                                  str(message.from_user.id),
                                                                  message.text))


@bot.message_handler(func=lambda message: True)
def dispatcher(message):  # Обработчик входящих команд
    user_id = message.from_user.id
    cur_user_state = users_states.get(user_id, 'main')

    if cur_user_state == MAIN_STATE:
        main_handler(message)

    elif cur_user_state == QUESTION_STATE:
        question_handler(message)

    else:
        raise Exception('Undefined bot state!')  # На всякий случай, в случае будущего изменения кода


# Обработчик основного состояния
def main_handler(message):

    if message.text == '/start':
        bot.send_message(message.chat.id, 'Это бот-игра "Кто хочет стать миллионером"')

    elif message.text.lower() == 'привет':
        bot.send_message(message.chat.id, 'Ну привет {0}!'.format(message.from_user.first_name))

    elif message.text.lower() in ('покажи счет', 'покажи счёт', 'счет', 'счёт'):
        d = get_user_score(message.from_user.id)
        bot.send_message(message.chat.id, str(d['victories']) + '-' + str(d['defeats']))

    elif message.text.lower() in ('сложность', 'сложность?', 'сложность ?',
                                  'complexity', 'complexity?', 'complexity ?'):
        complexity = users_complexity.get(message.from_user.id)
        if complexity is None:
            bot.send_message(message.chat.id, "Уровень сложности вопросов не задан")
        else:
            bot.send_message(message.chat.id, f"Уровень сложности = {complexity}")

    elif message.text.startswith('сложность=') or message.text.startswith('complexity='):
        try:
            complexity = int(message.text.split('=')[1])
        except ValueError:
            bot.send_message(message.chat.id, "Уровень сложности вопросов задается целым числом от 1 до 3")
        else:
            if 1 <= complexity <= 3:
                # Пользователь корректно задал уровень сложности вопросов, сохраним его
                users_complexity[message.from_user.id] = complexity
            else:
                bot.send_message(message.chat.id, "Уровень сложности вопросов задается целым числом от 1 до 3")

    elif message.text.lower() in ('спроси меня вопрос', 'спроси вопрос', 'вопрос', '?'):
        question_dict = get_new_question(message.from_user.id)  # Получим новый вопрос
        question_text = question_dict['question'] + \
                        ' '.join(list(map(lambda x, y: x+y,
                                          ['\n' + str(x+1) + ') ' for x in range(len(question_dict['answers']))],
                                          question_dict['answers'])))
        bot.send_message(message.chat.id, question_text)
        users_questions[message.from_user.id] = question_dict
        users_states[message.from_user.id] = QUESTION_STATE

    else:
        bot.send_message(message.chat.id, 'Я не понял')

    log(message)


# Обработчик ответа на заданный вопрос
def question_handler(message):

    q_dict = users_questions[message.from_user.id]  # Получим словарь с текщим вопросом и ответами для пользователя

    if message.text in q_dict['answers_indexes']:  # Ответ пользователя - индекс одного из допустимых ответов на вопрос

        if message.text == q_dict['right_answer_index']:  # Ответ пользователя - индекс ПРАВИЛЬНОГО ответа на вопрос
            bot.send_message(message.chat.id, 'Правильно!')
            change_user_score(message.from_user.id, True)
            users_states[message.from_user.id] = MAIN_STATE

        else:
            bot.send_message(message.chat.id, 'Неправильно :(')
            change_user_score(message.from_user.id, False)
            users_states[message.from_user.id] = MAIN_STATE
            if SHOW_RIGHT_ANSWER:  # Показывать правильный ответ?
                bot.send_message(message.chat.id, 'Правильный ответ - ' + str(q_dict['right_answer_index']))

    else:  # Keep staying in the QUESTION state ...
        bot.send_message(message.chat.id, 'Я не понял, повторите Ваш ответ...')

    log(message)


bot.polling()  # Запускаем бесконечный цикл
