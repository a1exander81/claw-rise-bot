# grid_layer/process_manager.py
import subprocess
import sys
import os

active_grid_bots = {}

def start_grid_bot(symbol: str, config_path: str) -> str:
    if symbol in active_grid_bots and active_grid_bots[symbol].poll() is None:
        return f"Grid bot for {symbol} already running."
    passivbot_dir = os.environ.get("PASSIVBOT_DIR", "./passivbot")
    cmd = [sys.executable, f"{passivbot_dir}/src/main.py", config_path]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=passivbot_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        active_grid_bots[symbol] = proc
        return f"✅ Grid bot {symbol} started (PID {proc.pid})"
    except Exception as e:
        return f"❌ Failed to start {symbol}: {str(e)}"

def stop_grid_bot(symbol: str) -> str:
    proc = active_grid_bots.pop(symbol, None)
    if proc is None:
        return f"No active grid bot for {symbol}."
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
    return f"🛑 Grid bot {symbol} stopped."