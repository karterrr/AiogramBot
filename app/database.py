import aiosqlite as sq



async def db_start():
    # Подключаемся к базе данных
    async with sq.connect("bot.db") as db:
        cur = await db.cursor()

        # Создание таблицы пользователей
        await cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id BIGINT NOT NULL, 
            first_name TEXT NOT NULL, 
            last_name TEXT NOT NULL
        )
        """)

        # Создание таблицы конкурсов
        await cur.execute("""
        CREATE TABLE IF NOT EXISTS contests (
            contest_id INTEGER PRIMARY KEY AUTOINCREMENT, 
            contest_name TEXT NOT NULL, 
            contest_description TEXT
        )
        """)

        # Создание таблицы вакансий
        await cur.execute("""
        CREATE TABLE IF NOT EXISTS vacancies (
            vacancy_id INTEGER PRIMARY KEY AUTOINCREMENT, 
            vacancy_name TEXT NOT NULL, 
            vacancy_description TEXT
        )
        """)

        # Создание таблицы тестовых заданий
        await cur.execute("""
        CREATE TABLE IF NOT EXISTS test_tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT, 
            vacancy_id INTEGER NOT NULL,
            task_name TEXT NOT NULL,
            task_description TEXT, 
            task_status TEXT DEFAULT 'Active', 
            FOREIGN KEY (vacancy_id) REFERENCES vacancies(vacancy_id)
        )
        """)

        # Создание таблицы резюме
        await cur.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            user_id INTEGER NOT NULL, 
            resume_link TEXT, 
            portfolio_link TEXT, 
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)

        # Создание таблицы лога выполнения\сдачи тестовых заданий
        await cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks_progress (
            user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            action_type TEXT NOT NULL CHECK(action_type IN ('взял', 'сдал')),
            action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )                 
        """)
        
        # Создание таблицы вопросов пользователей
        await cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            q_type TEXT NOT NULL CHECK(q_type IN ('to bot', 'to admin')),
            q_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )                 
        """)

        # Подтверждаем изменения
        await db.commit()

async def add_new_user():
    # Подключаемся к базе данных
    async with sq.connect("bot.db") as db:
        cur = await db.cursor()