from flask import Blueprint, jsonify, g, request
from models import db, User, Family, Member, FamilyRelation, Marriage
from auth import admin_required, login_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    return jsonify({
        'total_users': User.query.count(),
        'total_families': Family.query.count(),
        'total_members': Member.query.count(),
        'total_relations': FamilyRelation.query.count(),
        'total_marriages': Marriage.query.count(),
    })


@admin_bp.route('/admin/users', methods=['GET'])
@admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([{
        'user_id': u.user_id,
        'username': u.username,
        'email': u.email,
        'is_admin': u.is_admin,
        'family_count': Family.query.filter_by(user_id=u.user_id).count(),
        'created_at': u.created_at.isoformat() if u.created_at else None
    } for u in users])


@admin_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if user_id == g.current_user.user_id:
        return jsonify({'error': 'Cannot delete yourself'}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    # Cascade deletes families → members → relations → marriages
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User and all data deleted'})


@admin_bp.route('/admin/users/<int:user_id>/admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user.is_admin = not user.is_admin
    db.session.commit()
    return jsonify({'user_id': user.user_id, 'username': user.username, 'is_admin': user.is_admin})


@admin_bp.route('/admin/families', methods=['GET'])
@admin_required
def list_all_families():
    families = Family.query.join(User).order_by(Family.created_at.desc()).all()
    return jsonify([{
        'family_id': f.family_id,
        'family_name': f.family_name,
        'description': f.description,
        'owner_username': f.owner.username,
        'user_id': f.user_id,
        'member_count': f.members.count(),
        'created_at': f.created_at.isoformat() if f.created_at else None
    } for f in families])


@admin_bp.route('/admin/families/<int:family_id>', methods=['DELETE'])
@admin_required
def admin_delete_family(family_id):
    family = Family.query.get(family_id)
    if not family:
        return jsonify({'error': 'Family not found'}), 404
    db.session.delete(family)
    db.session.commit()
    return jsonify({'message': 'Family deleted'})


@admin_bp.route('/admin/me', methods=['GET'])
@login_required
def check_admin():
    return jsonify({
        'user_id': g.current_user.user_id,
        'username': g.current_user.username,
        'is_admin': g.current_user.is_admin
    })
