import os
import uuid
from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, jsonify, request, current_app
from werkzeug.utils import secure_filename
from sqlalchemy import func
from ..models import db, User, Report, Feedback, Post, Comment, AuditLog
from ..utils.decorators import admin_required
from ..utils.logger import record_log 
from ..routes.auth_routes import bcrypt
from firebase_admin import auth as firebase_auth
from ..services.notif_manager import create_notification
import shutil
from sqlalchemy import func, desc
from ..models import QuarantinedItem

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ANCHOR: LOGIN PAGE
@admin_bp.route('/login')
def login_page():
    return render_template('admin/login.html')

# ANCHOR: DASHBOARD PAGE
@admin_bp.route('/dashboard')
def dashboard_page():
    return render_template('admin/base.html')

# ANCHOR : GET STATS
@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_stats(current_user):
    try:
        time_range = request.args.get('range', '7d')
        
        offset_val = int(request.args.get('tz_offset', -420)) 
        USER_TZ = timezone(timedelta(minutes=-offset_val))
        
        now_local = datetime.now(USER_TZ)
        grouping = 'day'
        
        if time_range == 'today':
            start_date_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            grouping = 'hour'
        elif time_range == '7d':
            start_date_local = (now_local - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == '30d':
            start_date_local = (now_local - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == '1y':
            start_date_local = now_local.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            grouping = 'month'
        elif time_range == '5y':
            start_year = now_local.year - 4
            start_date_local = now_local.replace(year=start_year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            grouping = 'year'
        elif time_range == '10y':
            start_year = now_local.year - 9
            start_date_local = now_local.replace(year=start_year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            grouping = 'year'
        elif time_range == 'all':
            first_user = User.query.order_by(User.created_at.asc()).first()
            if first_user:
                first_date = first_user.created_at.replace(tzinfo=timezone.utc).astimezone(USER_TZ)
                start_date_local = first_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date_local = now_local.replace(year=now_local.year-1, month=1, day=1)
            grouping = 'year'
        else:
            start_date_local = (now_local - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)

        labels = []
        data_users = []
        data_posts = []
        data_reports = []

        current_step_local = start_date_local
        
        if grouping == 'hour':
            end_limit = now_local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        elif grouping == 'day':
            end_limit = now_local + timedelta(days=1)
        elif grouping == 'month':
            end_limit = now_local + timedelta(days=32)
        else: 
            end_limit = now_local + timedelta(days=366)

        while current_step_local < end_limit:
            if grouping == 'hour':
                next_step_local = current_step_local + timedelta(hours=1)
                label = current_step_local.strftime('%H:00')
            elif grouping == 'day':
                next_step_local = current_step_local + timedelta(days=1)
                label = current_step_local.strftime('%d/%m')
            elif grouping == 'month':
                next_month = current_step_local.month + 1 if current_step_local.month < 12 else 1
                next_year = current_step_local.year + 1 if current_step_local.month == 12 else current_step_local.year
                next_step_local = current_step_local.replace(year=next_year, month=next_month, day=1)
                label = current_step_local.strftime('%b %Y')
            elif grouping == 'year':
                next_step_local = current_step_local.replace(year=current_step_local.year + 1)
                label = current_step_local.strftime('%Y')

            if grouping != 'hour' and current_step_local.date() > now_local.date():
                break
            
            labels.append(label)# type: ignore

            query_start_utc = current_step_local.astimezone(timezone.utc)# type: ignore
            query_end_utc = next_step_local.astimezone(timezone.utc)# type: ignore

            u_count = User.query.filter(User.created_at >= query_start_utc, User.created_at < query_end_utc).count()
            p_count = Post.query.filter(Post.created_at >= query_start_utc, Post.created_at < query_end_utc).count()
            r_count = Report.query.filter(Report.created_at >= query_start_utc, Report.created_at < query_end_utc).count()

            data_users.append(u_count)
            data_posts.append(p_count)
            data_reports.append(r_count)

            current_step_local = next_step_local # type: ignore
            if current_step_local.year > now_local.year + 1: break
        
        sentiment_query = db.session.query(Feedback.sentiment, func.count(Feedback.id)).group_by(Feedback.sentiment).all()
        counts = {'positive': 0, 'negative': 0}
        for label, count in sentiment_query:
            if label:
                clean_label = label.lower().strip()
                if clean_label in counts:
                    counts[clean_label] += count
        
        return jsonify({
            'total_users': User.query.count(),
            'pending_reports': Report.query.filter_by(status='pending').count(),
            'total_feedback': Feedback.query.count(),
            'chart_data': {
                'labels': labels,
                'users': data_users,
                'posts': data_posts,
                'reports': data_reports
            },
            'sentiment_data': [counts['positive'], counts['negative']]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

#[ANCHOR]: GET USERS LIST
@admin_bp.route('/users-list', methods=['GET'])
@admin_required
def get_users_list(current_user):
    try:
        users = User.query.order_by(User.created_at.desc()).limit(100).all()
        data = []
        for u in users:
            data.append({
                'id': str(u.id),
                'username': u.username,
                'email': u.email,
                'role': u.role,
                'auth_provider': u.auth_provider,
                'is_suspended': u.is_suspended,
                'avatar_url': u.avatar_url,
                'created_at': u.created_at.strftime('%Y-%m-%d')
            })
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#[ANCHOR]: CHANGE ROLE
@admin_bp.route('/users/change-role', methods=['POST'])
@admin_required
def change_role(current_user):
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_role = data.get('new_role')

        if new_role not in ['admin', 'user']: 
            return jsonify({'message': 'Role tidak valid'}), 400

        target_user = User.query.get(user_id)
        if not target_user: return jsonify({'message': 'User tidak ditemukan'}), 404

        if target_user.role == 'owner':
            return jsonify({'error': 'Role Owner bersifat permanen dan tidak bisa diubah.'}), 403

        if target_user.role == 'admin' and current_user.role != 'owner':
            return jsonify({'error': 'Hanya Owner yang berhak menurunkan jabatan Admin.'}), 403


        old_role = target_user.role
        target_user.role = new_role
        db.session.commit()
        
        record_log(
            actor_id=current_user.id,
            target_id=target_user.id,
            target_type='User',
            action='CHANGE_ROLE',
            old_val={'role': old_role},
            new_val={'role': new_role},
            description=f"Mengubah role {target_user.username} dari {old_role} menjadi {new_role}"
        )
        
        return jsonify({'message': f'Role {target_user.username} berhasil diubah menjadi {new_role}.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
# ANCHOR: SUSPEND USER
@admin_bp.route('/users/suspend', methods=['POST'])
@admin_required
def suspend_user(current_user):
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        days = data.get('days')

        user_to_suspend = User.query.get(user_id)
        if not user_to_suspend: return jsonify({'message': 'User tidak ditemukan'}), 404

        if user_to_suspend.role == 'owner':
            return jsonify({'message': 'Anda mau men-suspend Pemilik? Jangan bercanda.'}), 403
            
        if user_to_suspend.role == 'admin' and current_user.role != 'owner':
            return jsonify({'message': 'Hanya Owner yang bisa men-suspend Admin.'}), 403

        old_status = user_to_suspend.is_suspended
        old_until = user_to_suspend.suspended_until.isoformat() if user_to_suspend.suspended_until else None

        user_to_suspend.is_suspended = True
        
        if int(days) == -1:
            user_to_suspend.suspended_until = datetime(9999, 12, 31, tzinfo=timezone.utc)
            action_msg = "dibanned permanen"
        else:
            user_to_suspend.suspended_until = datetime.now(timezone.utc) + timedelta(days=int(days))
            action_msg = f"disuspend selama {days} hari"

        db.session.commit()

        record_log(
            actor_id=current_user.id,
            target_id=user_to_suspend.id,
            target_type='User',
            action='SUSPEND',
            old_val={'is_suspended': old_status, 'suspended_until': old_until},
            new_val={'is_suspended': True, 'days': days},
            description=f"Suspend user {user_to_suspend.username}: {action_msg}"
        )

        return jsonify({'message': f"User {user_to_suspend.username} berhasil {action_msg}."})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ANCHOR: UNSUSPEND USER
@admin_bp.route('/users/unsuspend', methods=['POST'])
@admin_required
def unsuspend_user(current_user):
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        user = User.query.get(user_id)
        if not user: return jsonify({'message': 'User tidak ditemukan'}), 404

        old_until = user.suspended_until.isoformat() if user.suspended_until else None

        user.is_suspended = False
        user.suspended_until = None
        db.session.commit()

        record_log(
            actor_id=current_user.id,
            target_id=user.id,
            target_type='User',
            action='UNSUSPEND',
            old_val={'is_suspended': True, 'suspended_until': old_until},
            new_val={'is_suspended': False},
            description=f"Memulihkan akun user {user.username}"
        )

        return jsonify({'message': f"Akun {user.username} berhasil dipulihkan."})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ANCHOR: DELETE USER (BY ADMIN)
@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user_by_admin(current_user, user_id):
    try:
        user_to_delete = User.query.get(user_id)
        if not user_to_delete: return jsonify({'error': 'User tidak ditemukan'}), 404

        if user_to_delete.role == 'owner':
            return jsonify({'error': 'AKSES DITOLAK: Owner tidak bisa dihapus.'}), 403
            
        if user_to_delete.role == 'admin' and current_user.role != 'owner':
            return jsonify({'error': 'Hanya Owner yang bisa menghapus akun Admin.'}), 403

        user_snapshot = {
            'username': user_to_delete.username,
            'email': user_to_delete.email,
            'role': user_to_delete.role
        }
        username_backup = user_to_delete.username

        db.session.delete(user_to_delete)
        db.session.commit()

        record_log(
            actor_id=current_user.id,
            target_id=None, 
            target_type='User',
            action='DELETE_USER',
            old_val=user_snapshot,
            new_val=None,
            description=f"Menghapus permanen user {username_backup}"
        )

        return jsonify({'message': f'User {username_backup} berhasil dihapus permanen.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ANCHOR: GET REPORTS
@admin_bp.route('/reports', methods=['GET'])
@admin_required
def get_reports(current_user):
    try:
        filter_type = request.args.get('type', 'post')
        
        query = db.session.query(Report, User).join(User, Report.reporter_user_id == User.id)\
            .filter(Report.status == 'pending')

        if filter_type == 'post':
            query = query.filter(Report.reported_post_id.isnot(None))
        elif filter_type == 'comment':
            query = query.filter(Report.reported_comment_id.isnot(None))
        elif filter_type == 'user':
            query = query.filter(Report.reported_user_id.isnot(None))
        
        raw_reports = query.order_by(Report.created_at.desc()).all()

        grouped_data = {}

        for r, reporter in raw_reports:
            target_id = None
            if filter_type == 'post': 
                target_id = str(r.reported_post_id)
            elif filter_type == 'comment': 
                target_id = str(r.reported_comment_id)
            elif filter_type == 'user': 
                target_id = str(r.reported_user_id)
            
            if not target_id: continue

            if target_id not in grouped_data:
                content_preview = {}
                
                if filter_type == 'post':
                    post = Post.query.get(target_id)
                    if post:
                        content_preview = {
                            'caption': post.caption,
                            'image_url': post.image_url,
                            'author': post.author.username if post.author else "Unknown",
                            'author_id': str(post.user_id)
                        }
                elif filter_type == 'comment':
                    comment = Comment.query.get(target_id)
                    if comment:
                        parent_post = Post.query.get(comment.post_id)
                        content_preview = {
                            'text': comment.text,
                            'author': comment.user.username if comment.user else "Unknown",
                            'author_id': str(comment.user_id),
                            'context_image': parent_post.image_url if parent_post else None,
                            'context_caption': parent_post.caption if parent_post else "Post dihapus"
                        }
                elif filter_type == 'user':
                    user = User.query.get(target_id)
                    if user:
                        content_preview = {
                            'username': user.username,
                            'display_name': user.display_name,
                            'avatar_url': user.avatar_url,
                            'banner_url': user.banner_url,
                            'bio': user.bio
                        }

                grouped_data[target_id] = {
                    'target_id': target_id,
                    'target_type': filter_type,
                    'report_count': 0,
                    'preview': content_preview,
                    'reasons': [], 
                    'reporters': [], 
                    'latest_report_id': r.id
                }

            group = grouped_data[target_id]
            group['report_count'] += 1
            
            if r.reason not in group['reasons']:
                group['reasons'].append(r.reason)
            
            if len(group['reporters']) < 3:
                group['reporters'].append(reporter.username)

        final_list = list(grouped_data.values())
        final_list.sort(key=lambda x: x['report_count'], reverse=True)

        return jsonify(final_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/reports/<int:report_id>/resolve', methods=['POST'])
@admin_required
def resolve_report(current_user, report_id):
    try:
        report = Report.query.get(report_id)
        if not report: return jsonify({'message': 'Laporan tidak ditemukan'}), 404
        
        data = request.get_json()
        new_status = data.get('action')
        
        old_status = report.status
        report.status = new_status
        db.session.commit()

        record_log(
            actor_id=current_user.id,
            target_id=str(report.id),
            target_type='Report',
            action='RESOLVE_REPORT',
            old_val={'status': old_status},
            new_val={'status': new_status},
            description=f"Menandai laporan #{report.id} sebagai {new_status}"
        )

        return jsonify({'message': f'Laporan ditandai sebagai {report.status}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ANCHOR: GET FEEDBACKS
@admin_bp.route('/feedbacks', methods=['GET'])
@admin_required
def get_feedbacks(current_user):
    try:
        time_range = request.args.get('range', 'all')
        now = datetime.now(timezone.utc) + timedelta(hours=7)
        start_date = None

        if time_range == '7d': start_date = now - timedelta(days=7)
        elif time_range == '30d': start_date = now - timedelta(days=30)
        elif time_range == '1y': start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0)
        
        query = Feedback.query
        if start_date:
            start_date_utc = (start_date - timedelta(hours=7)).replace(tzinfo=None)
            query = query.filter(Feedback.created_at >= start_date_utc)
            
        feedbacks = query.order_by(Feedback.created_at.desc()).limit(200).all()
        
        pos_list = []
        neg_list = []
        for f in feedbacks:
            item = {
                'id': f.id,
                'text': f.feedback_text,
                'sentiment': f.sentiment.lower() if f.sentiment else 'neutral',
                'created_at': f.created_at.strftime('%d %b %Y, %H:%M')
            }
            if item['sentiment'] == 'positive': pos_list.append(item)
            elif item['sentiment'] == 'negative': neg_list.append(item)
            else: pos_list.append(item)

        return jsonify({
            'total': len(feedbacks),
            'positive': pos_list,
            'negative': neg_list,
            'counts': [len(pos_list), len(neg_list)]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ANCHOR: UPDATE PROFILE
@admin_bp.route('/update-profile', methods=['POST'])
@admin_required
def update_profile(current_user):
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        
        if username and username != current_user.username:
            if User.query.filter_by(username=username).first(): 
                return jsonify({'message': 'Username sudah dipakai'}), 400
            current_user.username = username
            
        if email and email != current_user.email:
            if User.query.filter_by(email=email).first(): 
                return jsonify({'message': 'Email sudah dipakai'}), 400
            current_user.email = email

        current_user.display_name = request.form.get('display_name')
        
        file = request.files.get('avatar')
        if file and file.filename:
            filename = secure_filename(file.filename)
            upload_folder = os.path.join(current_app.root_path, 'static/uploads')
            if not os.path.exists(upload_folder): os.makedirs(upload_folder)
            
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            file.save(os.path.join(upload_folder, unique_filename))
            current_user.avatar_url = unique_filename

        db.session.commit()

        user_data = {
            'id': str(current_user.id),
            'username': current_user.username,
            'email': current_user.email,
            'display_name': current_user.display_name,
            'role': current_user.role,
            'avatar_url': current_user.avatar_url,
            'auth_provider': current_user.auth_provider,
            'google_uid': current_user.google_uid,
            'has_pin': bool(current_user.security_pin_hash)
        }

        return jsonify({'message': 'Profil berhasil diperbarui', 'user': user_data})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ANCHOR: CHANGE PASSWORD
@admin_bp.route('/change-password', methods=['POST'])
@admin_required
def change_password(current_user):
    try:
        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not new_password or len(new_password) < 6:
            return jsonify({'error': 'Password baru minimal 6 karakter.'}), 400

        if current_user.auth_provider == 'google':
            current_user.auth_provider = 'email' 
        else:
            if not old_password:
                return jsonify({'error': 'Harap masukkan password lama.'}), 400
            
            if not bcrypt.check_password_hash(current_user.password_hash, old_password):
                return jsonify({'error': 'Password lama salah!'}), 400

        current_user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        
        return jsonify({'message': 'Password berhasil diperbarui!'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
# ANCHOR: UPDATE PIN
@admin_bp.route('/update-pin', methods=['POST'])
@admin_required
def update_pin(current_user):
    data = request.get_json()
    new_pin = data.get('new_pin')
    
    if not new_pin or len(new_pin) != 6 or not new_pin.isdigit():
        return jsonify({'error': 'PIN harus 6 digit angka.'}), 400

    if current_user.security_pin_hash:
        if not data.get('old_pin'): return jsonify({'error': 'Masukkan PIN lama.'}), 400
        if not bcrypt.check_password_hash(current_user.security_pin_hash, data.get('old_pin')):
            return jsonify({'error': 'PIN lama salah.'}), 400
            
    current_user.security_pin_hash = bcrypt.generate_password_hash(new_pin).decode('utf-8')
    db.session.commit()
    return jsonify({'message': 'PIN Keamanan berhasil diperbarui!'})

# ANCHOR: DELETE ACCOUNT(SELF)
@admin_bp.route('/delete-account', methods=['DELETE'])
@admin_required
def delete_account(current_user):
    try:
        db.session.delete(current_user)
        db.session.commit()
        print(f"[AUDIT] User {current_user} telah menghapus akunnya sendiri secara permanen.")

        return jsonify({'message': 'Akun Anda telah dihapus selamanya.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
# ANCHOR: KEY PEOPLE
@admin_bp.route('/users/key-people', methods=['GET'])
@admin_required
def get_key_people(current_user):
    try:
        people = User.query.filter(User.role.in_(['owner', 'admin'])).order_by(User.role.desc()).all()
        
        data = []
        for u in people:
            data.append({
                'id': str(u.id),
                'username': u.username,
                'email': u.email,
                'role': u.role,
                'auth_provider': u.auth_provider,
                'is_suspended': u.is_suspended,
                'avatar_url': u.avatar_url,
                'created_at': u.created_at.strftime('%Y-%m-%d')
            })
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ANCHOR: REGULAR USERS
@admin_bp.route('/users/regular', methods=['GET'])
@admin_required
def get_regular_users(current_user):
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 10, type=int)
        search = request.args.get('q', '', type=str)

        query = User.query.filter_by(role='user')

        if search:
            search_term = f"%{search}%"
            query = query.filter((User.username.ilike(search_term)) | (User.email.ilike(search_term)))

        query = query.order_by(User.created_at.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        users_data = []
        for u in pagination.items:
            users_data.append({
                'id': str(u.id),
                'username': u.username,
                'email': u.email,
                'role': u.role,
                'auth_provider': u.auth_provider,
                'is_suspended': u.is_suspended,
                'avatar_url': u.avatar_url,
                'created_at': u.created_at.strftime('%Y-%m-%d')
            })

        return jsonify({
            'users': users_data,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# ANCHOR: AUTOCOMPLETE
@admin_bp.route('/users/autocomplete', methods=['GET'])
@admin_required
def autocomplete_users(current_user):
    try:
        query = request.args.get('q', '', type=str)
        if len(query) < 2: 
            return jsonify([])

        search_term = f"%{query}%"
        users = User.query.filter(
            (User.email.ilike(search_term)) | (User.username.ilike(search_term))
        ).limit(5).all()

        results = []
        for u in users:
            results.append({
                'email': u.email,
                'username': u.username,
                'avatar_url': u.avatar_url
            })
        
        return jsonify(results)
    except Exception as e:
        return jsonify([])
    
# ANCHOR: LINK GOOGLE
@admin_bp.route('/link-google', methods=['POST'])
@admin_required
def link_google_account(current_user):
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token: return jsonify({'message': 'Token Google tidak ditemukan'}), 400

        decoded_token = firebase_auth.verify_id_token(token)
        google_uid = decoded_token['uid']
        google_email = decoded_token['email']

        if google_email.lower() != current_user.email.lower():
             return jsonify({'message': 'Email Google harus sama dengan email akun ini.'}), 400

        existing_user = User.query.filter_by(google_uid=google_uid).first()
        if existing_user and existing_user.id != current_user.id:
            return jsonify({'message': 'Akun Google ini sudah terhubung ke user lain!'}), 409

        current_user.google_uid = google_uid
        db.session.commit()

        return jsonify({
            'message': 'Akun Google berhasil dihubungkan.',
            'google_uid': google_uid
        })

    except Exception as e:
        return jsonify({'message': 'Token tidak valid atau expired.', 'error': str(e)}), 400
    
# ANCHOR: BANNED USERS
@admin_bp.route('/users/banned', methods=['GET'])
@admin_required
def get_banned_users(current_user):
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('q', '', type=str)
        per_page = 10
        
        query = User.query.filter_by(is_suspended=True)

        if search:
            search_term = f"%{search}%"
            query = query.filter((User.username.ilike(search_term)) | (User.email.ilike(search_term)))

        query = query.order_by(User.suspended_until.asc())
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        banned_data = []
        for u in pagination.items:
            status_label = "SEMENTARA"
            until_str = "-"
            
            if u.suspended_until:
                if u.suspended_until.year == 9999:
                    status_label = "PERMANEN"
                    until_str = "Selamanya"
                else:
                    until_str = u.suspended_until.strftime('%d %b %Y')
            
            banned_data.append({
                'id': str(u.id),
                'username': u.username,
                'email': u.email,
                'avatar_url': u.avatar_url,
                'role': u.role,
                'status_label': status_label,
                'until': until_str
            })

        return jsonify({
            'users': banned_data,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# ANCHOR: ACTIVITY LOGS
@admin_bp.route('/activity-logs', methods=['GET'])
@admin_required
def get_activity_logs(current_user):
    time_filter = request.args.get('filter', '14d')
    search = request.args.get('q', '')

    query = AuditLog.query
    
    # Filter Waktu
    now = datetime.now(timezone.utc)
    if time_filter == '1d':
        start_date = now - timedelta(days=1)
    elif time_filter == '3d':
        start_date = now - timedelta(days=3)
    elif time_filter == '7d':
        start_date = now - timedelta(days=7)
    else:
        start_date = now - timedelta(days=14)
    
    query = query.filter(AuditLog.created_at >= start_date)

    if search:
        search_term = f"%{search}%"
        query = query.filter(AuditLog.description.ilike(search_term))

    logs = query.order_by(AuditLog.created_at.desc()).all()
    
    data = []
    for log in logs:
        actor = User.query.get(log.actor_id)
        actor_name = actor.username if actor else "Unknown"
        actor_avatar = actor.avatar_url if actor else ""

        data.append({
            'id': log.id,
            'actor_name': actor_name,
            'actor_avatar': actor_avatar,
            'action': log.action,
            'description': log.description,
            'timestamp': log.created_at.strftime('%d %b %H:%M'),
            'can_revert': log.old_value is not None
        })

    return jsonify(data)

@admin_bp.route('/activity-logs/<int:log_id>/revert', methods=['POST'])
@admin_required
def revert_activity(current_user, log_id):
    if current_user.role != 'owner':
        return jsonify({'error': 'Hanya Owner yang bisa melakukan Revert!'}), 403

    log = AuditLog.query.get(log_id)
    if not log or not log.old_value:
        return jsonify({'error': 'Log tidak ditemukan atau tidak bisa direvert.'}), 400

    try:
        target_user = User.query.get(log.target_id)
        if not target_user:
            return jsonify({'error': 'User target sudah dihapus permanen, tidak bisa revert.'}), 404

        if log.action == 'CHANGE_ROLE':
            target_user.role = log.old_value.get('role')
        
        elif log.action == 'SUSPEND' or log.action == 'UNSUSPEND':
            target_user.is_suspended = log.old_value.get('is_suspended')
            old_date = log.old_value.get('suspended_until')
            if old_date:
                target_user.suspended_until = datetime.fromisoformat(old_date)
            else:
                target_user.suspended_until = None

        db.session.commit()
        
        record_log(current_user.id, target_user.id, 'User', 'REVERT', None, None, f"Owner membatalkan aksi: {log.description}")

        return jsonify({'message': 'Perubahan berhasil dibatalkan (Reverted).'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    


import shutil

@admin_bp.route('/appeals', methods=['GET'])
@admin_required
def get_appeals(current_user):
    try:
        from ..models import Appeal, Post, User
        appeals = db.session.query(Appeal, User).join(User, Appeal.user_id == User.id)\
            .filter(Appeal.status == 'pending')\
            .order_by(Appeal.created_at.desc()).all()
        
        data = []
        for app, user in appeals:
            post = Post.query.get(app.content_id)
            data.append({
                'id': app.id,
                'user_id': str(user.id),
                'username': user.username,
                'justification': app.justification,
                'content_type': app.content_type,
                'content_id': str(app.content_id),
                'post_caption': post.caption if post else "Post dihapus",
                'post_image': post.image_url if post else None,
                'moderation_details': post.moderation_details if post else {},
                'created_at': app.created_at.strftime('%Y-%m-%d %H:%M')
            })
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/appeals/<int:appeal_id>/action', methods=['POST'])
@admin_required
def handle_appeal_action(current_user, appeal_id):
    try:
        from ..models import Appeal, Post
        app = Appeal.query.get(appeal_id)
        if not app: return jsonify({'error': 'Banding tidak ditemukan'}), 404
        
        data = request.get_json()
        action = data.get('action') 
        admin_note = data.get('admin_note', '')

        post = Post.query.get(app.content_id)
        if not post:
            db.session.delete(app)
            db.session.commit()
            return jsonify({'error': 'Konten terkait sudah tidak ada'}), 404

        reject_folder = os.path.join(current_app.root_path, 'static', 'reject')
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        filename = post.image_url

        if action == 'approved':
            if filename:
                src = os.path.join(reject_folder, filename)
                dst = os.path.join(upload_folder, filename)
                if os.path.exists(src):
                    shutil.move(src, dst)
            post.moderation_status = 'approved'
            app.status = 'approved'
            notif_type = 'appeal_approved'
        else:
            if filename:
                path = os.path.join(reject_folder, filename)
                if os.path.exists(path):
                    os.remove(path)
            post.moderation_status = 'final_rejected'
            post.image_url = None
            app.status = 'rejected'
            notif_type = 'appeal_rejected'

        app.admin_note = admin_note
        app.reviewed_at = datetime.now(timezone.utc)
        db.session.commit()

        create_notification(
            recipient_id=app.user_id,
            sender_id=current_user.id,
            type=notif_type,
            reference_id=str(app.id),
            text=admin_note
        )

        return jsonify({'message': 'Keputusan berhasil dikirim'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


def move_file_to_quarantine(filename):
    if not filename: return None
    
    upload_folder = os.path.join(current_app.root_path, 'static/uploads')
    quarantine_folder = os.path.join(current_app.root_path, 'static/quarantine')
    
    if not os.path.exists(quarantine_folder):
        os.makedirs(quarantine_folder)
        
    src = os.path.join(upload_folder, filename)
    
    ext = filename.split('.')[-1]
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    dst = os.path.join(quarantine_folder, safe_name)
    
    if os.path.exists(src):
        shutil.move(src, dst)
        return safe_name
    return None

@admin_bp.route('/reports/action/quarantine-post', methods=['POST'])
@admin_required
def action_quarantine_post(current_user):
    try:
        data = request.get_json()
        post_id = data.get('target_id')
        reason = data.get('reason', 'Melanggar Pedoman Komunitas')

        post = Post.query.get(post_id)
        if not post: return jsonify({'error': 'Post tidak ditemukan'}), 404

        quarantine_path = None
        if post.image_url:
            quarantine_path = move_file_to_quarantine(post.image_url)

        q_item = QuarantinedItem(
            original_target_id=post.id, # type: ignore
            target_type='post', # type: ignore
            file_path=quarantine_path, # type: ignore
            text_content=post.caption, # type: ignore
            quarantined_by=current_user.id, # type: ignore
            reason=reason # type: ignore
        )
        db.session.add(q_item)

        post.image_url = None
        post.moderation_status = 'quarantined'
        post.caption = "[Konten ini telah dihapus oleh Tim Admin karena melanggar pedoman komunitas]"
        
        Report.query.filter_by(reported_post_id=post.id, status='pending')\
            .update({Report.status: 'resolved'})

        db.session.commit()

        create_notification(
            recipient_id=post.user_id,
            sender_id=current_user.id,
            type='post_rejected',
            reference_id=str(post.id),
            text=f"Postingan Anda dihapus: {reason}"
        )

        return jsonify({'message': 'Post berhasil dikarantina dan laporan diselesaikan.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# --- ACTION: DISMISS (ABAIKAN LAPORAN) ---
@admin_bp.route('/reports/action/dismiss-group', methods=['POST'])
@admin_required
def action_dismiss_group(current_user):
    try:
        data = request.get_json()
        target_id = data.get('target_id')
        target_type = data.get('target_type') 

        query = Report.query.filter_by(status='pending')

        if target_type == 'post':
            query = query.filter_by(reported_post_id=target_id)
        elif target_type == 'comment':
            query = query.filter_by(reported_comment_id=target_id)
        elif target_type == 'user':
            query = query.filter_by(reported_user_id=target_id)
        
        # Update massal
        count = query.update({Report.status: 'dismissed'})
        db.session.commit()

        return jsonify({'message': f'{count} laporan diabaikan. Konten dianggap aman.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/reports/action/delete-comment', methods=['POST'])
@admin_required
def action_delete_comment(current_user):
    try:
        data = request.get_json()
        comment_id = data.get('target_id')
        reason = data.get('reason', 'Spam/Toxic')

        comment = Comment.query.get(comment_id)
        if not comment: return jsonify({'error': 'Komentar tidak ditemukan'}), 404

        target_user_id = comment.user_id 
        
        db.session.add(QuarantinedItem(
            original_target_id=comment.id, # type: ignore
            target_type='comment', # type: ignore
            text_content=comment.text, # type: ignore
            quarantined_by=current_user.id, # type: ignore
            reason=reason # type: ignore
        ))

        db.session.query(Report).filter(Report.reported_comment_id == comment_id).update({
            Report.reported_comment_id: None,
            Report.status: 'resolved'
        }, synchronize_session=False)

        db.session.delete(comment)
        
        db.session.commit()

        create_notification(
            recipient_id=target_user_id,
            sender_id=current_user.id,
            type='system',
            text=f"Komentar Anda dihapus karena melanggar aturan: {reason}"
        )

        return jsonify({'message': 'Komentar berhasil dihapus.'})

    except Exception as e:
        db.session.rollback()
        print(f"ERROR DELETE COMMENT: {e}") 
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/reports/action/sanitize-user', methods=['POST'])
@admin_required
def action_sanitize_user(current_user):
    try:
        data = request.get_json()
        user_id = data.get('target_id')
        fields = data.get('fields', []) 
        reason = data.get('reason', 'Profil tidak pantas')

        target_user = User.query.get(user_id)
        if not target_user: return jsonify({'error': 'User tidak ditemukan'}), 404

        actions_taken = []

        if 'avatar' in fields and target_user.avatar_url:
            q_path = move_file_to_quarantine(target_user.avatar_url)
            db.session.add(QuarantinedItem(
                original_target_id=target_user.id, target_type='user_avatar', # type: ignore
                file_path=q_path, quarantined_by=current_user.id, reason=reason # type: ignore
            ))
            target_user.avatar_url = None
            actions_taken.append("Avatar direset")

        if 'banner' in fields and target_user.banner_url:
            q_path = move_file_to_quarantine(target_user.banner_url)
            db.session.add(QuarantinedItem(
                original_target_id=target_user.id, target_type='user_banner', # type: ignore
                file_path=q_path, quarantined_by=current_user.id, reason=reason # type: ignore
            ))
            target_user.banner_url = None
            actions_taken.append("Banner direset")

        if 'bio' in fields:
            db.session.add(QuarantinedItem(
                original_target_id=target_user.id, target_type='user_bio', # type: ignore
                text_content=target_user.bio, quarantined_by=current_user.id, reason=reason # type: ignore
            ))
            target_user.bio = ""
            actions_taken.append("Bio dibersihkan")

        if 'display_name' in fields:
            old_name = target_user.display_name
            target_user.display_name = "Amica User"
            actions_taken.append(f"Nama diubah dari {old_name}")

        if 'username' in fields:
            old_username = target_user.username
            random_suffix = uuid.uuid4().hex[:8]
            new_username = f"user_{random_suffix}"
            target_user.username = new_username
            actions_taken.append(f"Username acak: {new_username}")

        Report.query.filter_by(reported_user_id=target_user.id, status='pending')\
            .update({Report.status: 'resolved'})

        db.session.commit()

        create_notification(
            recipient_id=target_user.id, sender_id=current_user.id, type='system', 
            text=f"Profil Anda disesuaikan Admin: {', '.join(actions_taken)}."
        )

        return jsonify({'message': 'Sanitasi berhasil.', 'details': actions_taken})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    

@admin_bp.route('/quarantine-list', methods=['GET'])
@admin_required
def get_quarantine_list(current_user):
    try:
        items = QuarantinedItem.query.order_by(QuarantinedItem.created_at.desc()).all()
        data = []
        for item in items:
            admin = User.query.get(item.quarantined_by)
            data.append({
                'id': str(item.id),
                'target_type': item.target_type,
                'file_path': item.file_path,
                'text_content': item.text_content,
                'reason': item.reason,
                'admin_name': admin.username if admin else "System",
                'created_at': item.created_at.strftime('%d %b %Y, %H:%M')
            })
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500