from ..extensions import db
from ..models import AuditLog   

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
        db.session.commit() 
    except Exception as e:
        print(f"Gagal mencatat log: {e}")
        db.session.rollback()