import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    token: str
    admin_id: int
    client_id: int
    db_path: str


def load_settings() -> Settings:
    path = Path(__file__).with_name("config.json")
    if not path.exists():
        raise FileNotFoundError("config.json not found рядом с config.py")
    raw = json.loads(path.read_text(encoding="utf-8"))
    token = str(raw.get("token", "")).strip()
    admin_id = int(raw.get("admin_id", 0))
    client_id = int(raw.get("client_id", 0))
    db_path = str(raw.get("db_path", "db.sqlite3")).strip() or "db.sqlite3"
    if not token or token == "PUT_TOKEN_HERE":
        raise ValueError("В config.json нужно указать token")
    if admin_id <= 0 or client_id <= 0 or admin_id == client_id:
        raise ValueError("В config.json нужно указать разные admin_id и client_id")
    return Settings(token=token, admin_id=admin_id, client_id=client_id, db_path=db_path)


settings = load_settings()
TOKEN = settings.token
ADMIN_ID = settings.admin_id
CLIENT_ID = settings.client_id
DB_PATH = settings.db_path
