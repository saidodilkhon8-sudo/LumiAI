from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Новый диалог", callback_data="new_dialog"),
            InlineKeyboardButton(text="🧠 Мой AI", callback_data="my_ai"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
            InlineKeyboardButton(text="📚 История", callback_data="history"),
        ],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
    ])
    return keyboard


def settings_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Модель", callback_data="settings_model")],
        [InlineKeyboardButton(text="🌐 Язык", callback_data="settings_language")],
        [InlineKeyboardButton(text="🧾 Личность AI", callback_data="settings_persona")],
        [InlineKeyboardButton(text="🧠 Память: Вкл/Выкл", callback_data="toggle_memory")],
        [InlineKeyboardButton(text="🗑️ Очистить историю", callback_data="clear_history")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="toggle_notifications")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")],
    ])
    return keyboard


def model_keyboard(models: list[str]) -> InlineKeyboardMarkup:
    buttons = []
    for model in models:
        buttons.append([InlineKeyboardButton(text=model, callback_data=f"set_model:{model}")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Русский", callback_data="lang:ru")],
        [InlineKeyboardButton(text="O'zbekcha", callback_data="lang:uz")],
        [InlineKeyboardButton(text="English", callback_data="lang:en")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")],
    ])


def history_keyboard(dialogs: list[dict]) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for dialog in dialogs:
        title = (dialog.get("title") or "Диалог")[:20]
        buttons.append([
            InlineKeyboardButton(text=f"{title}", callback_data=f"select_dialog:{dialog['id']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"delete_dialog:{dialog['id']}"),
        ])
    buttons.append([InlineKeyboardButton(text="💬 Новый диалог", callback_data="new_dialog")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
