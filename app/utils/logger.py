from ..database import db       # Pastikan import db
from ..models import AuditLog   # Pastikan import model AuditLog

def record_log(actor_id, target_id, target_type, action, old_val, new_val, description):
    try:
        log = AuditLog(
            actor_id=actor_id, # type: ignore
            target_id=target_id,# type: ignore
            target_type=target_type,# type: ignore
            action=action,# type: ignore
            old_value=old_val,# type: ignore
            new_value=new_val,# type: ignore
            description=description # type: ignore
        )
        db.session.add(log)
        # Note: Biasanya commit dilakukan di route utama, 
        # tapi kalau mau force commit di sini juga boleh:
        db.session.commit() 
    except Exception as e:
        print(f"Gagal mencatat log: {e}")
        db.session.rollback()