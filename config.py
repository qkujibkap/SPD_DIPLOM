import os

TOKEN_GROUP = os.getenv("TOKEN_GROUP")
TOKEN_USER = os.getenv("TOKEN_USER")
GROUP_ID = int(os.getenv("GROUP_ID", 0))

SEARCH_PARAMS = {
    "count": 50
}

FAVORITES_FILE = "favorites.json"