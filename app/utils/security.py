import os
from cryptography.fernet import Fernet

def get_cipher():
    key = os.getenv('ENCRYPTION_KEY')
    return Fernet(key.encode()) # type: ignore

def encrypt_file(file_bytes):
    cipher = get_cipher()
    return cipher.encrypt(file_bytes)

def decrypt_file(encrypted_bytes):
    cipher = get_cipher()
    return cipher.decrypt(encrypted_bytes)