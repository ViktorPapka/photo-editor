-- ============================================
-- База данных для FOTEX AI
-- PostgreSQL
-- ============================================

-- 1. Создание базы данных (выполнить один раз в pgAdmin)
-- CREATE DATABASE fotex_db;

-- 2. Таблица пользователей (совместима с Telegram-ботом)
CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    balance INTEGER DEFAULT 100,
    gift_balance INTEGER DEFAULT 0,
    total_balance INTEGER DEFAULT 100,
    generations INTEGER DEFAULT 0,
    videos INTEGER DEFAULT 0,
    expenses INTEGER DEFAULT 0,
    friends INTEGER DEFAULT 0,
    friends_friends INTEGER DEFAULT 0,
    recharged INTEGER DEFAULT 0,
    bonus INTEGER DEFAULT 0,
    withdraw INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Таблица истории обработок
CREATE TABLE IF NOT EXISTS processing_history (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    original_photo_url TEXT,
    processed_photo_url TEXT,
    edit_type VARCHAR(100),
    custom_prompt TEXT,
    cost INTEGER DEFAULT 15,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Таблица рефералов
CREATE TABLE IF NOT EXISTS referrals (
    id SERIAL PRIMARY KEY,
    referrer_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    referred_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    bonus INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(referrer_id, referred_id)
);

-- 5. Добавляем тестового пользователя (для разработки)
INSERT INTO users (telegram_id, username, first_name, balance, generations)
VALUES (123456789, 'test_user', 'Тестовый', 500, 10)
ON CONFLICT (telegram_id) DO NOTHING;

-- 6. Индексы для ускорения запросов
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_history_user_id ON processing_history(telegram_id);
CREATE INDEX IF NOT EXISTS idx_history_created_at ON processing_history(created_at);
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);

-- 7. Функция автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 8. Триггер для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 9. Проверка: показать все таблицы
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;