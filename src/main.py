from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from base64 import b64decode
import base64
import datetime
import pyotp

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

app = FastAPI()

KEYS_DIR = Path("keys")
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

class DecryptSeedRequest(BaseModel):
    encrypted_seed: str

class Generate2FAResponse(BaseModel):
    code: str
    seconds_remaining: int

class Verify2FARequest(BaseModel):
    code: str

class Verify2FAResponse(BaseModel):
    valid: bool

def load_private_key():
    with open(KEYS_DIR / "student_private.pem", "rb") as f:
        key_data = f.read()
    return serialization.load_pem_private_key(key_data, password=None)

@app.post("/decrypt-seed")
def decrypt_seed(payload: DecryptSeedRequest):
    try:
        encrypted_bytes = b64decode(payload.encrypted_seed)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 for encrypted_seed")

    try:
        private_key = load_private_key()
        decrypted = private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except Exception:
        raise HTTPException(status_code=400, detail="RSA decryption failed")

    seed_hex = decrypted.decode("utf-8").strip()
    (DATA_DIR / "seed.txt").write_text(seed_hex, encoding="utf-8")
    return {"status": "ok", "seed_length": len(seed_hex)}

def load_seed_hex() -> str:
    seed_path = DATA_DIR / "seed.txt"
    if not seed_path.exists():
        raise HTTPException(status_code=500, detail="seed.txt not found; call /decrypt-seed first")
    seed_hex = seed_path.read_text(encoding="utf-8").strip()
    if len(seed_hex) != 64:
        raise HTTPException(status_code=500, detail="Invalid seed length in seed.txt")
    return seed_hex

def hex_to_base32(hex_str: str) -> str:
    key_bytes = bytes.fromhex(hex_str)
    return base64.b32encode(key_bytes).decode("utf-8")

@app.get("/generate-2fa", response_model=Generate2FAResponse)
def generate_2fa():
    seed_hex = load_seed_hex()
    secret_base32 = hex_to_base32(seed_hex)

    totp = pyotp.TOTP(secret_base32, digits=6, interval=30)

    now = datetime.datetime.now(datetime.timezone.utc)
    code = totp.now()

    seconds_used = int(now.timestamp()) % totp.interval
    seconds_remaining = totp.interval - seconds_used

    return Generate2FAResponse(code=code, seconds_remaining=seconds_remaining)

@app.post("/verify-2fa", response_model=Verify2FAResponse)
def verify_2fa(payload: Verify2FARequest):
    seed_hex = load_seed_hex()
    secret_base32 = hex_to_base32(seed_hex)

    totp = pyotp.TOTP(secret_base32, digits=6, interval=30)

    # valid_window=1 -> accepts previous, current, next 30s steps
    is_valid = totp.verify(payload.code, valid_window=1)
    return Verify2FAResponse(valid=is_valid)
