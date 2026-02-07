from telegram import MessageEntity
import random
import re
import json
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# ===== НАСТРОЙКИ =====
TOKEN = "8529025317:AAFtVpp70nj0m-xNCAqn-z12mhWDYmC0Bp4"
ADMIN_USERNAME = "@Anonveil"
ADMIN_ID = 7162818793  # ← ВСТАВЬ СВОЙ user_id
VALUE_777 = 64

# ===== ФАЙЛЫ =====
GIFTS_FILE = Path("gifts.json")
WINNERS_FILE = Path("winners.log")
TOURNAMENT_FILE = Path("tournament.json")

# 👇 ID чата со слотами и канала
SLOT_CHAT_ID = -1002706747017      # ← ВСТАВЬ ID ЧАТА
INFO_CHANNEL_ID = -1003823627924   # ← ВСТАВЬ ID КАНАЛА


# ===== ХРАНИЛИЩА =====
users_spins = {}
GIFTS = []  # [{name, link}]
tournament_draft = {}


# ===== PREMIUM EMOJI IDS =====
EMOJI_LOGO = "5348501505030780591"
EMOJI_7 = "5443135830883313930"
EMOJI_ACTION = "5235989279024373566"
EMOJI_NFT = "5053473385355412667"
EMOJI_BANK = "4965219701572503640"
EMOJI_TOP = "5188344996356448758"
EMOJI_PIN = "5397782960512444700"

def e(eid: str) -> str:
    return f'<tg-emoji emoji-id="{eid}">◻</tg-emoji>'

def ce(offset: int, length: int, emoji_id: str):
    return MessageEntity(
        type=MessageEntity.CUSTOM_EMOJI,
        offset=offset,
        length=length,
        custom_emoji_id=emoji_id
    )


# ===== УТИЛИТЫ =====
# ===== УТИЛИТЫ =====
def extract_gift_name(link: str) -> str:
    slug = link.rstrip("/").split("/")[-1]
    slug = slug.replace("-", " ")
    slug = re.sub(r"(\D)(\d+)$", r"\1 #\2", slug)
    return slug.strip()


def load_gifts():
    global GIFTS
    if GIFTS_FILE.exists():
        GIFTS = json.loads(GIFTS_FILE.read_text(encoding="utf-8"))


def save_gifts():
    GIFTS_FILE.write_text(
        json.dumps(GIFTS, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def log_winner(user, gift):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = (
        f"[{timestamp}] "
        f"{user.id} | "
        f"{user.username or user.full_name} | "
        f"{gift['name']} | "
        f"{gift['link']}\n"
    )
    WINNERS_FILE.write_text(
        WINNERS_FILE.read_text(encoding="utf-8") + line
        if WINNERS_FILE.exists() else line,
        encoding="utf-8"
    )


async def post_winner_to_channel(bot, user, gift):
    # ссылка на пользователя
    if user.username:
        user_link = f"<a href='https://t.me/{user.username}'>@{user.username}</a>"
    else:
        user_link = f"<a href='tg://user?id={user.id}'>Победитель</a>"

    text = (
        f"{e(EMOJI_7)}{e(EMOJI_7)}{e(EMOJI_7)} <b>ДЖЕКПОТ ВЫПАЛ!</b>\n\n"
        f"{e(EMOJI_TOP)} <b>Победитель:</b> {user_link}\n\n"
        f"{e(EMOJI_NFT)} <b>Выигрыш:</b>\n"
        f"🎁 <a href='{gift['link']}'><b>{gift['name']}</b></a>\n\n"
        f"{e(EMOJI_BANK)} <b>Банк подарков:</b> {ADMIN_USERNAME}\n\n"
        f"{e(EMOJI_PIN)} <i>Крути 🎰 — следующий пост может быть про тебя</i>"
    )

    await bot.send_message(
        chat_id=INFO_CHANNEL_ID,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=False
    )


    # ===== УТИЛИТЫ ТУРНИРА =====
def save_tournament(data):
    TOURNAMENT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def load_tournament():
    if TOURNAMENT_FILE.exists():
        return json.loads(TOURNAMENT_FILE.read_text(encoding="utf-8"))
    return None

# ===== КОМАНДЫ =====

async def add_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет прав.")
        return

    if not context.args:
        await update.message.reply_text(
            "❗ Используй:\n/addgift https://t.me/nft/InstantRamen-176452"
        )
        return

    link = context.args[0]
    name = extract_gift_name(link)

    GIFTS.append({"name": name, "link": link})
    save_gifts()

    await update.message.reply_text(
        f"✅ Подарок добавлен:\n<b>{name}</b>\n"
        f"Всего подарков: {len(GIFTS)}",
        parse_mode="HTML"
    )


async def list_gifts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет прав.")
        return

    if not GIFTS:
        await update.message.reply_text("📭 Список подарков пуст.")
        return

    text = "<b>🎁 Текущие подарки:</b>\n\n"
    for i, gift in enumerate(GIFTS, start=1):
        text += f"{i}. <a href='{gift['link']}'>{gift['name']}</a>\n"

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )


async def remove_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет прав.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❗ Используй:\n/removegift НОМЕР")
        return

    idx = int(context.args[0]) - 1
    if idx < 0 or idx >= len(GIFTS):
        await update.message.reply_text("❗ Неверный номер.")
        return

    removed = GIFTS.pop(idx)
    save_gifts()

    await update.message.reply_text(
        f"🗑️ Удалён подарок:\n<b>{removed['name']}</b>",
        parse_mode="HTML"
    )


async def winners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет прав.")
        return

    if not WINNERS_FILE.exists():
        await update.message.reply_text("📭 Победителей пока нет.")
        return

    lines = WINNERS_FILE.read_text(encoding="utf-8").splitlines()
    stats = {}
    last = []

    for line in lines:
        try:
            parts = line.split(" | ")
            user = parts[1].strip()
            gift = parts[2].strip()

            if not user.startswith("@"):
                user = "@" + user

            stats[user] = stats.get(user, 0) + 1
            last.append(f"👤 {user} — 🎁 {gift}")
        except:
            continue

    text = "<b>🏆 Последние победители:</b>\n\n"
    for row in last[-10:]:
        text += f"{row}\n"

    text += "\n<b>📊 Статистика выигрышей:</b>\n"
    for user, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        text += f"• {user}: <b>{count}</b>\n"

    await update.message.reply_text(text, parse_mode="HTML")


async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет прав.")
        return

    text = (
    "<b>🛠 Админ-панель GIFT DROP BOT</b>\n"
    "<i>Команды работают только в личных сообщениях</i>\n\n"

    "<b>🎁 ПОДАРКИ</b>\n"
    "➕ <code>/addgift LINK</code> — добавить NFT / подарок\n"
    "📜 <code>/listgifts</code> — список подарков\n"
    "❌ <code>/removegift N</code> — удалить подарок\n\n"

    "<b>🏆 ПОБЕДИТЕЛИ</b>\n"
    "👑 <code>/winners</code> — последние победители и статистика\n\n"

    "<b>🏁 ТУРНИРЫ</b>\n"
    "🚀 <code>/turnirstart</code> — создать турнир (пошагово)\n"
    "📋 <code>/turnirlist</code> — активный турнир\n"
    "🛑 <code>/turnirend</code> — завершить турнир\n"
    "📢 <code>/turnir_chat</code> — опубликовать в чате\n"
    "📣 <code>/turnir_channel</code> — опубликовать в канале\n\n"

    "<b>ℹ️ ПОДСКАЗКА</b>\n"
    "• Активен только <b>один турнир</b>\n"
    "• Текст турнира ты задаёшь <b>сам</b>\n"
    "• Дата окончания — для контроля\n"
)


    await update.message.reply_text(text, parse_mode="HTML")



# ===== ТУРНИРЫ =====

tournament_draft = {}


async def turnirstart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет прав.")
        return

    tournament_draft.clear()
    tournament_draft["step"] = "text"

    await update.message.reply_text(
        "🏆 <b>Создание турнира</b>\n\n"
        "Отправь <b>текст турнира</b>.",
        parse_mode="HTML"
    )


async def tournament_steps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not tournament_draft:
        return

    text = update.message.text.strip()

    if tournament_draft["step"] == "text":
        tournament_draft["text"] = text
        tournament_draft["step"] = "days"
        await update.message.reply_text(
            "⏳ <b>Сколько дней длится турнир?</b>\n"
            "Напиши <b>только число</b>.",
            parse_mode="HTML"
        )
        return

    if tournament_draft["step"] == "days":
        if not text.isdigit():
            await update.message.reply_text("❗ Введи число дней.")
            return

        days = int(text)
        end = datetime.now() + timedelta(days=days)

        save_tournament({
            "text": tournament_draft["text"],
            "start": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "end": end.strftime("%Y-%m-%d %H:%M"),
            "days": days
        })

        tournament_draft.clear()

        await update.message.reply_text(
            "✅ <b>Турнир создан</b>\n\n"
            "Доступные действия:\n"
            "/turnir_chat — опубликовать в чате\n"
            "/turnir_channel — опубликовать в канале",
            parse_mode="HTML"
        )


async def turnir_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет прав.")
        return

    tournament = load_tournament()
    if not tournament:
        await update.message.reply_text("📭 Активных турниров нет.")
        return

    await update.message.reply_text(
        "<b>🏆 Активный турнир</b>\n\n"
        f"🟢 Запущен: {tournament['start']}\n"
        f"🔴 Окончание: {tournament['end']}\n"
        f"⏳ Длительность: {tournament['days']} дней",
        parse_mode="HTML"
    )


async def turnir_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет прав.")
        return

    if not TOURNAMENT_FILE.exists():
        await update.message.reply_text("📭 Активного турнира нет.")
        return

    TOURNAMENT_FILE.unlink()
    await update.message.reply_text(
        "🛑 <b>Турнир завершён.</b>\n"
        "Теперь можно создать новый.",
        parse_mode="HTML"
    )


async def turnir_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    tournament = load_tournament()
    if not tournament:
        await update.message.reply_text("❗ Турнир не найден.")
        return

    await context.bot.send_message(
        SLOT_CHAT_ID,
        tournament["text"],
        parse_mode="HTML"
    )

    await update.message.reply_text("✅ Опубликовано в чате.")


async def turnir_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    tournament = load_tournament()
    if not tournament:
        await update.message.reply_text("❗ Турнир не найден.")
        return

    await context.bot.send_message(
        INFO_CHANNEL_ID,
        tournament["text"],
        parse_mode="HTML"
    )

    await update.message.reply_text("✅ Опубликовано в канале.")



# ===== 🎰 ОБРАБОТКА =====

async def handle_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.dice or msg.dice.emoji != "🎰":
        return

    uid = msg.from_user.id
    users_spins.setdefault(uid, 0)
    users_spins[uid] += 1

    if users_spins[uid] == 1:
        text = (
            f"{e(EMOJI_LOGO)} <b>Добро пожаловать в GIFT DROP</b> "
            f"{e(EMOJI_7)}{e(EMOJI_7)}{e(EMOJI_7)}\n\n"
            "<b>Давай давай, крути крути — здесь всё решает удача. "
            "Один прокрут может изменить всё.</b>\n\n"
            f"{e(EMOJI_ACTION)} <b>выбил</b> "
            f"{e(EMOJI_7)}{e(EMOJI_7)}{e(EMOJI_7)} — "
            f"получил NFT подарок до 15 000 {e(EMOJI_NFT)}.\n\n"
            f"{e(EMOJI_BANK)} <b>Банк подарков</b> — {ADMIN_USERNAME}. "
            "Может выпасть любой подарок, даже самый <b>дорогой.</b>\n\n"
            f"{e(EMOJI_TOP)} Лидер недели по прокрутам получает бесплатный NFT.\n"
             f"{e(EMOJI_PIN)} Новости, турниры и пруфы победителей — "
            f"<a href='https://t.me/giftdropnw'><b>в нашем канале</b></a>\n"
            f"{e(EMOJI_PIN)} Вся важная информация всегда в закрепе."
        )

        await msg.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)
        return

    # ===== ДЖЕКПОТ =====
    if msg.dice.value == VALUE_777:
        if GIFTS:
            gift = random.choice(GIFTS)
            GIFTS.remove(gift)
            save_gifts()

            log_winner(msg.from_user, gift)

            # 🔥 ПУБЛИКАЦИЯ В КАНАЛ
            await post_winner_to_channel(
                context.bot,
                msg.from_user,
                gift
            )

            gift_text = (
                f"<a href='{gift['link']}'>{gift['name']}</a>\n"
            )
        else:
            gift_text = "<i>Подарки закончились. Свяжись с администратором.</i>"

        text = (
            f"{e(EMOJI_7)}{e(EMOJI_7)}{e(EMOJI_7)} <b>ДЖЕКПОТ!</b>\n\n"
            f"<b>Поздравляем!</b>\n"
            f"Ты выбил заветную комбинацию "
            f"{e(EMOJI_7)}{e(EMOJI_7)}{e(EMOJI_7)}.\n\n"
            f"<b>Твой приз:</b>\n{gift_text}\n\n"
            f"{e(EMOJI_BANK)} <b>Банк подарков — {ADMIN_USERNAME}</b>"
        )

        await msg.reply_text(
            text,
            parse_mode="HTML",
            disable_web_page_preview=False
        )

load_gifts()

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("addgift", add_gift, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("listgifts", list_gifts, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("removegift", remove_gift, filters=filters.ChatType.PRIVATE))
app.add_handler(MessageHandler(filters.Dice.SLOT_MACHINE, handle_dice))
app.add_handler(CommandHandler("winners", winners, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("admin", admin_help, filters=filters.ChatType.PRIVATE))

# турниры
app.add_handler(CommandHandler("turnirstart", turnirstart, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("turnirlist", turnir_list, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("turnirend", turnir_end, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("turnir_chat", turnir_chat, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("turnir_channel", turnir_channel, filters=filters.ChatType.PRIVATE))

# шаги создания турнира (ВАЖНО: без команд)
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, tournament_steps)
)

print("✅ GIFT DROP BOT запущен")
app.run_polling(allowed_updates=["message"])
