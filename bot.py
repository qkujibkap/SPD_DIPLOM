# bot.py
import random
from datetime import date

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from config import TOKEN_GROUP, TOKEN_USER, GROUP_ID
from vk_client import VKClient
from favorites import get_favorites, add_to_favorites

# --- Сессии ---
vk_session = vk_api.VkApi(token=TOKEN_GROUP)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID, wait=5)

user_session = vk_api.VkApi(token=TOKEN_USER)
user_vk = user_session.get_api()
client = VKClient(user_vk)

running = True
shown_users: set[int] = set()  # уже показанные пользователи
last_shown_user: dict[int, dict] = {}  # последний показанный пользователь для каждого peer_id
user_filters: dict[int, dict] = {}  # кэш параметров поиска по пользователям


def make_keyboard() -> str:
    """Создаёт клавиатуру для бота."""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("Следующий",
                        color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("В избранное",
                        color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("Показать избранных",
                        color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("Стоп",
                        color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()


def calculate_age(bdate_str: str | None) -> int | None:
    """Вычислить возраст по дате рождения формата 'DD.MM.YYYY'."""
    if not bdate_str:
        return None

    parts = bdate_str.split(".")
    if len(parts) != 3:
        return None

    try:
        day, month, year = map(int, parts)
        born = date(year, month, day)
        today = date.today()
        age = today.year - born.year - (
                (today.month, today.day) < (born.month, born.day)
        )
        return age
    except ValueError:
        return None


def get_user_search_filters(peer_id: int) -> dict:
    """Получить параметры поиска на основе информации о пользователе."""
    if peer_id in user_filters:
        return user_filters[peer_id]

    info = user_vk.users.get(
        user_ids=peer_id,
        fields="bdate,sex,city",
    )[0]

    sex = info.get("sex")  # 1 — женский, 2 — мужской
    if sex in (1, 2):
        # ищаем противоположный пол
        search_sex = 1 if sex == 2 else 2
    else:
        search_sex = 0  # любой

    city = info.get("city")
    city_id = city["id"] if isinstance(city, dict) and "id" in city else None

    age = calculate_age(info.get("bdate"))
    if age is not None:
        age_from = max(age - 2, 18)
        age_to = age + 2
    else:
        age_from = None
        age_to = None

    filters = {
        "sex": search_sex,
        "city_id": city_id,
        "age_from": age_from,
        "age_to": age_to,
    }

    user_filters[peer_id] = filters
    return filters


def send_user_card(peer_id: int, user: dict) -> None:
    """Отправить карточку пользователя с 3 фотографиями."""
    message = (
        f"{user['first_name']} {user['last_name']}\n"
        f"https://vk.com/id{user['id']}"
    )
    photos = client.get_top_photos(user["id"])
    attachments = [
        f"photo{photo['owner_id']}_{photo['id']}" for photo in photos
    ]

    try:
        vk.messages.send(
            peer_id=peer_id,
            random_id=0,
            message=message,
            attachment=",".join(attachments),
            keyboard=make_keyboard(),
        )
    except Exception as exc:
        print(f"Ошибка при отправке сообщения пользователю {peer_id}: {exc}")


def run_bot() -> None:
    """Основной цикл работы бота."""
    global running
    print("Bot started...")
    try:
        while running:
            for event in longpoll.listen():
                if event.type != VkBotEventType.MESSAGE_NEW or not event.from_user:
                    continue

                peer_id = event.message.peer_id
                text = event.message.text.strip().lower()

                try:
                    if text == "начать":
                        vk.messages.send(
                            peer_id=peer_id,
                            random_id=0,
                            message=(
                                "Привет! Я помогу найти интересных людей 😉\n"
                                "Команды:\n"
                                "• Следующий\n"
                                "• В избранное\n"
                                "• Показать избранных\n"
                                "• Стоп"
                            ),
                            keyboard=make_keyboard(),
                        )

                    elif text == "следующий":
                        filters = get_user_search_filters(peer_id)

                        # ищем следующего пользователя
                        while True:
                            offset = random.randint(0, 1000)
                            results = client.search_users(
                                offset=offset,
                                **filters,
                            )

                            if not results:
                                continue

                            candidate = random.choice(results)

                            if candidate["id"] in shown_users:
                                continue

                            shown_users.add(candidate["id"])
                            last_shown_user[peer_id] = candidate
                            send_user_card(peer_id, candidate)
                            break

                    elif text == "в избранное":
                        if peer_id not in last_shown_user:
                            vk.messages.send(
                                peer_id=peer_id,
                                random_id=0,
                                message=(
                                    "Сначала нажмите «Следующий», "
                                    "чтобы выбрать пользователя."
                                ),
                                keyboard=make_keyboard(),
                            )
                            continue

                        user = last_shown_user[peer_id]
                        favorites = get_favorites()

                        if any(fav["id"] == user["id"] for fav in favorites):
                            vk.messages.send(
                                peer_id=peer_id,
                                random_id=0,
                                message=(
                                    f"{user['first_name']} "
                                    "уже в избранном ⭐"
                                ),
                                keyboard=make_keyboard(),
                            )
                            continue

                        # формируем структурированные данные для favorites.json
                        photos = client.get_top_photos(user["id"])
                        photo_ids = [
                            f"photo{p['owner_id']}_{p['id']}" for p in photos
                        ]

                        favorite_entry = {
                            "id": user["id"],
                            "first_name": user.get("first_name", ""),
                            "last_name": user.get("last_name", ""),
                            "profile_url": f"https://vk.com/id{user['id']}",
                            "photos": photo_ids,
                        }

                        added = add_to_favorites(favorite_entry)

                        if added:
                            msg = (
                                f"{user['first_name']} добавлен(а) "
                                "в избранное ⭐"
                            )
                        else:
                            msg = (
                                f"{user['first_name']} уже находится "
                                "в избранном ⭐"
                            )

                        vk.messages.send(
                            peer_id=peer_id,
                            random_id=0,
                            message=msg,
                            keyboard=make_keyboard(),
                        )

                    elif text == "показать избранных":
                        favorites = get_favorites()
                        if not favorites:
                            msg = "Список избранных пуст 🙃"
                        else:
                            lines = []
                            for u in favorites:
                                line = (
                                    f"{u.get('first_name', '')} "
                                    f"{u.get('last_name', '')} — "
                                    f"{u.get('profile_url', f'https://vk.com/id{u.get('id')}')}"
                                )
                                lines.append(line)
                            msg = "⭐ Избранные:\n" + "\n".join(lines)

                        vk.messages.send(
                            peer_id=peer_id,
                            random_id=0,
                            message=msg,
                            keyboard=make_keyboard(),
                        )

                    elif text == "стоп":
                        vk.messages.send(
                            peer_id=peer_id,
                            random_id=0,
                            message="Бот остановлен ✅",
                            keyboard=make_keyboard(),
                        )
                        print("Bot stopped by user command")
                        running = False
                        break

                    else:
                        vk.messages.send(
                            peer_id=peer_id,
                            random_id=0,
                            message=(
                                "Не понял команду 😅\n"
                                "Доступные команды:\n"
                                "• Начать\n"
                                "• Следующий\n"
                                "• В избранное\n"
                                "• Показать избранных\n"
                                "• Стоп"
                            ),
                            keyboard=make_keyboard(),
                        )

                except Exception as exc:
                    # общая защита от падений внутри обработки сообщения
                    print(f"Ошибка при обработке сообщения от {peer_id}: {exc}")
                    try:
                        vk.messages.send(
                            peer_id=peer_id,
                            random_id=0,
                            message="Произошла ошибка, попробуйте ещё раз позже 🙃",
                            keyboard=make_keyboard(),
                        )
                    except Exception:
                        pass

    except KeyboardInterrupt:
        print("Bot stopped manually")


if __name__ == "__main__":
    run_bot()
