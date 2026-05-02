# unified_ui/handlers.py
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config.sessions import TRADING_SESSIONS
from unified_ui.main_menu import main_menu_keyboard

logger = logging.getLogger(__name__)

active_sessions = {
    "claw": None,
    "grid": None,
}

async def claw_session_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":", 1)
    if len(parts) != 2:
        await query.edit_message_text("❌ Malformed callback data.")
        return
    _, session_key = parts
    session = TRADING_SESSIONS.get(session_key)
    if not session:
        await query.edit_message_text("❌ Unknown session.")
        return
    active_sessions["claw"] = session_key
    text = f"🔥 Clawmimoto switched to **{session['emoji']} {session['name']}** session.\n"
    text += f"Volatility level: {session['volatility_level'].upper()}\n"
    text += f"Max trades: {session['claw_settings']['max_trades_per_session']}\n"
    text += f"Risk per trade: {session['claw_settings']['risk_per_trade_pct']}%"
    await query.edit_message_text(text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

async def claw_stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    active_sessions["claw"] = None
    await query.edit_message_text("🛑 Clawmimoto stopped.", reply_markup=main_menu_keyboard())

async def grid_session_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":", 1)
    if len(parts) != 2:
        await query.edit_message_text("❌ Malformed callback data.")
        return
    _, session_key = parts
    session = TRADING_SESSIONS.get(session_key)
    if not session:
        await query.edit_message_text("❌ Unknown session.")
        return
    active_sessions["grid"] = session_key
    text = f"🕸️ Grid Engine switched to **{session['emoji']} {session['name']}** session.\n"
    text += f"Volatility level: {session['volatility_level'].upper()}\n"
    text += f"Grid spacing factor: {session['grid_settings']['grid_spacing_factor']}\n"
    text += f"TP markup: {session['grid_settings']['tp_markup_pct']}%"
    await query.edit_message_text(text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

async def grid_stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    active_sessions["grid"] = None
    await query.edit_message_text("🛑 Grid Engine stopped.", reply_markup=main_menu_keyboard())

async def ignore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()