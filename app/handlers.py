from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import aiosqlite

import app.keyboard as kb
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

# Состояния для FSM
class ResumeStates(StatesGroup):
    waiting_for_resume_link = State()
    waiting_for_portfolio_link = State()

class QuestionStates(StatesGroup):
    waiting_for_question_to_bot = State()
    waiting_for_question_to_admin = State()


# Блокировка кнопок в состоянии ожидания ссылки
@router.callback_query(StateFilter(ResumeStates.waiting_for_resume_link))
async def block_buttons_during_state(callback: CallbackQuery):
    await callback.answer("Сначала завершите отправку ссылки.", show_alert=True)
@router.callback_query(StateFilter(ResumeStates.waiting_for_portfolio_link))
async def block_buttons_during_state(callback: CallbackQuery):
    await callback.answer("Сначала завершите отправку ссылки.", show_alert=True)


# Блокировка кнопк в состоянии ожидания вопроса
@router.callback_query(StateFilter(QuestionStates.waiting_for_question_to_bot))
async def block_buttons_during_state(callback: CallbackQuery):
    await callback.answer("Сначала напишите вопрос", show_alert=True)
@router.callback_query(StateFilter(QuestionStates.waiting_for_question_to_admin))
async def block_buttons_during_state(callback: CallbackQuery):
    await callback.answer("Сначала напишите вопрос", show_alert=True)


# Сбор сведений о пользователе
@router.message(CommandStart())
async def cmd_start(message: Message):

    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""

    # Сохранение пользователя в базу данных
    async with aiosqlite.connect("bot.db") as db:

        # Проверяем, существует ли пользователь
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_exists = await cursor.fetchone()
        
        if user_exists:
            # Пользователь уже есть в базе данных
            print(f"Пользователь {user_id} уже существует.")
        else:
            # Добавляем нового пользователя
            await db.execute(
                "INSERT INTO users (user_id, first_name, last_name) VALUES (?, ?, ?)",
                (user_id, first_name, last_name),
            )
            await db.commit()
            print(f"Добавлен новый пользователь: {user_id}, {first_name} {last_name}")

    
    await message.answer("Приветствую!", reply_markup=kb.main)


# Функция помощи
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Вы нажали на кнопку помощи")


# Обработчик нажатий на "Задать вопрос"
@router.message(F.text == "Задать вопрос")
async def catalog(message: Message):
    await message.answer("Выберите, кому вы хотите задать вопрос? (описание разницы)", reply_markup=kb.question)
    
@router.callback_query(F.data == "q_to_bot")
async def resume(callback: CallbackQuery, state: FSMContext):

    # Устанавливаем состояние для получения вопроса боту
    await state.set_state(QuestionStates.waiting_for_question_to_bot)
    await callback.message.answer("Пожалуйста, напишите свой вопрос:")
    await callback.answer()

@router.callback_query(F.data == "q_to_admin")
async def resume(callback: CallbackQuery, state: FSMContext):

    # Устанавливаем состояние для получения вопроса админу
    await state.set_state(QuestionStates.waiting_for_question_to_admin)
    await callback.message.answer("Пожалуйста, напишите свой вопрос:")
    await callback.answer()

# Обработчик отправки вопроса боту
@router.message(StateFilter(QuestionStates.waiting_for_question_to_bot))
async def get_q_to_bot(message: Message, state: FSMContext):
    user_id = message.from_user.id
    q = message.text  
    print(f"Получен вопрос от {user_id}: {q}")

    # Сохраняем вопрос в базе данных
    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "INSERT INTO questions (user_id, question, q_type, q_date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (user_id, q, "to bot")
        )
        await db.commit()

    await message.answer("Ваш вопрос получен. Мы с вами свяжемся.")
    await state.clear()  # Сбрасываем состояние

# Обработчик отправки ссылки на портфолио
@router.message(StateFilter(QuestionStates.waiting_for_question_to_admin))
async def get_q_to_bot(message: Message, state: FSMContext):
    user_id = message.from_user.id
    q = message.text  
    print(f"Получен вопрос от {user_id}: {q}")

    # Сохраняем вопрос в базе данных
    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "INSERT INTO questions (user_id, question, q_type, q_date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (user_id, q, "to admin")
        )
        await db.commit()

    await message.answer("Ваш вопрос получен. Мы с вами свяжемся.")
    await state.clear()  # Сбрасываем состояние


# Вывод списка доступных вакансий
@router.message(F.text == "Получить список вакансий")
async def vacancies_list(message: Message):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT vacancy_id, vacancy_name FROM vacancies") as cursor:
            vacancies = await cursor.fetchall()


    if not vacancies:
        await message.answer("Нет доступных вакансий.")
        return
    

    vacancies_kb = InlineKeyboardBuilder()
    for vacancy_id, vacancy_name in vacancies:
        button_text = f"{vacancy_name or "No vacancie"} "
        callback_data = f"vacancy:{vacancy_id}"
        vacancies_kb.button(text=button_text, callback_data=callback_data)
    vacancies_kb.adjust(1)

    await message.answer("Выберите вакансию:", reply_markup=vacancies_kb.as_markup())

# Обработчик нажатий на вакансии
@router.callback_query(lambda c: c.data.startswith("vacancy:"))
async def vacancy_info_callback(callback: CallbackQuery):
    vacancy_id = callback.data.split(":")[1]  # Извлекаем ID вакансии
    async with aiosqlite.connect("bot.db") as db:

        async with db.execute("SELECT vacancy_name, vacancy_description FROM vacancies WHERE vacancy_id = ?", (vacancy_id)) as cursor:
            vacancy = await cursor.fetchone()
        
        async with db.execute("SELECT task_id, task_name FROM test_tasks WHERE vacancy_id=?", (vacancy_id)) as cursor:
            test_tasks = await cursor.fetchall()

    # Проверяем, что вакансия найдена
    if not vacancy:
        await callback.message.answer("Вакансия не найдена.")
        await callback.answer()
        return
    

    # Формируем описание вакансии
    vacancy_name, vacancy_description = vacancy
    message_text = f"📌 {vacancy_name}\n\n{vacancy_description}\n\n"


    # Выводим список тестовых заданий
    if test_tasks:
        message_text += "📝 Доступные тестовые задания:\n"
        test_tasks_kb = InlineKeyboardBuilder()
        for task_id, task_name in test_tasks:
            task_button_text = task_name[:50]  # Ограничиваем длину текста
            test_tasks_kb.button(text=task_button_text, callback_data=f"task:{task_id}")
        test_tasks_kb.adjust(1)
        await callback.message.answer(message_text, reply_markup=test_tasks_kb.as_markup())
    else:
        message_text += "Нет доступных тестовых заданий."
        await callback.message.answer(message_text)
    await callback.answer()  # Закрываем уведомление




# Вывод описания тестового задания с кнопками "Взять задание" и "Сдать задание"
@router.callback_query(lambda c: c.data.startswith("task:"))
async def task_description_callback(callback: CallbackQuery):
    task_id = callback.data.split(":")[1]  # Извлекаем ID тестового задания
    user_id = callback.from_user.id

    async with aiosqlite.connect("bot.db") as db:
        # Получаем описание задания
        async with db.execute(
            "SELECT task_name, task_description FROM test_tasks WHERE task_id = ?", 
            (task_id,)
        ) as cursor:
            task = await cursor.fetchone()

        # Проверяем статус задания для данного пользователя
        async with db.execute(
            "SELECT action_type FROM tasks_progress WHERE user_id = ? AND task_id = ? ORDER BY action_date DESC LIMIT 1",
            (user_id, task_id)
        ) as cursor:
            task_status = await cursor.fetchone()

    # Если задание не найдено
    if not task:
        await callback.message.answer("Тестовое задание не найдено.")
        await callback.answer()
        return

    task_name, task_description = task

    # Формируем текст с описанием задания
    message_text = f"📋 <b>{task_name}</b>\n\n{task_description}\n"

    # Генерируем клавиатуру с кнопками
    task_kb = InlineKeyboardBuilder()

    if not task_status or task_status[0] == "сдал":  # Задание еще не взято или уже сдано
        task_kb.button(text="Взять задание", callback_data=f"take_task:{task_id}")
    elif task_status[0] == "взял":  # Задание взято
        task_kb.button(text="Сдать задание", callback_data=f"submit_task:{task_id}")

    task_kb.adjust(1)

    await callback.message.answer(message_text, reply_markup=task_kb.as_markup(), parse_mode="HTML")
    await callback.answer()

# Обработчик кнопки "Взять задание"
@router.callback_query(lambda c: c.data.startswith("take_task:"))
async def take_task_callback(callback: CallbackQuery):
    task_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    action_type = "взял"

    async with aiosqlite.connect("bot.db") as db:
        # Проверяем, не взял ли уже пользователь это задание
        async with db.execute(
            "SELECT action_type FROM tasks_progress WHERE user_id = ? AND task_id = ? ORDER BY action_date DESC LIMIT 1",
            (user_id, task_id)
        ) as cursor:
            task_status = await cursor.fetchone()

        if task_status and task_status[0] == "взял":
            await callback.message.answer("Вы уже взяли это задание.", parse_mode="HTML")
            await callback.answer()
            return

        # Добавляем запись о взятии задания
        await db.execute(
            "INSERT INTO tasks_progress (user_id, task_id, action_type, action_date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (user_id, task_id, action_type)
        )
        await db.commit()

    await callback.message.answer("Вы взяли задание. Удачи!", parse_mode="HTML")
    await callback.answer()

# Обработчик кнопки "Сдать задание"
@router.callback_query(lambda c: c.data.startswith("submit_task:"))
async def submit_task_callback(callback: CallbackQuery):
    task_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    action_type = "сдал"

    async with aiosqlite.connect("bot.db") as db:
        # Проверяем, не сдал ли уже пользователь это задание
        async with db.execute(
            "SELECT action_type FROM tasks_progress WHERE user_id = ? AND task_id = ? ORDER BY action_date DESC LIMIT 1",
            (user_id, task_id)
        ) as cursor:
            task_status = await cursor.fetchone()

        if task_status and task_status[0] == "сдал":
            await callback.message.answer("Вы уже сдали это задание. Спасибо за работу!", parse_mode="HTML")
            await callback.answer()
            return

        # Проверяем, взял ли пользователь это задание
        if not task_status or task_status[0] != "взял":
            await callback.message.answer("Вы не можете сдать задание, которое не взяли.", parse_mode="HTML")
            await callback.answer()
            return

        # Добавляем запись о сдаче задания
        await db.execute(
            "INSERT INTO tasks_progress (user_id, task_id, action_type, action_date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (user_id, task_id, action_type)
        )
        await db.commit()

    await callback.message.answer("Вы сдали задание. Спасибо за работу!", parse_mode="HTML")
    await callback.answer()






# Вывод списка доступных конкурсов
@router.message(F.text == "Список доступных конкурсов")
async def contest_list(message: Message):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT contest_id, contest_name FROM contests") as cursor:
            contests = await cursor.fetchall()


    if not contests:
        await message.answer("Нет доступных конкурсов.")
        return
    

    contests_kb = InlineKeyboardBuilder()
    for contest_id, contest_name in contests:
        button_text = f"{contest_name or "No contest"} "
        callback_data = f"contest:{contest_id}"
        contests_kb.button(text=button_text, callback_data=callback_data)
    contests_kb.adjust(1)

    await message.answer("Выберите конкурс:", reply_markup=contests_kb.as_markup())


# Обработчик нажатий на конкурсы
@router.callback_query(lambda c: c.data.startswith("contest:"))
async def contest_info_callback(callback: CallbackQuery):
    contest_id = callback.data.split(":")[1]  # Извлекаем ID конкурса
    async with aiosqlite.connect("bot.db") as db:

        async with db.execute("SELECT contest_name, contest_description FROM contests WHERE contest_id = ?", (contest_id)) as cursor:
            contest = await cursor.fetchone()
        

    # Проверяем, что конкурс найден
    if not contest:
        await callback.message.answer("Конкурс не найден.")
        await callback.answer()
        return
    

    # Формируем описание конкурса
    contest_name, contest_description = contest
    message_text = f"🖥️ {contest_name}\n\n{contest_description}\n\n"


    # Выводим описание конкурса
    await callback.message.answer(message_text)
    await callback.answer()  # Закрываем уведомление






# Обработчик нажатий на кнопку "Рассказать о себе"
@router.message(F.text == "Рассказать о себе")
async def about_myself(message: Message):
    await message.answer("Вы можете отправить ссылку на своё резюме или портфолио.\n"
                         "\nПожалуйста, выберите опцию ниже:", reply_markup=kb.about_myself)


# Обработчик нажатий на кнопку "Отправить ссылку на резюме"
@router.callback_query(F.data == "resume")
async def resume(callback: CallbackQuery, state: FSMContext):

    # Устанавливаем состояние для получения ссылки на резюме
    await state.set_state(ResumeStates.waiting_for_resume_link)
    await callback.message.answer("Пожалуйста, отправьте ссылку на ваше резюме:")
    await callback.answer()

# Обработчик нажатий на кнопку "Отправить ссылку на портфолио"
@router.callback_query(F.data == "portfolio")
async def portfolio(callback: CallbackQuery, state: FSMContext):

    # Устанавливаем состояние для получения ссылки на портфолио
    await state.set_state(ResumeStates.waiting_for_portfolio_link)
    await callback.message.answer("Пожалуйста, отправьте ссылку на ваше портфолио:")
    await callback.answer()





# Обработчик отправки ссылки на резюме
@router.message(StateFilter(ResumeStates.waiting_for_resume_link))
async def get_resume_link(message: Message, state: FSMContext):
    user_id = message.from_user.id
    resume_link = message.text  # Ссылка, отправленная пользователем
    print(f"Получено сообщение от {user_id}: {resume_link}")

    # Проверяем, является ли сообщение ссылкой
    if not resume_link.startswith("http"):
        await message.answer("Пожалуйста, отправьте корректную ссылку.")
        return

    # Сохраняем ссылку в базе данных
    """async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "INSERT INTO resumes (user_id, resume_link) VALUES (?, ?)",
            (user_id, resume_link)
        )
        await db.commit()"""
    async with aiosqlite.connect("bot.db") as db:
        # Проверяем отправлял ли пользователь ссылки до этого
        async with db.execute(
            "SELECT user_id FROM resumes WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            user_found = await cursor.fetchone()

        # Если нет, то создаём новую запись
        if not user_found:
            await db.execute(
                "INSERT INTO resumes (user_id, resume_link) VALUES (?, ?)",
                (user_id, resume_link)
            )
        # Если да, то обновляем данные о пользователе
        else:
            await db.execute(
                "UPDATE resumes SET resume_link = ? WHERE user_id = ?",
                (resume_link, user_id)
            )
        await db.commit()

    await message.answer("Ссылка на резюме успешно сохранена. Спасибо!")
    await state.clear()  # Сбрасываем состояние

# Обработчик отправки ссылки на портфолио
@router.message(StateFilter(ResumeStates.waiting_for_portfolio_link))
async def get_portfolio_link(message: Message, state: FSMContext):
    user_id = message.from_user.id
    portfolio_link = message.text  # Ссылка, отправленная пользователем

    # Проверяем, является ли сообщение ссылкой
    if not portfolio_link.startswith("http"):
        await message.answer("Пожалуйста, отправьте корректную ссылку.")
        return

    # Сохраняем ссылку в базе данных
    async with aiosqlite.connect("bot.db") as db:
        # Проверяем отправлял ли пользователь ссылки до этого
        async with db.execute(
            "SELECT user_id FROM resumes WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            user_found = await cursor.fetchone()

        # Если нет, то создаём новую запись
        if not user_found:
            await db.execute(
                "INSERT INTO resumes (user_id, portfolio_link) VALUES (?, ?)",
                (user_id, portfolio_link)
            )
        # Если да, то обновляем данные о пользователе
        else:
            await db.execute(
                "UPDATE resumes SET portfolio_link = ? WHERE user_id = ?",
                (portfolio_link, user_id)
            )
        await db.commit()

    await message.answer("Ссылка на портфолио успешно сохранена. Спасибо!")
    await state.clear()  # Сбрасываем состояние

