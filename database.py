import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

# ============================================
# НАСТРОЙКИ ПОДКЛЮЧЕНИЯ К POSTGRESQL
# ============================================

DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "fotex_db"
DB_USER = "postgres"
DB_PASSWORD = "Kirlovo98!"  # ⚠️

# Кодируем пароль (на случай спецсимволов)
encoded_password = quote_plus(DB_PASSWORD)

# Строка подключения
DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Создаём engine
engine = create_engine(DATABASE_URL, echo=True)

# Фабрика сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ
# ============================================

def get_db():
    """Получить сессию базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    """Проверить подключение к PostgreSQL"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ PostgreSQL подключён успешно!")
            return True
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def get_user(telegram_id):
    """Получить пользователя по telegram_id"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM users WHERE telegram_id = :tid"),
                {"tid": telegram_id}
            ).fetchone()
            if result:
                return dict(result._mapping)
            return None
    except Exception as e:
        print(f"Ошибка get_user: {e}")
        return None

def get_user_by_username(username):
    """Получить пользователя по username"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM users WHERE username = :uname"),
                {"uname": username}
            ).fetchone()
            if result:
                return dict(result._mapping)
            return None
    except Exception as e:
        print(f"Ошибка get_user_by_username: {e}")
        return None

def create_user(telegram_id, username, first_name="", last_name=""):
    """Создать нового пользователя"""
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""INSERT INTO users 
                       (telegram_id, username, first_name, last_name, balance, total_balance)
                       VALUES (:tid, :uname, :fname, :lname, 100, 100)"""),
                {"tid": telegram_id, "uname": username, "fname": first_name, "lname": last_name}
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"Ошибка create_user: {e}")
        return False

def update_balance(telegram_id, new_balance):
    """Обновить баланс пользователя"""
    try:
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE users SET balance = :balance, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = :tid"),
                {"balance": new_balance, "tid": telegram_id}
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"Ошибка update_balance: {e}")
        return False

def add_to_history(telegram_id, original_url, result_url, edit_type, custom_prompt=None, cost=15):
    """Добавить запись в историю обработок"""
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""INSERT INTO processing_history 
                       (telegram_id, original_photo_url, processed_photo_url, edit_type, custom_prompt, cost)
                       VALUES (:tid, :orig, :res, :edit, :prompt, :cost)"""),
                {"tid": telegram_id, "orig": original_url, "res": result_url,
                 "edit": edit_type, "prompt": custom_prompt, "cost": cost}
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"Ошибка add_to_history: {e}")
        return False

def get_user_history(telegram_id, limit=20):
    """Получить историю обработок пользователя"""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""SELECT * FROM processing_history 
                       WHERE telegram_id = :tid 
                       ORDER BY created_at DESC 
                       LIMIT :limit"""),
                {"tid": telegram_id, "limit": limit}
            ).fetchall()
            return [dict(row._mapping) for row in result]
    except Exception as e:
        print(f"Ошибка get_user_history: {e}")
        return []

def update_user_stats(telegram_id, generations_increment=1, expenses_increment=15):
    """Обновить статистику пользователя"""
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""UPDATE users 
                       SET generations = generations + :gen,
                           expenses = expenses + :exp,
                           total_balance = total_balance - :exp,
                           updated_at = CURRENT_TIMESTAMP
                       WHERE telegram_id = :tid"""),
                {"gen": generations_increment, "exp": expenses_increment, "tid": telegram_id}
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"Ошибка update_user_stats: {e}")
        return False

# ============================================
# ПРОВЕРКА ПОДКЛЮЧЕНИЯ ПРИ ЗАПУСКЕ
# ============================================

if __name__ == "__main__":
    test_connection()