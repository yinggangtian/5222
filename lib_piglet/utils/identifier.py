import base64
import hashlib
from random import random
import time
from yaml import dump


def encode(num: str):
    hasher = hashlib.sha1(num.encode())
    return str(base64.urlsafe_b64encode(hasher.digest()))[2:11]


def identifier(obj: object):
    return encode(f"{id(obj)}")

def get_random_id():
    return encode(f"{random()}")

