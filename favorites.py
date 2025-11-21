import json
import os
from datetime import datetime
from typing import List, Dict, Any

FAVORITES_FILE = "favorites.json"


def _ensure_file_exists() -> None:
    if not os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_favorites() -> List[Dict[str, Any]]:
    _ensure_file_exists()
    with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if not isinstance(data, list):
                # если файл повреждён или не тот формат — пересоздаём
                return []
            return data
        except json.JSONDecodeError:
            return []


def save_favorites(data: List[Dict[str, Any]]) -> None:
    with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_favorites() -> List[Dict[str, Any]]:
    return load_favorites()


def add_to_favorites(user_data: Dict[str, Any]) -> bool:
    if "id" not in user_data:
        raise ValueError("Ошибка, нету 'id'")

    favorites = load_favorites()
    if any(u.get("id") == user_data["id"] for u in favorites):
        return False

    entry = user_data.copy()
    # добавляем служебное поле с временем добавления
    entry["_added_at"] = datetime.now().isoformat() + "Z"

    favorites.append(entry)
    save_favorites(favorites)
    return True