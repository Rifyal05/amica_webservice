import os
import uuid
from datetime import datetime, timezone
from flask import current_app
from cryptography.fernet import Fernet
from ..models import db, ProfessionalProfile, User

class ProfessionalService:
    def __init__(self):
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            raise ValueError("ENCRYPTION_KEY tidak ditemukan di .env")
        self.cipher = Fernet(key.encode())

    def _encrypt(self, data):
        return self.cipher.encrypt(data)

    def _decrypt(self, data):
        return self.cipher.decrypt(data)

    def submit_application(self, user_id, form_data, files):
        upload_folder = os.path.join(current_app.root_path, 'static', 'verifications')
        os.makedirs(upload_folder, exist_ok=True)

        paths = {}
        for doc_type in ['str_image', 'ktp_image', 'selfie_image']:
            file = files.get(doc_type)
            if not file:
                return False, f"File {doc_type} diperlukan"
            
            file_bytes = file.read()
            encrypted_data = self._encrypt(file_bytes)
            
            filename = f"{doc_type}_{user_id}_{uuid.uuid4().hex[:8]}.enc"
            with open(os.path.join(upload_folder, filename), 'wb') as f:
                f.write(encrypted_data)
            paths[doc_type] = filename

        new_pro = ProfessionalProfile(
            user_id=user_id, # type: ignore
            full_name_with_title=form_data.get('full_name'), # type: ignore
            str_number=form_data.get('str_number'),# type: ignore
            province=form_data.get('province'),# type: ignore
            practice_address=form_data.get('address'),# type: ignore
            practice_schedule=form_data.get('schedule'),# type: ignore
            str_image_path=paths['str_image'],# type: ignore
            ktp_image_path=paths['ktp_image'],# type: ignore
            selfie_image_path=paths['selfie_image']# type: ignore
        )
        db.session.add(new_pro)
        db.session.commit()
        return True, "Permohonan verifikasi berhasil dikirim"

    def approve_application(self, pro_id):
        pro = ProfessionalProfile.query.get(pro_id)
        if not pro: return False, "Data tidak ditemukan"

        folder = os.path.join(current_app.root_path, 'static', 'verifications')
        files_to_delete = [pro.ktp_image_path, pro.selfie_image_path]
        
        for filename in files_to_delete:
            if filename:
                path = os.path.join(folder, filename)
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception as e:
                    print(f"Gagal hapus file: {e}")

        pro.status = 'approved'
        pro.verified_at = datetime.now(timezone.utc)
        pro.ktp_image_path = None
        pro.selfie_image_path = None
        
        user = User.query.get(pro.user_id)
        
        user.is_verified = True # type: ignore
        
        db.session.commit()
        return True, "Disetujui"

    def reject_application(self, pro_id):
        pro = ProfessionalProfile.query.get(pro_id)
        if not pro: return False, "Data tidak ditemukan"

        upload_folder = os.path.join(current_app.root_path, 'static', 'verifications')
        
        for attr in ['str_image_path', 'ktp_image_path', 'selfie_image_path']:
            filename = getattr(pro, attr)
            if filename:
                path = os.path.join(upload_folder, filename)
                if os.path.exists(path):
                    os.remove(path)

        db.session.delete(pro)
        db.session.commit()
        return True, "Permohonan ditolak dan semua dokumen telah dihapus"

    def revoke_verification(self, pro_id):
        pro = ProfessionalProfile.query.get(pro_id)
        if not pro: return False, "Data tidak ditemukan"

        upload_folder = os.path.join(current_app.root_path, 'static', 'verifications')

        if pro.str_image_path:
            path = os.path.join(upload_folder, pro.str_image_path)
            if os.path.exists(path):
                os.remove(path)
        
        user = User.query.get(pro.user_id)
        if user:
            user.role = 'user'
            user.is_verified = False
        
        db.session.delete(pro)
        db.session.commit()
        return True, "Status verifikasi dicabut dan arsip dokumen telah dibersihkan"
    
    def update_professional_info(self, user_id, form_data):
        pro = ProfessionalProfile.query.filter_by(user_id=user_id).first()
        
        if not pro:
            return False, "Profil profesional tidak ditemukan."
            
        if pro.status != 'approved':
            return False, "Akun belum terverifikasi sebagai profesional."

        if 'province' in form_data:
            pro.province = form_data.get('province')
        if 'address' in form_data:
            pro.practice_address = form_data.get('address')
        if 'schedule' in form_data:
            pro.practice_schedule = form_data.get('schedule')

        try:
            db.session.commit()
            return True, "Informasi profesional berhasil diperbarui."
        except Exception as e:
            db.session.rollback()
            return False, f"Gagal menyimpan data: {str(e)}"