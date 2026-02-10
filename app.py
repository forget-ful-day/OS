import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

UTC = timezone.utc


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


def parse_admin_ids(raw: str) -> set[int]:
    return {int(x.strip()) for x in raw.split(",") if x.strip()}


def format_dt(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def parse_duration(label: str) -> timedelta:
    parts = label.strip().split(" ")
    if len(parts) < 2:
        raise ValueError("Неверный формат периода")
    amount = int(parts[0])
    unit = parts[1].lower()

    if "минут" in unit:
        return timedelta(minutes=amount)
    if "час" in unit:
        return timedelta(hours=amount)
    if "день" in unit or "дня" in unit or "дней" in unit:
        return timedelta(days=amount)
    if "недел" in unit:
        return timedelta(weeks=amount)
    if "месяц" in unit or "месяц" in unit or "месяцев" in unit:
        return timedelta(days=30 * amount)
    if "год" in unit or "лет" in unit or "года" in unit:
        return timedelta(days=365 * amount)
    raise ValueError(f"Неизвестная единица времени в периоде: {unit}")


class DB:
    def __init__(self, path: str):
        self.path = path

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS channels (
                    chat_id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    added_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    start_at TEXT NOT NULL,
                    end_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY(user_id) REFERENCES users(user_id),
                    FOREIGN KEY(channel_id) REFERENCES channels(chat_id)
                );

                CREATE TABLE IF NOT EXISTS payment_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    duration_label TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    bank TEXT NOT NULL,
                    receipt_file_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    admin_id INTEGER,
                    created_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id),
                    FOREIGN KEY(channel_id) REFERENCES channels(chat_id)
                );
                """
            )
            await db.commit()

    async def ensure_defaults(self, phone: str, banks: list[str]):
        prices = {
            "1 минут": 10,
            "1 час": 40,
            "1 день": 50,
            "1 неделя": 100,
            "1 месяц": 110,
            "1 год": 150,
        }
        await self.set_if_missing("phone", phone)
        await self.set_if_missing("banks", json.dumps(banks, ensure_ascii=False))
        await self.set_if_missing("prices", json.dumps(prices, ensure_ascii=False))

    async def set_if_missing(self, key: str, value: str):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT 1 FROM settings WHERE key = ?", (key,))
            row = await cur.fetchone()
            if not row:
                await db.execute(
                    "INSERT INTO settings(key, value) VALUES(?, ?)",
                    (key, value),
                )
                await db.commit()

    async def get_setting(self, key: str, default: str = "") -> str:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = await cur.fetchone()
            return row[0] if row else default

    async def set_setting(self, key: str, value: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO settings(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (key, value),
            )
            await db.commit()

    async def upsert_channel(self, chat_id: int, title: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO channels(chat_id, title, active, added_at)
                VALUES(?, ?, 1, ?)
                ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title, active=1
                """,
                (chat_id, title, now_utc().isoformat()),
            )
            await db.commit()

    async def deactivate_channel(self, chat_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE channels SET active=0 WHERE chat_id=?", (chat_id,))
            await db.commit()

    async def list_channels(self) -> list[tuple[int, str, int]]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT chat_id, title, active FROM channels ORDER BY added_at DESC"
            )
            return await cur.fetchall()

    async def get_channel(self, chat_id: int) -> Optional[tuple[int, str, int]]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT chat_id, title, active FROM channels WHERE chat_id = ?", (chat_id,)
            )
            return await cur.fetchone()

    async def upsert_user(self, user_id: int, username: str | None, full_name: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO users(user_id, username, full_name, created_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    full_name=excluded.full_name
                """,
                (user_id, username, full_name, now_utc().isoformat()),
            )
            await db.commit()

    async def create_payment_request(
        self,
        user_id: int,
        channel_id: int,
        duration_label: str,
        amount: int,
        bank: str,
        receipt_file_id: str,
    ) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                INSERT INTO payment_requests(
                    user_id, channel_id, duration_label, amount, bank, receipt_file_id, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    channel_id,
                    duration_label,
                    amount,
                    bank,
                    receipt_file_id,
                    now_utc().isoformat(),
                ),
            )
            await db.commit()
            return cur.lastrowid

    async def get_payment_request(self, request_id: int):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT id, user_id, channel_id, duration_label, amount, bank,
                       receipt_file_id, status, admin_id, created_at
                FROM payment_requests
                WHERE id = ?
                """,
                (request_id,),
            )
            return await cur.fetchone()

    async def set_payment_status(self, request_id: int, status: str, admin_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                UPDATE payment_requests
                SET status = ?, admin_id = ?, reviewed_at = ?
                WHERE id = ?
                """,
                (status, admin_id, now_utc().isoformat(), request_id),
            )
            await db.commit()

    async def add_subscription(self, user_id: int, channel_id: int, duration: timedelta):
        start = now_utc()
        end = start + duration
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO subscriptions(user_id, channel_id, start_at, end_at, active)
                VALUES(?, ?, ?, ?, 1)
                """,
                (user_id, channel_id, start.isoformat(), end.isoformat()),
            )
            await db.commit()
        return start, end

    async def get_stats(self):
        async with aiosqlite.connect(self.path) as db:
            users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
            channels = (
                await (await db.execute("SELECT COUNT(*) FROM channels WHERE active=1")).fetchone()
            )[0]
            pending = (
                await (
                    await db.execute(
                        "SELECT COUNT(*) FROM payment_requests WHERE status='pending'"
                    )
                ).fetchone()
            )[0]
            active_subs = (
                await (
                    await db.execute(
                        "SELECT COUNT(*) FROM subscriptions WHERE active=1 AND end_at > ?",
                        (now_utc().isoformat(),),
                    )
                ).fetchone()
            )[0]
            return users, channels, pending, active_subs

    async def list_people(self):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT u.user_id, u.username, u.full_name,
                       COUNT(s.id) FILTER (WHERE s.active=1 AND s.end_at > ?) as active_sub_count
                FROM users u
                LEFT JOIN subscriptions s ON s.user_id = u.user_id
                GROUP BY u.user_id
                ORDER BY u.created_at DESC
                LIMIT 50
                """,
                (now_utc().isoformat(),),
            )
            return await cur.fetchall()

    async def list_expired_subscriptions(self):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT id, user_id, channel_id
                FROM subscriptions
                WHERE active=1 AND end_at <= ?
                """,
                (now_utc().isoformat(),),
            )
            return await cur.fetchall()

    async def deactivate_subscription(self, sub_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE subscriptions SET active=0 WHERE id=?", (sub_id,))
            await db.commit()


class PriceStates(StatesGroup):
    waiting_prices = State()


class BanksStates(StatesGroup):
    waiting_banks = State()


class PaymentStates(StatesGroup):
    waiting_receipt = State()


@dataclass
class AppContext:
    db: DB
    admin_ids: set[int]
    admin_bot: Bot
    payment_bot: Bot


def admin_only(admin_ids: set[int], user_id: int) -> bool:
    return user_id in admin_ids


def prices_to_text(prices: dict[str, int]) -> str:
    return "\n".join([f"{k}-{v}руб" for k, v in prices.items()])


def parse_prices_text(raw: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if "-" not in line:
            raise ValueError(f"Строка без '-' : {line}")
        left, right = [x.strip() for x in line.split("-", 1)]
        value_str = "".join(ch for ch in right if ch.isdigit())
        if not value_str:
            raise ValueError(f"Нет цены в строке: {line}")
        result[left] = int(value_str)
    if not result:
        raise ValueError("Прайс пустой")
    return result


def payment_keyboard(channels, _prices):
    rows = []
    for chat_id, title, active in channels:
        if not active:
            continue
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"📢 {title}", callback_data=f"pick_channel:{chat_id}"
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def duration_keyboard(prices: dict[str, int]):
    rows = []
    for label, amount in prices.items():
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{label} — {amount} ₽",
                    callback_data=f"pick_duration:{label}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_channels")])
    return InlineKeyboardMarkup(inline_keyboard=rows)



async def download_photo_bytes(source_bot: Bot, source_file_id: str) -> Optional[tuple[bytes, str]]:
    """Скачивает фото через одного бота и возвращает байты + имя файла."""
    try:
        tg_file = await source_bot.get_file(source_file_id)
        if not tg_file.file_path:
            return None
        stream = await source_bot.download_file(tg_file.file_path)
        payload = stream.read()
        if not payload:
            return None
        filename = tg_file.file_path.rsplit("/", 1)[-1] or "receipt.jpg"
        return payload, filename
    except Exception:
        logging.exception("Ошибка подготовки изображения чека для пересылки")
        return None

def banks_keyboard(banks: list[str]):
    rows = []
    for bank in banks:
        rows.append([InlineKeyboardButton(text=bank, callback_data=f"pick_bank:{bank}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def build_routers(ctx: AppContext):
    admin_router = Router(name="admin")
    payment_router = Router(name="payment")

    @admin_router.message(Command("start"))
    async def admin_start(message: Message):
        if not admin_only(ctx.admin_ids, message.from_user.id):
            return
        await message.answer(
            "Админ-бот активен.\n"
            "Команды:\n"
            "/people\n/price\n/price_edit\n/channel\n/channels\n/statistics\n/phone\n/banks\n/banks_edit"
        )

    @admin_router.my_chat_member()
    async def channel_autodetect(event: ChatMemberUpdated):
        chat = event.chat
        new_status = event.new_chat_member.status
        if chat.type not in {"channel", "supergroup"}:
            return

        if new_status in {
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER,
        }:
            await ctx.db.upsert_channel(chat.id, chat.title or str(chat.id))
        elif new_status in {
            ChatMemberStatus.LEFT,
            ChatMemberStatus.KICKED,
            ChatMemberStatus.RESTRICTED,
        }:
            await ctx.db.deactivate_channel(chat.id)

    @admin_router.message(Command("channels"))
    @admin_router.message(Command("channel"))
    async def channels_list(message: Message):
        if not admin_only(ctx.admin_ids, message.from_user.id):
            return
        channels = await ctx.db.list_channels()
        if not channels:
            await message.answer("Каналов пока нет. Добавьте админ-бота в канал.")
            return
        text = "Каналы:\n" + "\n".join(
            [f"• {title} (`{chat_id}`) — {'активен' if active else 'неактивен'}" for chat_id, title, active in channels]
        )
        await message.answer(text, parse_mode=ParseMode.MARKDOWN)

    @admin_router.message(Command("price"))
    async def show_price(message: Message):
        if not admin_only(ctx.admin_ids, message.from_user.id):
            return
        prices = json.loads(await ctx.db.get_setting("prices", "{}"))
        await message.answer("Текущий прайс:\n" + prices_to_text(prices))

    @admin_router.message(Command("price_edit"))
    async def price_edit(message: Message, state: FSMContext):
        if not admin_only(ctx.admin_ids, message.from_user.id):
            return
        await state.set_state(PriceStates.waiting_prices)
        await message.answer(
            "Отправьте новый прайс строками, например:\n"
            "1 минут-10руб\n1 час-40руб\n1 день-50руб"
        )

    @admin_router.message(PriceStates.waiting_prices)
    async def save_prices(message: Message, state: FSMContext):
        if not admin_only(ctx.admin_ids, message.from_user.id):
            return
        try:
            parsed = parse_prices_text(message.text or "")
        except Exception as e:
            await message.answer(f"Ошибка: {e}")
            return
        await ctx.db.set_setting("prices", json.dumps(parsed, ensure_ascii=False))
        await state.clear()
        await message.answer("Прайс обновлён:\n" + prices_to_text(parsed))

    @admin_router.message(Command("phone"))
    async def set_phone(message: Message):
        if not admin_only(ctx.admin_ids, message.from_user.id):
            return
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) == 1:
            phone = await ctx.db.get_setting("phone")
            await message.answer(f"Текущий номер: {phone}\nИспользование: /phone +79990001122")
            return
        await ctx.db.set_setting("phone", parts[1].strip())
        await message.answer("Номер телефона обновлён.")

    @admin_router.message(Command("banks"))
    async def banks_show(message: Message):
        if not admin_only(ctx.admin_ids, message.from_user.id):
            return
        banks = json.loads(await ctx.db.get_setting("banks", "[]"))
        await message.answer("Банки: " + ", ".join(banks))

    @admin_router.message(Command("banks_edit"))
    async def banks_edit(message: Message, state: FSMContext):
        if not admin_only(ctx.admin_ids, message.from_user.id):
            return
        await state.set_state(BanksStates.waiting_banks)
        await message.answer("Отправьте список банков через запятую. Пример: Sber, Tinkoff, Alfa")

    @admin_router.message(BanksStates.waiting_banks)
    async def banks_save(message: Message, state: FSMContext):
        if not admin_only(ctx.admin_ids, message.from_user.id):
            return
        banks = [x.strip() for x in (message.text or "").split(",") if x.strip()]
        if not banks:
            await message.answer("Список пуст")
            return
        await ctx.db.set_setting("banks", json.dumps(banks, ensure_ascii=False))
        await state.clear()
        await message.answer("Банки обновлены: " + ", ".join(banks))

    @admin_router.message(Command("statistics"))
    async def stats(message: Message):
        if not admin_only(ctx.admin_ids, message.from_user.id):
            return
        users, channels, pending, active_subs = await ctx.db.get_stats()
        await message.answer(
            "Статистика:\n"
            f"Пользователей: {users}\n"
            f"Активных каналов: {channels}\n"
            f"Ожидают проверки чеков: {pending}\n"
            f"Активных подписок: {active_subs}"
        )

    @admin_router.message(Command("people"))
    async def people(message: Message):
        if not admin_only(ctx.admin_ids, message.from_user.id):
            return
        rows = await ctx.db.list_people()
        if not rows:
            await message.answer("Пока нет людей.")
            return
        text = "Люди (последние 50):\n"
        for user_id, username, full_name, active_count in rows:
            text += (
                f"• {full_name} (@{username or '-'}) id={user_id}, "
                f"активных подписок: {active_count}\n"
            )
        await message.answer(text)

    @admin_router.callback_query(F.data.startswith("approve:"))
    async def approve_payment(call: CallbackQuery):
        if not admin_only(ctx.admin_ids, call.from_user.id):
            await call.answer("Нет доступа", show_alert=True)
            return
        request_id = int(call.data.split(":", 1)[1])
        req = await ctx.db.get_payment_request(request_id)
        if not req:
            await call.answer("Заявка не найдена", show_alert=True)
            return
        _, user_id, channel_id, duration_label, amount, bank, _, status, _, _ = req
        if status != "pending":
            await call.answer("Уже обработано")
            return

        channel = await ctx.db.get_channel(channel_id)
        if not channel or not channel[2]:
            await call.answer("Канал не активен", show_alert=True)
            return

        duration = parse_duration(duration_label)
        start, end = await ctx.db.add_subscription(user_id, channel_id, duration)
        await ctx.db.set_payment_status(request_id, "approved", call.from_user.id)

        link = await ctx.admin_bot.create_chat_invite_link(
            chat_id=channel_id,
            member_limit=1,
            expire_date=end,
            creates_join_request=False,
            name=f"sub_{user_id}_{request_id}",
        )
        await ctx.payment_bot.send_message(
            user_id,
            (
                "✅ Оплата подтверждена!\n"
                f"Канал: {channel[1]}\n"
                f"Срок: {duration_label}\n"
                f"Сумма: {amount} ₽ ({bank})\n"
                f"Доступ до: {format_dt(end)}\n\n"
                f"Одноразовая ссылка:\n{link.invite_link}"
            ),
        )
        await call.message.edit_caption(
            (call.message.caption or "") + "\n\n✅ Подтверждено",
            reply_markup=None,
        )
        await call.answer("Подтверждено")

    @admin_router.callback_query(F.data.startswith("reject:"))
    async def reject_payment(call: CallbackQuery):
        if not admin_only(ctx.admin_ids, call.from_user.id):
            await call.answer("Нет доступа", show_alert=True)
            return
        request_id = int(call.data.split(":", 1)[1])
        req = await ctx.db.get_payment_request(request_id)
        if not req:
            await call.answer("Заявка не найдена", show_alert=True)
            return
        _, user_id, _, _, _, _, _, status, _, _ = req
        if status != "pending":
            await call.answer("Уже обработано")
            return
        await ctx.db.set_payment_status(request_id, "rejected", call.from_user.id)
        await ctx.payment_bot.send_message(
            user_id,
            "❌ Чек отклонён администратором. Пожалуйста, проверьте оплату и отправьте новый чек.",
        )
        await call.message.edit_caption(
            (call.message.caption or "") + "\n\n❌ Отклонено",
            reply_markup=None,
        )
        await call.answer("Отклонено")

    @payment_router.message(Command("start"))
    async def user_start(message: Message):
        await ctx.db.upsert_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
        )
        channels = await ctx.db.list_channels()
        if not channels:
            await message.answer("Сейчас нет доступных каналов.")
            return
        prices = json.loads(await ctx.db.get_setting("prices", "{}"))
        await message.answer(
            "Выберите канал:",
            reply_markup=payment_keyboard(channels, prices),
        )

    @payment_router.callback_query(F.data == "refresh")
    async def refresh(call: CallbackQuery):
        channels = await ctx.db.list_channels()
        prices = json.loads(await ctx.db.get_setting("prices", "{}"))
        await call.message.edit_reply_markup(reply_markup=payment_keyboard(channels, prices))
        await call.answer("Обновлено ✅")

    @payment_router.callback_query(F.data.startswith("pick_channel:"))
    async def pick_channel(call: CallbackQuery, state: FSMContext):
        channel_id = int(call.data.split(":", 1)[1])
        channel = await ctx.db.get_channel(channel_id)
        if not channel or not channel[2]:
            await call.answer("Канал не найден", show_alert=True)
            return
        prices = json.loads(await ctx.db.get_setting("prices", "{}"))
        await state.update_data(channel_id=channel_id)
        await call.message.edit_text(
            f"Канал: {channel[1]}\nВыберите период:",
            reply_markup=duration_keyboard(prices),
        )
        await call.answer()

    @payment_router.callback_query(F.data == "back_to_channels")
    async def back_to_channels(call: CallbackQuery):
        channels = await ctx.db.list_channels()
        prices = json.loads(await ctx.db.get_setting("prices", "{}"))
        await call.message.edit_text("Выберите канал:", reply_markup=payment_keyboard(channels, prices))
        await call.answer()

    @payment_router.callback_query(F.data.startswith("pick_duration:"))
    async def pick_duration(call: CallbackQuery, state: FSMContext):
        duration_label = call.data.split(":", 1)[1]
        prices = json.loads(await ctx.db.get_setting("prices", "{}"))
        if duration_label not in prices:
            await call.answer("Период недоступен", show_alert=True)
            return
        await state.update_data(duration_label=duration_label, amount=prices[duration_label])
        banks = json.loads(await ctx.db.get_setting("banks", "[]"))
        await call.message.edit_text(
            f"Период: {duration_label}\nСумма: {prices[duration_label]} ₽\nВыберите банк:",
            reply_markup=banks_keyboard(banks),
        )
        await call.answer()

    @payment_router.callback_query(F.data.startswith("pick_bank:"))
    async def pick_bank(call: CallbackQuery, state: FSMContext):
        bank = call.data.split(":", 1)[1]
        phone = await ctx.db.get_setting("phone")
        await state.update_data(bank=bank)
        await state.set_state(PaymentStates.waiting_receipt)
        await call.message.edit_text(
            (
                f"Банк: {bank}\n"
                f"Переведите сумму на номер: `{phone}`\n"
                "После оплаты отправьте ФОТО чека в этот чат."
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
        await call.answer()

    @payment_router.message(PaymentStates.waiting_receipt, F.photo)
    async def receipt_received(message: Message, state: FSMContext):
        data = await state.get_data()
        channel_id = data.get("channel_id")
        duration_label = data.get("duration_label")
        amount = data.get("amount")
        bank = data.get("bank")
        if not all([channel_id, duration_label, amount, bank]):
            await state.clear()
            await message.answer("Сессия истекла. Нажмите /start")
            return

        await ctx.db.upsert_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
        )

        receipt = message.photo[-1].file_id
        request_id = await ctx.db.create_payment_request(
            user_id=message.from_user.id,
            channel_id=channel_id,
            duration_label=duration_label,
            amount=amount,
            bank=bank,
            receipt_file_id=receipt,
        )

        channel = await ctx.db.get_channel(channel_id)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить", callback_data=f"approve:{request_id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Отменить", callback_data=f"reject:{request_id}"
                    ),
                ]
            ]
        )
        caption = (
            "Новый чек на проверку\n"
            f"Заявка: #{request_id}\n"
            f"Юзер: {message.from_user.full_name} (@{message.from_user.username or '-'})\n"
            f"ID пользователя: {message.from_user.id}\n"
            f"Канал: {channel[1] if channel else channel_id}\n"
            f"Период: {duration_label}\n"
            f"Сумма: {amount} ₽\n"
            f"Время: {format_dt(now_utc())}"
        )
        photo_payload = await download_photo_bytes(ctx.payment_bot, receipt)

        for admin_id in ctx.admin_ids:
            try:
                if photo_payload is not None:
                    payload, filename = photo_payload
                    await ctx.admin_bot.send_photo(
                        chat_id=admin_id,
                        photo=BufferedInputFile(payload, filename=filename),
                        caption=caption,
                        reply_markup=keyboard,
                    )
                else:
                    await ctx.admin_bot.send_message(
                        chat_id=admin_id,
                        text=caption + "\n\n⚠️ Фото чека не удалось прикрепить автоматически.",
                        reply_markup=keyboard,
                    )
            except TelegramBadRequest:
                logging.exception("Не удалось отправить чек администратору %s", admin_id)

        await state.clear()
        await message.answer("Чек отправлен на проверку администратору. Ожидайте подтверждения.")

    @payment_router.message(PaymentStates.waiting_receipt)
    async def receipt_required(message: Message):
        await message.answer("Пожалуйста, отправьте именно фото чека.")

    return admin_router, payment_router


async def subscription_watcher(ctx: AppContext):
    while True:
        try:
            expired = await ctx.db.list_expired_subscriptions()
            for sub_id, user_id, channel_id in expired:
                try:
                    await ctx.admin_bot.ban_chat_member(channel_id, user_id)
                    await ctx.admin_bot.unban_chat_member(channel_id, user_id, only_if_banned=True)
                except TelegramBadRequest:
                    logging.exception("Не удалось удалить пользователя=%s из канала=%s", user_id, channel_id)
                await ctx.db.deactivate_subscription(sub_id)
                try:
                    await ctx.payment_bot.send_message(
                        user_id,
                        f"Срок подписки истек. Доступ к каналу {channel_id} отключен.",
                    )
                except TelegramBadRequest:
                    pass
        except Exception:
            logging.exception("Ошибка фонового обработчика подписок")

        await asyncio.sleep(60)


async def main():
    load_dotenv()

    admin_token = os.getenv("ADMIN_BOT_TOKEN", "")
    payment_token = os.getenv("PAYMENT_BOT_TOKEN", "")
    admin_ids_raw = os.getenv("ADMIN_IDS", "")
    db_path = os.getenv("DB_PATH", "bot.sqlite3")
    default_phone = os.getenv("DEFAULT_PHONE", "+79991234567")
    default_banks = [
        x.strip() for x in os.getenv("DEFAULT_BANKS", "Сбер,Тинькофф,ВТБ").split(",") if x.strip()
    ]

    if not admin_token or not payment_token or not admin_ids_raw:
        raise RuntimeError("Заполните переменные ADMIN_BOT_TOKEN, PAYMENT_BOT_TOKEN и ADMIN_IDS в файле .env")

    admin_ids = parse_admin_ids(admin_ids_raw)

    db = DB(db_path)
    await db.init()
    await db.ensure_defaults(default_phone, default_banks)

    admin_bot = Bot(token=admin_token)
    payment_bot = Bot(token=payment_token)

    ctx = AppContext(
        db=db,
        admin_ids=admin_ids,
        admin_bot=admin_bot,
        payment_bot=payment_bot,
    )

    admin_dp = Dispatcher()
    payment_dp = Dispatcher()

    admin_router, payment_router = await build_routers(ctx)
    admin_dp.include_router(admin_router)
    payment_dp.include_router(payment_router)

    watcher_task = asyncio.create_task(subscription_watcher(ctx))

    try:
        await asyncio.gather(
            admin_dp.start_polling(admin_bot, allowed_updates=admin_dp.resolve_used_update_types()),
            payment_dp.start_polling(
                payment_bot,
                allowed_updates=payment_dp.resolve_used_update_types(),
            ),
        )
    finally:
        watcher_task.cancel()
        await admin_bot.session.close()
        await payment_bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
