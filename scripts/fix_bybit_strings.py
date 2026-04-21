#!/usr/bin/env python3
"""Replace remaining BingX references with Bybit in telegram_ui.py"""

path = "/data/.openclaw/workspace/clawmimoto-bot/clawforge/telegram_ui.py"

with open(path, "r") as f:
    content = f.read()

replacements = [
    # Messages
    ('"Fetching BingX hot pairs', '"Fetching Bybit hot pairs'),
    ('"I\'ll verify on BingX."', '"I\'ll verify on Bybit."'),
    ('"BingX URL detected', '"Bybit URL detected'),
    ('"Handle BingX URL', '"Handle Bybit URL'),  # comment
    ('is not listed on BingX', 'is not listed on Bybit'),
    ('Pair not on BingX', 'Pair not on Bybit'),
    ('Extract pair from BingX perpetual', 'Extract pair from Bybit perpetual'),
    # Sources dict
    ('"BingX": False', '"Bybit": False'),
    ('sources["BingX"]', 'sources["Bybit"]'),
    # Comments
    ('# 1. Try BingX', '# 1. Try Bybit'),
    ('# BingX', '# Bybit'),
    # Function call name already replaced but ensure no leftover
    ('validate_pair_on_bingx(', 'validate_pair_on_bybit('),
]

for old, new in replacements:
    content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print("✅ Remaining BingX → Bybit string replacements done")
