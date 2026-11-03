from __future__ import annotations

import html
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.database import (
    clear_dialog_context,
    create_dialog,
    delete_dialog,
    ensure_user,
    get_active_dialog,
    get_admin_stats,
    get_dialog_messages,
    get_or_create_active_dialog,
    get_user,
    get_user_dialogs,
    get_user_history,
    save_message,
    set_active_dialog,
    set_user_field,
)
from app.groq_client import (
    ModelDiscoveryError,
    chat_with_groq,
    detect_language,
    get_available_models,
    split_message,
)
from app.keyboards import history_keyboard, language_keyboard, main_menu_keyboard, model_keyboard, settings_keyboard

router = Router()


async def get_user_profile_text(user_id: int) -> str:
    user = await get_user(user_id)
    if not user:
        return "Профиль не найден."
    active = await get_active_dialog(user_id)
    return (
        "<b>👤 Профиль LumiAI</b>\n\n"
        f"Имя: {html.escape(user['first_name'] or 'Неизвестно')}\n"
        f"Telegram ID: <code>{user['user_id']}</code>\n"
        f"Дата регистрации: {user['registered_at']}\n"
        f"Сообщений: {user['total_messages']}\n"
        f"Диалогов: {user['total_dialogs']}\n"
        f"Выбранная модель: {html.escape(user['selected_model'] or settings.default_model)}\n"
        f"Язык интерфейса: {user['language']}\n"
        f"Активный диалог: {active['title'] if active else 'Нет'}"
    )


async def user_has_model(user_id: int) -> str:
    user = await get_user(user_id)
    return user["selected_model"] or settings.default_model


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    await ensure_user(user.id, user.username, user.first_name, user.last_name)
    await message.answer(
        "<b>🤖 LumiAI</b>\n\nПривет! Я LumiAI — твой интеллектуальный помощник.\n\nЧем могу помочь?",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>📘 Помощь LumiAI</b>\n\n"
        "Команды:\n"
        "/start — запуск\n"
        "/new — новый диалог\n"
        "/clear — очистить контекст\n"
        "/history — история\n"
        "/model — выбрать модель\n"
        "/settings — настройки\n"
        "/profile — профиль\n"
        "/about — о LumiAI\n"
        "/cancel — отмена\n\n"
        "Также можно просто писать сообщения в чат — я отвечу как AI-ассистент."
    )


@router.message(Command("about"))
async def cmd_about(message: Message) -> None:
    await message.answer(
        "<b>🤖 LumiAI</b>\n\n"
        "LumiAI — это интеллектуальный персональный помощник, работающий через Groq API.\n\n"
        "Он умеет:\n"
        "• отвечать на вопросы\n"
        "• помогать с программированием\n"
        "• объяснять сложные темы\n"
        "• переводить тексты\n"
        "• анализировать материалы\n"
        "• поддерживать русский, узбекский и английский языки"
    )


@router.message(Command("new"))
async def cmd_new(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    await ensure_user(user.id, user.username, user.first_name, user.last_name)
    current_user = await get_user(user.id)
    count = (current_user["total_dialogs"] if current_user else 0) + 1
    dialog_id = await create_dialog(user.id, title=f"Новый диалог #{count}")
    await set_active_dialog(user.id, dialog_id)
    await message.answer("✅ Создан новый диалог. Можно начинать беседу.")


@router.message(Command("clear"))
async def cmd_clear(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    await ensure_user(user.id, user.username, user.first_name, user.last_name)
    active = await get_active_dialog(user.id)
    if not active:
        await message.answer("❌ Нет активного диалога для очистки.")
        return
    await clear_dialog_context(active["id"])
    await message.answer("🧹 Контекст текущего диалога очищен.")


@router.message(Command("history"))
async def cmd_history(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    await ensure_user(user.id, user.username, user.first_name, user.last_name)
    dialogs = await get_user_history(user.id, limit=10)
    if not dialogs:
        await message.answer("📚 История пуста. Создайте первый диалог.")
        return
    await message.answer("<b>📚 История диалогов</b>", reply_markup=history_keyboard(dialogs))


@router.message(Command("model"))
async def cmd_model(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    await ensure_user(user.id, user.username, user.first_name, user.last_name)
    try:
        models = await get_available_models()
    except ModelDiscoveryError:
        await message.answer("⚠️ Не удалось загрузить список моделей Groq. Проверьте GROQ_API_KEY и подключение к интернету.")
        return
    if not models:
        await message.answer("⚠️ Список моделей пуст. Проверьте GROQ_API_KEY в файле .env.")
        return
    await message.answer("<b>🧠 Выберите AI-модель</b>", reply_markup=model_keyboard(models))


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    await ensure_user(user.id, user.username, user.first_name, user.last_name)
    await message.answer("<b>⚙️ Настройки LumiAI</b>", reply_markup=settings_keyboard())


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    await ensure_user(user.id, user.username, user.first_name, user.last_name)
    await message.answer(await get_user_profile_text(user.id))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message) -> None:
    await message.answer("❌ Текущее действие отменено.")


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    if user.id not in settings.admin_ids:
        await message.answer("⛔ Доступ запрещён.")
        return
    stats = await get_admin_stats()
    await message.answer(
        "<b>🛡️ Admin Panel</b>\n\n"
        f"Users: {stats['users']}\n"
        f"Dialogs: {stats['dialogs']}\n"
        f"Messages: {stats['messages']}"
    )


@router.callback_query(F.data == "new_dialog")
async def callback_new_dialog(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    await ensure_user(user_id, callback.from_user.username, callback.from_user.first_name, callback.from_user.last_name)
    current_user = await get_user(user_id)
    count = (current_user["total_dialogs"] if current_user else 0) + 1
    dialog_id = await create_dialog(user_id, title=f"Диалог #{count}")
    await set_active_dialog(user_id, dialog_id)
    await callback.answer("✅ Новый диалог создан")
    await callback.message.edit_text("✅ Новый диалог создан. Можно начинать.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "back_main")
async def callback_back_main(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "<b>🤖 LumiAI</b>\n\nПривет! Я LumiAI — твой интеллектуальный помощник.\n\nЧем могу помочь?",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "my_ai")
async def callback_my_ai(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text("<b>🧠 LumiAI</b>\n\nЯ — ваш AI-ассистент. Я могу общаться на русском, узбекском и английском, помогать с кодом, анализом, математикой и текстами.")


@router.callback_query(F.data == "settings")
async def callback_settings(callback: CallbackQuery) -> None:
    await callback.message.edit_text("<b>⚙️ Настройки LumiAI</b>", reply_markup=settings_keyboard())


@router.callback_query(F.data == "settings_model")
async def callback_settings_model(callback: CallbackQuery) -> None:
    try:
        models = await get_available_models()
    except ModelDiscoveryError:
        await callback.answer("Не удалось загрузить модели Groq", show_alert=True)
        return
    if not models:
        await callback.answer("Список моделей пуст. Проверьте GROQ_API_KEY.", show_alert=True)
        return
    await callback.message.edit_text("<b>🧠 Выберите AI-модель</b>", reply_markup=model_keyboard(models))


@router.callback_query(F.data == "settings_language")
async def callback_settings_language(callback: CallbackQuery) -> None:
    await callback.message.edit_text("<b>🌐 Выберите язык интерфейса</b>", reply_markup=language_keyboard())


@router.callback_query(F.data == "settings_persona")
async def callback_settings_persona(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "<b>🧾 Личность AI</b>\n\nТекущая личность: дружелюбная, понятная и практичная.\n\n"
        "Чтобы изменить личность, напишите её описание в чате или используйте команду /settings.",
        reply_markup=settings_keyboard(),
    )


@router.callback_query(F.data == "toggle_memory")
async def callback_toggle_memory(callback: CallbackQuery) -> None:
    user = await get_user(callback.from_user.id)
    enabled = not (user["memory_enabled"] if user else False)
    await set_user_field(callback.from_user.id, "memory_enabled", int(enabled))
    await callback.answer(f"Память {'включена' if enabled else 'выключена'}")
    await callback.message.edit_text("<b>⚙️ Настройки LumiAI</b>", reply_markup=settings_keyboard())


@router.callback_query(F.data == "toggle_notifications")
async def callback_toggle_notifications(callback: CallbackQuery) -> None:
    user = await get_user(callback.from_user.id)
    enabled = not (user["notifications_enabled"] if user else False)
    await set_user_field(callback.from_user.id, "notifications_enabled", int(enabled))
    await callback.answer(f"Уведомления {'включены' if enabled else 'выключены'}")
    await callback.message.edit_text("<b>⚙️ Настройки LumiAI</b>", reply_markup=settings_keyboard())


@router.callback_query(F.data == "clear_history")
async def callback_clear_history(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    dialogs = await get_user_dialogs(user_id)
    if not dialogs:
        await callback.answer("История пуста")
        return
    for dialog in dialogs:
        await delete_dialog(dialog["id"], user_id)
    await callback.answer("🗑️ История удалена")
    await callback.message.edit_text("<b>⚙️ Настройки LumiAI</b>", reply_markup=settings_keyboard())


@router.callback_query(F.data.startswith("set_model:"))
async def callback_set_model(callback: CallbackQuery) -> None:
    model = callback.data.split(":", 1)[1]
    try:
        models = await get_available_models()
    except ModelDiscoveryError:
        await callback.answer("Не удалось проверить модель Groq", show_alert=True)
        return
    if model not in models:
        await callback.answer("Эта модель больше недоступна. Откройте /model.", show_alert=True)
        return
    await set_user_field(callback.from_user.id, "selected_model", model)
    await callback.answer(f"Модель выбрана: {model}")
    await callback.message.edit_text("<b>🧠 Выберите AI-модель</b>", reply_markup=model_keyboard(models))


@router.callback_query(F.data.startswith("lang:"))
async def callback_set_language(callback: CallbackQuery) -> None:
    lang = callback.data.split(":", 1)[1]
    await set_user_field(callback.from_user.id, "language", lang)
    await callback.answer(f"Язык интерфейса: {lang}")
    await callback.message.edit_text("<b>🌐 Выберите язык интерфейса</b>", reply_markup=language_keyboard())


@router.callback_query(F.data == "profile")
async def callback_profile(callback: CallbackQuery) -> None:
    await callback.message.edit_text(await get_user_profile_text(callback.from_user.id))


@router.callback_query(F.data == "history")
async def callback_history(callback: CallbackQuery) -> None:
    dialogs = await get_user_history(callback.from_user.id, limit=10)
    if not dialogs:
        await callback.message.edit_text("📚 История пуста.")
        return
    await callback.message.edit_text("<b>📚 История диалогов</b>", reply_markup=history_keyboard(dialogs))


@router.callback_query(F.data.startswith("select_dialog:"))
async def callback_select_dialog(callback: CallbackQuery) -> None:
    dialog_id = int(callback.data.split(":", 1)[1])
    await set_active_dialog(callback.from_user.id, dialog_id)
    await callback.answer("Диалог выбран")
    await callback.message.edit_text("✅ Диалог активирован.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data.startswith("delete_dialog:"))
async def callback_delete_dialog(callback: CallbackQuery) -> None:
    dialog_id = int(callback.data.split(":", 1)[1])
    await delete_dialog(dialog_id, callback.from_user.id)
    await callback.answer("🗑️ Диалог удалён")
    dialogs = await get_user_history(callback.from_user.id, limit=10)
    if dialogs:
        await callback.message.edit_text("<b>📚 История диалогов</b>", reply_markup=history_keyboard(dialogs))
    else:
        await callback.message.edit_text("📚 История пуста.")


@router.message()
async def handle_user_message(message: Message) -> None:
    user = message.from_user
    if user is None or not message.text:
        return
    if message.text.startswith("/"):
        return
    await ensure_user(user.id, user.username, user.first_name, user.last_name)
    profile = await get_user(user.id)
    dialog_id = await get_or_create_active_dialog(user.id, profile["selected_model"])
    memory_enabled = bool(profile["memory_enabled"])
    history = []
    if memory_enabled:
        history = await get_dialog_messages(dialog_id)
    user_language = detect_language(message.text)
    selected_model = profile["selected_model"] or settings.default_model
    await save_message(dialog_id, "user", message.text, selected_model)
    response = await chat_with_groq(history, message.text, selected_model, user_language, profile["persona"])
    for part in split_message(response):
        await message.answer(f"<b>LumiAI</b>: {html.escape(part)}", parse_mode="HTML")
    await save_message(dialog_id, "assistant", response, selected_model)
    await set_user_field(user.id, "selected_model", selected_model)
