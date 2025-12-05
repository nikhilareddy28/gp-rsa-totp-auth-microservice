#!/usr/bin/env bash
set -e

SEED_FILE=/data/seed.txt
OUT_FILE=/cron/last_code.txt

if [ ! -f "$SEED_FILE" ]; then
  exit 0
fi

SEED_HEX=$(cat "$SEED_FILE" | tr -d '\r\n')
if [ ${#SEED_HEX} -ne 64 ]; then
  exit 0
fi

python - << 'EOF'
import base64
import datetime
import pyotp
import os

seed_file = "/data/seed.txt"
out_file = "/cron/last_code.txt"

with open(seed_file, "r", encoding="utf-8") as f:
    seed_hex = f.read().strip()

key_bytes = bytes.fromhex(seed_hex)
secret_base32 = base64.b32encode(key_bytes).decode("utf-8")

totp = pyotp.TOTP(secret_base32, digits=6, interval=30)

now = datetime.datetime.now(datetime.timezone.utc)
code = totp.now()

ts = now.strftime("%Y-%m-%d %H:%M:%S")
line = f"{ts} - 2FA Code: {code}\n"

os.makedirs(os.path.dirname(out_file), exist_ok=True)
with open(out_file, "w", encoding="utf-8") as f:
    f.write(line)
EOF
