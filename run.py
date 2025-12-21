from gevent import monkey
monkey.patch_all()

import sys
import os
from app import create_app as pembuat_aplikasi
from app.socket_instance import socketio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

amica_app_obj = pembuat_aplikasi()

if __name__ == '__main__':
    print("Amica Socket Server (Gevent) is starting on http://0.0.0.0:5000")
    
    socketio.run(
        amica_app_obj, 
        host='0.0.0.0', 
        port=5000, 
        debug=True,
        use_reloader=False
    )

# NOTES(pengingat) = gunicorn -k gevent -w 1 run:amica_app_obj
# Nanti di server asli, pastikan perintah itu dimasukkan ke dalam System Service (systemd).
# Jadi nanti, servernya akan berjalan otomatis di background 24 jam nonstop, meski servernya habis restart.