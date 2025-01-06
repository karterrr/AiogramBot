from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                            InlineKeyboardMarkup, InlineKeyboardButton)


# Главное меню
main = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Получить список вакансий')],
                                     [KeyboardButton(text='Список доступных конкурсов')],
                                     [KeyboardButton(text='Задать вопрос'),
                                      KeyboardButton(text='Рассказать о себе')]],
                            resize_keyboard=True,
                            input_field_placeholder='Выберете пункт меню...')

# Главное меню админа
main_admin = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Изменить список вакансий')],
                                     [KeyboardButton(text='Изменить список конкурсов')],
                                     [KeyboardButton(text='Ответить на вопросы'),
                                      KeyboardButton(text='Тестовые задания')]],
                            resize_keyboard=True,
                            input_field_placeholder='Выберете пункт меню...')

# Клавиатура задать вопрос
question = InlineKeyboardMarkup (inline_keyboard=[
    [InlineKeyboardButton(text='Задать вопрос боту', callback_data='q_to_bot')],
    [InlineKeyboardButton(text='Задать вопрос админу', callback_data='q_to_admin')]])

# Клавиатура рассказать о себе
about_myself = InlineKeyboardMarkup (inline_keyboard=[
    [InlineKeyboardButton(text='Отправить ссылку на резюме', callback_data='resume')],
    [InlineKeyboardButton(text='Отправить ссылку на портфолио', callback_data='portfolio')]])


