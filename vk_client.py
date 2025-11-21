from typing import List, Dict, Any
from config import SEARCH_PARAMS


class VKClient:
    def __init__(self, vk):
        self.vk = vk

    def search_users(
        self,
        sex: int | None = None,
        city_id: int | None = None,
        age_from: int | None = None,
        age_to: int | None = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Поиск пользователей по параметрам:
        sex: 1 — женский, 2 — мужской, 0 или None — любой.
        city_id: id города пользователя.
        age_from, age_to: границы возраста.
        """
        params = SEARCH_PARAMS.copy()
        params.update(
            {
                "offset": offset,
                "has_photo": 1,
                "fields": "photo_id,city,domain,bdate",
                "status": 1,
            }
        )

        if sex in (0, 1, 2):
            params["sex"] = sex
        if city_id:
            params["city"] = city_id
        if age_from:
            params["age_from"] = age_from
        if age_to:
            params["age_to"] = age_to

        try:
            resp = self.vk.users.search(**params)
            return resp.get("items", [])
        except Exception as exc:
            print(f"Ошибка при поиске пользователей: {exc}")
            return []

    def get_top_photos(self, user_id: int, album: str = "profile") -> list:
        """
        Получить топ-3 фото пользователя по лайкам.
        Если из альбома profile не удаётся — пробуем wall.
        """
        try:
            resp = self.vk.photos.get(
                owner_id=user_id,
                album_id=album,
                extended=1,
            )
            items = resp.get("items", [])
            if not items and album == "profile":
                # пробуем фотографии со стены
                resp = self.vk.photos.get(
                    owner_id=user_id,
                    album_id="wall",
                    extended=1,
                )
                items = resp.get("items", [])

            items.sort(
                key=lambda x: x.get("likes", {}).get("count", 0),
                reverse=True,
            )
            return items[:3]
        except Exception as exc:
            print(f"Ошибка при получении фото пользователя {user_id}: {exc}")
            return []