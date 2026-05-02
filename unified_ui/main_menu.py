# unified_ui/main_menu.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔥 CLAW SNIPER (Directional)", callback_data="claw_info")],
        [
            InlineKeyboardButton("🌅 P-Ldn", callback_data="claw_session:pre_london"),
            InlineKeyboardButton("🇬🇧 Ldn", callback_data="claw_session:london"),
            InlineKeyboardButton("🇺🇸 NY", callback_data="claw_session:ny"),
        ],
        [InlineKeyboardButton("⏹️ STOP CLAW", callback_data="claw_stop")],

        [InlineKeyboardButton("━━━━━━━━━━━━━━", callback_data="ignore")],

        [InlineKeyboardButton("🕸️ GRID ENGINE (Contrarian)", callback_data="grid_info")],
        [
            InlineKeyboardButton("🌅 P-Ldn", callback_data="grid_session:pre_london"),
            InlineKeyboardButton("🇬🇧 Ldn", callback_data="grid_session:london"),
            InlineKeyboardButton("🇺🇸 NY", callback_data="grid_session:ny"),
        ],
        [InlineKeyboardButton("⏹️ STOP GRID", callback_data="grid_stop")],

        [InlineKeyboardButton("📊 ALL POSITIONS", callback_data="all_positions")],
        [InlineKeyboardButton("💰 PnL LEDGER", callback_data="pnl")],
        [InlineKeyboardButton("⚙️ GLOBAL SETTINGS", callback_data="global_settings")],
    ]
    return InlineKeyboardMarkup(keyboard)