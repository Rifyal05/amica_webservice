# app/services/user_action_service.py
from ..database import db
from ..models import BlockedUser, User
from typing import List
import uuid

class UserActionService:
    
    def block_user(self, blocker_id: uuid.UUID, target_id: uuid.UUID) -> bool:
        if blocker_id == target_id:
            return False
        
        existing_block = BlockedUser.query.filter_by(
            blocker_id=blocker_id, blocked_id=target_id
        ).first()
        
        if existing_block:
            return True
            
        new_block = BlockedUser(blocker_id=blocker_id, blocked_id=target_id) # type: ignore
        db.session.add(new_block)
        db.session.commit()
        return True

    def unblock_user(self, blocker_id: uuid.UUID, target_id: uuid.UUID) -> bool:
        block = BlockedUser.query.filter_by(
            blocker_id=blocker_id, blocked_id=target_id
        ).first()
        
        if block:
            db.session.delete(block)
            db.session.commit()
            return True
        return False

    def get_blocked_users(self, user_id: uuid.UUID) -> List[User]:
        blocked_relations = BlockedUser.query.filter_by(blocker_id=user_id).all()
        
        blocked_user_ids = [relation.blocked_id for relation in blocked_relations]
        
        # Mengambil objek User berdasarkan daftar UUID yang diblokir
        # Asumsi User model memiliki .in_() method
        blocked_users_list = User.query.filter(User.id.in_(blocked_user_ids)).all()
                
        return blocked_users_list