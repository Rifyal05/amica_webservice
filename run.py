from gevent import monkey
monkey.patch_all()

import sys
import os
from app import create_app as pembuat_aplikasi
from app.extensions import socketio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

amica_app_obj = pembuat_aplikasi()

if __name__ == '__main__':    
    socketio.run(
        amica_app_obj, 
        host='0.0.0.0', 
        port=5000, 
        debug=False,
        use_reloader=False,
        # log_output=True
    )

# NOTES(pengingat) = gunicorn -k gevent -w 1 run:amica_app_obj
# Nanti di server asli, pastikan perintah itu dimasukkan ke dalam System Service (systemd).
# Jadi nanti, servernya akan berjalan otomatis di background 24 jam nonstop, meski servernya habis restart.