

import Crypto.Cipher.AES as AES
from Crypto.PublicKey import RSA
from Crypto import Random
from Crypto.Cipher import PKCS1_v1_5


def get_random_bytes(size=16):
    return Random.get_random_bytes(size)


def make_aes(aes_key, aes_iv, segment_size=8):
    cipher = AES.new(aes_key, AES.MODE_CFB, aes_iv, segment_size=8)
    return cipher


def gen_rsa_key(size=1024):
    return RSA.generate(1024)


def export_pubkey(key):
    return key.publickey().exportKey(format="DER")


def load_pubkey(s):
    return RSA.importKey(s)


def encrypt(message, pubkey):
    cipher = PKCS1_v1_5.new(pubkey)
    return cipher.encrypt(message)


def decrypt(message, privkey):
    cipher = PKCS1_v1_5.new(privkey)
    return cipher.decrypt(message, None)
