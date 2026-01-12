from flask_mail import Message
from ..extensions import mail
from flask import current_app
import threading

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            print(f"Gagal kirim email: {e}")

def send_otp_email(to_email, user_name, otp_code, category='password'):

    if category == 'pin':
        subject = "Reset PIN Keamanan Amica"
        action_text = "mereset PIN Keamanan (Security PIN)"
    else:
        subject = "Reset Password Amica"
        action_text = "mereset password akun"

    body = f"""
    Halo {user_name},
    
    Kami menerima permintaan untuk {action_text} Amica kamu.
    Gunakan kode OTP berikut:
    
    {otp_code}
    
    Kode ini berlaku selama 15 menit.
    Jika ini bukan kamu, mohon abaikan email ini dan amankan akunmu.
    
    Salam,
    Lensa Team
    """
    
    msg = Message(subject, recipients=[to_email], body=body)

    app = current_app._get_current_object() # type: ignore
    threading.Thread(target=send_async_email, args=(app, msg)).start()
    
    return True