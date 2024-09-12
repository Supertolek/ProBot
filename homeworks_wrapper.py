import hashlib
import json


def store_homeworks_hash(user_id: int, homeworks: list[str]):
    homeworks_hash = [
        hashlib.sha256(str(homework).encode()).hexdigest()
        for homework in homeworks
    ]
    user_id_hash = hashlib.sha256(str(user_id).encode()).hexdigest()
    homeworks_dictionary = json.load(open("homeworks.json"))
    homeworks_dictionary[user_id_hash] = homeworks_hash
    json.dump(homeworks_dictionary, open("homeworks.json", "w"))


def get_stored_homeworks_hash(user_id: int) -> list[str]:
    user_id_hash = hashlib.sha256(str(user_id).encode()).hexdigest()
    homeworks_dictionary = json.load(open("homeworks.json"))
    if user_id_hash in homeworks_dictionary:
        return homeworks_dictionary[user_id_hash]
    else:
        return []


def compare_stored_homeworks(user_id: int, homeworks: list[str]) -> bool:
    homeworks_hash = [
        hashlib.sha256(str(homework).encode()).hexdigest()
        for homework in homeworks
    ]
    stored_homeworks_hash = json.load(open("homeworks.json"))
    return homeworks_hash == stored_homeworks_hash
