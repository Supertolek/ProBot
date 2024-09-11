import os
import json


def _encrypt_str(text: str, key: str) -> str:
    """Encrypts the given ID using my algorithim."""
    encrypted_text = ""
    for letter_index in range(len(text)):
        encrypted_text += chr(
                ord(text[letter_index]) + ord(key[letter_index % len(key)]))
    return encrypted_text


def _decrpyt_str(text: str, key: str) -> str:
    """Decrypts the given ID using my algorithim."""
    decrypted_text = ""
    for letter_index in range(len(text)):
        decrypted_text += chr(
                ord(text[letter_index]) - ord(key[letter_index % len(key)]))
    return decrypted_text


def save_user(discord_user_id: int,
                            url: str,
                            username: str,
                            token: str,
                            uuid: str,
                            replace: bool = True) -> str | None:
    """Saves the user informations to a file. Returns None if the user is already registered."""
    users_dictionary = json.load(open("users.json"))

    encrypted_discord_username = _encrypt_str(str(discord_user_id),
                                                                                        os.environ["ENCRYPTING_KEY"])
    encrypted_url = _encrypt_str(url, os.environ["ENCRYPTING_KEY"])
    encrypted_username = _encrypt_str(username, os.environ["ENCRYPTING_KEY"])
    encrypted_token = _encrypt_str(token, os.environ["ENCRYPTING_KEY"])
    encrypted_uuid = _encrypt_str(uuid, os.environ["ENCRYPTING_KEY"])

    if encrypted_discord_username in users_dictionary and not replace:
        return None
    users_dictionary[encrypted_discord_username] = [
            encrypted_url, encrypted_username, encrypted_token, encrypted_uuid
    ]
    json.dump(users_dictionary, open("users.json", "w"))
    return ""


def get_user(discord_user_id: int) -> dict | None:
    """Returns the informations of the user if the user is registered, returns None if he doesn't."""
    users_dictionary = json.load(open("users.json"))

    encrypted_discord_username = _encrypt_str(str(discord_user_id),
                                                                                        os.environ["ENCRYPTING_KEY"])

    if encrypted_discord_username in users_dictionary:
        url = _decrpyt_str(users_dictionary[encrypted_discord_username][0],
                                             os.environ["ENCRYPTING_KEY"])
        username = _decrpyt_str(users_dictionary[encrypted_discord_username][1],
                                                        os.environ["ENCRYPTING_KEY"])
        token = _decrpyt_str(users_dictionary[encrypted_discord_username][2],
                                                 os.environ["ENCRYPTING_KEY"])
        uuid = _decrpyt_str(users_dictionary[encrypted_discord_username][3],
                                                os.environ["ENCRYPTING_KEY"])
        return {"url": url, "username": username, "token": token, "uuid": uuid}
    else:
        return None

def get_all_users() -> list[list]:
    """Returns the informations of all users ,returns None if no user is registered."""
    users_dictionary = json.load(open("users.json"))
    all_users = list()
    for user, value in users_dictionary.items():
        user = _decrpyt_str(user, os.environ["ENCRYPTING_KEY"])
        url = _decrpyt_str(value[0], os.environ["ENCRYPTING_KEY"])
        username = _decrpyt_str(value[1], os.environ["ENCRYPTING_KEY"])
        token = _decrpyt_str(value[2], os.environ["ENCRYPTING_KEY"])
        uuid = _decrpyt_str(value[3], os.environ["ENCRYPTING_KEY"])
        all_users.append([user, url, username, token, uuid])

    return all_users
    
def allready_registered(discord_user_id: int) -> bool:
    users_dictionary = json.load(open("users.json"))

    encrypted_discord_username = _encrypt_str(str(discord_user_id), os.environ["ENCRYPTING_KEY"])
    if encrypted_discord_username in users_dictionary:
        return True
    else: 
        return False
    
