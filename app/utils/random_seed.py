import hashlib
import random


def get_seeded_random(seed_str: str) -> random.Random:
    seed_int = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed_int)


def make_daily_seed(work_date: str) -> str:
    return f"{work_date}:zt-controller:v1"
