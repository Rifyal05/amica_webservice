from flask_mail import Message
from ..extensions import mail
from flask import current_app
import threading

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
            print("Email terkirim!")
        except Exception as e:
            print(f"Gagal kirim email: {e}")

def send_otp_email(to_email, user_name, otp_code):
    subject = "Reset Password Amica"
    body = f"""
    Halo {user_name},
    
    Kami menerima permintaan untuk mereset password akun Amica kamu.
    Gunakan kode OTP berikut:
    
    {otp_code}
    
    Kode ini berlaku selama 15 menit.
    Jika ini bukan kamu, abaikan email ini.
    
    Salam,
    Lensa Team
    """
    
    msg = Message(subject, recipients=[to_email], body=body)

    app = current_app._get_current_object() # type: ignore
    threading.Thread(target=send_async_email, args=(app, msg)).start()
    
    return True