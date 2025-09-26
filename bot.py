import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ВСТАВЬ СЮДА СВОЙ ТОКЕН ОТ BOTFATHER!
BOT_TOKEN = "8261463641:AAFDksPqqr_xhHB1rJqfgVTff22B0VE21yc"

# ========== НАСТРОЙКА БАЗЫ ДАННЫХ ==========
def init_db():
    """Создает базу данных и таблицу для расходов, если они не существуют."""
    conn = sqlite3.connect('expenses.db', check_same_thread=False)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            category TEXT,
            date TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Инициализируем базу данных при старте
init_db()

# ========== КОМАНДА /start ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение при команде /start."""
    welcome_text = """
    💰 *Привет! Я твой бот для учета расходов.*

    Просто напиши мне сумму и категорию расхода, например:
    *250 обед*
    *1000 такси*

    📊 *Доступные команды:*
    /start - показать это сообщение
    /today - расходы за сегодня
    /month - статистика по категориям за текущий месяц
    /undo - удалить последнюю запись (если ошиблись)
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# ========== КОМАНДА /today ==========
async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает сумму расходов за сегодня."""
    user_id = update.effective_user.id
    today = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect('expenses.db', check_same_thread=False)
    cur = conn.cursor()
    cur.execute(
        'SELECT SUM(amount) FROM expenses WHERE user_id = ? AND date LIKE ?',
        (user_id, today + '%')
    )
    total = cur.fetchone()[0]
    conn.close()

    if total is None:
        total = 0

    await update.message.reply_text(f'📊 *Расходы за сегодня:* {total:.2f} руб.', parse_mode='Markdown')

# ========== КОМАНДА /month ==========
async def month_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику по категориям за текущий месяц."""
    user_id = update.effective_user.id
    current_month = datetime.now().strftime("%Y-%m")

    conn = sqlite3.connect('expenses.db', check_same_thread=False)
    cur = conn.cursor()
    cur.execute('''
        SELECT category, SUM(amount) 
        FROM expenses 
        WHERE user_id = ? AND date LIKE ?
        GROUP BY category
    ''', (user_id, current_month + '%'))
    records = cur.fetchall()
    conn.close()

    if not records:
        await update.message.reply_text("За этот месяц расходов пока нет.")
        return

    response = "📈 *Расходы за этот месяц по категориям:*\n"
    for category, total in records:
        response += f"• *{category}*: {total:.2f} руб.\n"

    total_month = sum([total for _, total in records])
    response += f"\n💵 *Итого за месяц:* {total_month:.2f} руб."

    await update.message.reply_text(response, parse_mode='Markdown')

# ========== КОМАНДА /undo ========== (НОВАЯ ФУНКЦИЯ!)
async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет последнюю добавленную запись пользователя."""
    user_id = update.effective_user.id

    conn = sqlite3.connect('expenses.db', check_same_thread=False)
    cur = conn.cursor()

    # Находим последнюю запись пользователя
    cur.execute('''
        SELECT id, amount, category FROM expenses 
        WHERE user_id = ? 
        ORDER BY id DESC 
        LIMIT 1
    ''', (user_id,))
    last_record = cur.fetchone()

    if last_record:
        # Если запись найдена - удаляем ее
        record_id, amount, category = last_record
        cur.execute('DELETE FROM expenses WHERE id = ?', (record_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f'❌ *Запись удалена:* {amount} руб. на "{category}"', parse_mode='Markdown')
    else:
        conn.close()
        await update.message.reply_text('ℹ️ *Нечего удалять.* Вы еще не добавили ни одной записи.', parse_mode='Markdown')

# ========== ОБРАБОТКА СООБЩЕНИЙ С РАСХОДАМИ ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения с расходами."""
    user_id = update.effective_user.id
    user_message = update.message.text

    try:
        # Пытаемся разделить сообщение на сумму и категорию
        parts = user_message.split(' ', 1)
        amount = float(parts[0])
        category = parts[1].lower().strip() if len(parts) > 1 else 'другое'

        # Сохраняем в базу данных
        conn = sqlite3.connect('expenses.db', check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)',
            (user_id, amount, category, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()

        await update.message.reply_text(f'✅ *Расход {amount} руб. на "{category}" добавлен!*', parse_mode='Markdown')

    except (ValueError, IndexError):
        await update.message.reply_text('❌ *Неправильный формат.* Напишите, например, так: "100 кофе" или "500 такси"', parse_mode='Markdown')

# ========== ОБРАБОТКА ОШИБОК ==========
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ошибки, чтобы бот не падал."""
    print(f"Произошла ошибка: {context.error}")

# ========== ЗАПУСК БОТА ==========
def main():
    """Основная функция, которая запускает бота."""
    # Создаем приложение и передаем ему токен
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("month", month_command))
    application.add_handler(CommandHandler("undo", undo_command))  # НОВЫЙ ОБРАБОТЧИК!
    
    # Обработчик для текстовых сообщений (предполагаем, что это новые расходы)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Обработчик ошибок
    application.add_error_handler(error_handler)

    # Запускаем бота в режиме опроса серверов Telegram
    print("🟢 Бот запущен и слушает сообщения...")
    application.run_polling()

# Точка входа в программу
if __name__ == '__main__':
    main()
