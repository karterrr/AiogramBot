from datetime import datetime

from aiogram import F, Router, BaseMiddleware, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from typing import Callable, Awaitable, Dict
import aiosqlite

import app.keyboard as kb
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Список ID админов
ADMIN_IDS = [307464344]

class AdminCheckMiddleware(BaseMiddleware):
    async def __call__(
            self, handler: Callable[[Message, Dict], Awaitable], event: Message, data: Dict
    ):
        if event.from_user.id not in ADMIN_IDS:
            await event.answer("Вы не являетесь администратором.")
            return #Прерываем, если юзер не админ
        return await handler(event, data)

admin_router = Router()

@admin_router.message(F.text=="админка")
async def go_to_admin(message: Message):  
    await message.answer("Вы перешли в режим администрирования", reply_markup=kb.main_admin)

TASKS_PER_PAGE = 5 #Кол-во заданий на одной странице
QUESTIONS_PER_PAGE = 10  # Количество вопросов на одной странице


@admin_router.message(F.text == "Тестовые задания")
@admin_router.callback_query(F.data.startswith("tasks_page:"))
async def tasks_list(callback_or_message):
    # Определяем источник вызова: сообщение или callback
    if isinstance(callback_or_message, Message):
        message = callback_or_message
        is_callback = False
        page = 0  # Начинаем с первой страницы
    else:
        callback = callback_or_message
        message = callback.message
        is_callback = True
        # Извлекаем текущую страницу из callback data
        page = int(callback.data.split(":")[1])
        print(f"Страница {page} Выбрана")

    async with aiosqlite.connect("bot.db") as db:
        # Получаем общее количество заданий
        async with db.execute(
            "SELECT COUNT(*) FROM tasks_progress WHERE task_link NOT NULL"
        ) as cursor:
            total_tasks = (await cursor.fetchone())[0]

        # Получаем вопросы для текущей страницы
        offset = page * TASKS_PER_PAGE
        async with db.execute(
            """
            SELECT 
                t.user_id, 
                u.first_name, 
                u.last_name,
                v.vacancy_name,
                t.task_id,
                t.action_date     
            FROM 
                tasks_progress t
            LEFT JOIN 
                users u ON t.user_id = u.user_id
            LEFT JOIN 
                test_tasks tt ON t.task_id = tt.task_id
            LEFT JOIN 
                vacancies v ON tt.vacancy_id = v.vacancy_id
            WHERE 
                t.task_link IS NOT NULL
            LIMIT ? OFFSET ?
            """,
            (TASKS_PER_PAGE, offset),
        ) as cursor:
            tasks = await cursor.fetchall()

    # Если вопросов нет
    if not tasks:
        if is_callback:
            await message.edit_text("Нет выполненных заданий.")
            await callback.answer()
        else:
            await message.answer("Нет выполненных заданий.")
        return

    # Формируем текст и клавиатуру
    tasks_kb = InlineKeyboardBuilder()
    for user_id, first_name, last_name, vacancy_name, task_id, action_date in tasks:
        display_name = first_name if first_name else f"ID {user_id}"
        display_lastname = last_name if last_name else ""
        button_text = (
        f"От: {display_name} {display_lastname}. " 
        f"Вакансия: {vacancy_name}\n"
        )
        callback_data = f"complete_task_info,{user_id},{task_id},{action_date},{page}"  # Передаем ID пользователя для идентификации
        tasks_kb.button(text=button_text, callback_data=callback_data)

    # Добавляем кнопки пагинации
    if total_tasks > (offset + TASKS_PER_PAGE):  
        tasks_kb.button(text="➡️ Вперёд", callback_data=f"tasks_page:{page + 1}")
    if page > 0:  # Кнопка "Назад", если страница не первая
        tasks_kb.button(text="⬅️ Назад", callback_data=f"tasks_page:{page - 1}")

    tasks_kb.adjust(1)  # Размещаем кнопки в столбик

    # Отправляем или обновляем сообщение
    if is_callback:
        await message.edit_text("Выберите задание, которое хотите просмотреть:", reply_markup=tasks_kb.as_markup())
        await callback.answer()
    else:
        await message.answer("Выберите задание, которое хотите просмотреть:", reply_markup=tasks_kb.as_markup())



@admin_router.callback_query(F.data.startswith("complete_task_info,"))
async def view_question(callback: CallbackQuery):
    data = callback.data.split(",")
    user_id = data[1]
    task_id = data[2]
    task_date = data[3]
    page = data[4]


    async with aiosqlite.connect("bot.db") as db:
        async with db.execute(
            """
            SELECT
                t.user_id,  
                u.first_name, 
                u.last_name, 
                t.action_date,
                v.vacancy_name,
                tt.task_name,
                t.task_link      
            FROM 
                tasks_progress t
            LEFT JOIN 
                users u ON t.user_id = u.user_id
            LEFT JOIN 
                test_tasks tt ON t.task_id = tt.task_id
            LEFT JOIN 
                vacancies v ON tt.vacancy_id = v.vacancy_id
            WHERE 
                t.task_link IS NOT NULL AND t.user_id = ? AND t.task_id = ? AND t.action_date = ?
            """,
            (user_id, task_id, task_date)
        ) as cursor:
            task_data = await cursor.fetchone()
            print(user_id, task_id, task_date, page)

    if not task_data:
        await callback.answer("Задание уже скрыто или не найдено.", show_alert=True)
        return

    user_id, first_name, last_name, task_date, vacancy_name, task_name, task_link = task_data
    task_date_formatted = datetime.strptime(task_date, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
    display_name = first_name if first_name else f"ID {user_id}"
    display_lastname = last_name if last_name else ""

    message_text = (
        f"📝 <b>Задание от:</b> {display_name} {display_lastname}\n\n"
        f"<b>Дата:</b> {task_date_formatted}\n\n"
        f"<b>Вакансия:</b> {vacancy_name}\n\n"
        f"<b>Задание:</b> {task_name}\n\n"
        f"<b>Ссылка на выполненное задание:</b>\n{task_link}"
    )

    # Клавиатура
    task_kb = InlineKeyboardBuilder()
    task_kb.button(text="⬅️ Назад", callback_data=f"tasks_page:{page}")
    task_kb.adjust(1)

    await callback.message.edit_text(message_text, reply_markup=task_kb.as_markup(), parse_mode="HTML")
    await callback.answer()






@admin_router.message(F.text == "Ответить на вопросы")
@admin_router.callback_query(F.data.startswith("questions:"))
async def questions_list(callback_or_message, page = 0):
    # Определяем источник вызова: сообщение или callback
    if isinstance(callback_or_message, Message):
        message = callback_or_message
        is_callback = False
        page = 0  # Начинаем с первой страницы
    else:
        callback = callback_or_message
        message = callback.message
        is_callback = True
        # Извлекаем текущую страницу из callback data
        page = int(callback.data.split(":")[1])

    async with aiosqlite.connect("bot.db") as db:
        # Получаем общее количество вопросов
        async with db.execute(
            "SELECT COUNT(*) FROM questions WHERE q_type='to admin' AND answered = 0"
        ) as cursor:
            total_questions = (await cursor.fetchone())[0]

        # Получаем вопросы для текущей страницы
        offset = page * QUESTIONS_PER_PAGE
        async with db.execute(
            """
            SELECT q.user_id, u.first_name, u.last_name, q.q_date
            FROM questions q 
            LEFT JOIN users u ON q.user_id = u.user_id
            WHERE q.q_type='to admin' AND q.answered = 0
            LIMIT ? OFFSET ?
            """,
            (QUESTIONS_PER_PAGE, offset),
        ) as cursor:
            questions = await cursor.fetchall()

    # Если вопросов нет
    if not questions:
        if is_callback:
            await message.edit_text("Нет активных вопросов.")
            await callback.answer()
        else:
            await message.answer("Нет активных вопросов.")
        return

    # Формируем текст и клавиатуру
    question_kb = InlineKeyboardBuilder()
    for user_id, first_name, last_name, q_date in questions:
        display_name = first_name if first_name else f"ID {user_id}"
        display_lastname = last_name if last_name else ""
        button_text = f"Вопрос от: {display_name} {display_lastname}"
        callback_data = f"question_text,{user_id},{q_date},{page}"  # Передаем ID пользователя для идентификации
        question_kb.button(text=button_text, callback_data=callback_data)

    # Добавляем кнопки пагинации
    if page > 0:  # Кнопка "Назад", если страница не первая
        question_kb.button(text="⬅️ Назад", callback_data=f"questions:{page - 1}")
    if total_questions > (offset + QUESTIONS_PER_PAGE):  # Кнопка "Вперёд", если есть следующие вопросы
        question_kb.button(text="➡️ Вперёд", callback_data=f"questions:{page + 1}")

    question_kb.adjust(1)  # Размещаем кнопки в столбик

    # Отправляем или обновляем сообщение
    if is_callback:
        await message.edit_text("Выберите вопрос:", reply_markup=question_kb.as_markup())
        await callback.answer()
    else:
        await message.answer("Выберите вопрос:", reply_markup=question_kb.as_markup())


# Состояние для ввода ответа
class AnswerQuestionState(StatesGroup):
    waiting_for_answer = State()

@admin_router.callback_query(F.data.startswith("question_text,"))
async def view_question(callback: CallbackQuery, state: FSMContext):
    data = callback.data.split(",")
    user_id = data[1]
    q_date = data[2]
    page = int(data[3])

    await state.update_data(current_page=page)


    async with aiosqlite.connect("bot.db") as db:
        async with db.execute(
            """
            SELECT q.question, q.q_date, u.first_name, u.last_name 
            FROM questions q
            LEFT JOIN users u ON q.user_id = u.user_id
            WHERE q.user_id = ? AND q.q_type = 'to admin' AND q.answered = 0 AND q.q_date = ?
            """,
            (user_id, q_date)
        ) as cursor:
            question_data = await cursor.fetchone()

    if not question_data:
        await callback.answer("Вопрос уже закрыт или не найден.", show_alert=True)
        return

    question_text, question_date, first_name, last_name = question_data
    question_date_formatted = datetime.strptime(question_date, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
    display_name = first_name if first_name else f"ID {user_id}"
    display_lastname = last_name if last_name else ""

    message_text = (
        f"📝 <b>Вопрос от:</b> {display_name} {display_lastname}\n"
        f"<b>Дата:</b> {question_date_formatted}\n\n"
        f"<b>Текст вопроса:</b>\n{question_text}"
    )

    # Клавиатура
    question_kb = InlineKeyboardBuilder()
    question_kb.button(text="Ответить на вопрос", callback_data=f"answer_question,{user_id},{q_date}")
    question_kb.button(text="⬅️ Назад", callback_data=f"questions:{page}")
    question_kb.adjust(1)

    await callback.message.edit_text(message_text, reply_markup=question_kb.as_markup(), parse_mode="HTML")
    await callback.answer()

# Обработка кнопки "Ответить на вопрос"
@admin_router.callback_query(F.data.startswith("answer_question,"))
async def answer_question(callback: CallbackQuery, state: FSMContext):
    # Извлекаем user_id и текст вопроса из callback data
    data = callback.data.split(",")
    user_id = data[1]
    q_date = data[2]
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute(
            """
            SELECT q.question
            FROM questions q
            WHERE q.user_id = ? AND q.q_type = 'to admin' AND q.answered = 0 AND q.q_date = ?
            """,
            (user_id, q_date)
        ) as cursor:
            question_data = await cursor.fetchone()
    
    
    if question_data:
        question_text = question_data[0]  # Извлекаем текст вопроса
    else:
        question_text = None

    if question_text is None:
        await callback.message.edit_text("Вопрос не найден или уже был отвечен.")
        await callback.answer()
        return
    

    print(question_text)
    # Сохраняем данные в состояние
    await state.update_data(answer_user_id=user_id, answer_question_text=question_text)

    await callback.message.edit_text(
        "Напишите текст ответа на вопрос.\n\nДля отмены введите /cancel."
    )
    await state.set_state(AnswerQuestionState.waiting_for_answer)
    await callback.answer()

@admin_router.message(AnswerQuestionState.waiting_for_answer)
async def process_answer(message: Message, state: FSMContext, bot: Bot):
    # Получаем ID пользователя и текст ответа
    data = await state.get_data()
    user_id = data["answer_user_id"]
    question_text = data["answer_question_text"]
    answer_text = message.text

    if answer_text.lower() == "/cancel":
        await state.clear()
        await message.answer("Ввод ответа отменён.")
        return

    async with aiosqlite.connect("bot.db") as db:
        # Обновляем таблицу questions
        await db.execute(
            """
            UPDATE questions
            SET a_date = CURRENT_TIMESTAMP, answered = 1
            WHERE user_id = ? AND question = ? AND q_type = 'to admin' AND answered = 0
            """,
            (user_id, question_text),
        )
        await db.commit()

    # Отправляем ответ пользователю
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "Ваш вопрос был рассмотрен.\n\n"
                f"Ваш вопрос: {question_text}\n\n"
                f"Ответ: {answer_text}"
            ),
        )
    except Exception:
        await message.answer("Не удалось отправить сообщение пользователю.")

    # Уведомляем админа
    await message.answer("Ответ отправлен пользователю.")

    page = data.get("current_page", 0) 

    # Возвращаемся к списку вопросов
    await questions_list(message, page) 

    # Возвращаемся к списку вопросов
    await state.clear()



@admin_router.callback_query(F.data.startswith("questions:"))
async def back_to_questions(callback: CallbackQuery):
    page = int(callback.data.split(":")[3])
    await questions_list(callback, page)  # Вызываем существующую функцию questions_list








@admin_router.callback_query(F.data == "back_to_vacancies")
@admin_router.message(F.text == "Изменить список вакансий")
async def vacancies_list(callback_or_message):

    if isinstance(callback_or_message, Message):
        message = callback_or_message
        is_callback = False
    else:
        callback = callback_or_message
        message = callback.message
        is_callback = True

    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT vacancy_id, vacancy_name FROM vacancies") as cursor:
            vacancies = await cursor.fetchall()


    if not vacancies:
        if is_callback:
            await message.edit_text("Нет вакансий.")
        else:
            await message.answer("Нет вакансий.")   
        return
    

    vacancies_kb = InlineKeyboardBuilder()
    for vacancy_id, vacancy_name in vacancies:
        button_text = f"{vacancy_name or 'No vacancie'} "
        callback_data = f"delete_vacancy:{vacancy_id}"
        vacancies_kb.button(text=button_text, callback_data=callback_data)
    vacancies_kb.button(text="✔Добавить вакансию", callback_data="add_vacancy")
    vacancies_kb.adjust(1)

    if is_callback:
        await message.edit_text("Выберите вакансию, которую хотите удалить:", reply_markup=vacancies_kb.as_markup())
        await callback.answer()
    else:
        await message.answer("Выберите вакансию, которую хотите удалить:", reply_markup=vacancies_kb.as_markup())