from flask import Blueprint, request, jsonify, g
from models import db, Family, FamilyRelation, Marriage
from auth import login_required

family_bp = Blueprint('family', __name__)

@family_bp.route('', methods=['GET'])
@login_required
def list_families():
    families = Family.query.filter_by(user_id=g.current_user.user_id)\
        .order_by(Family.created_at.desc()).all()
    return jsonify([{
        'family_id': f.family_id,
        'family_name': f.family_name,
        'description': f.description,
        'member_count': f.members.count(),
        'created_at': f.created_at.isoformat() if f.created_at else None
    } for f in families])

@family_bp.route('', methods=['POST'])
@login_required
def create_family():
    data = request.get_json()
    if not data or not data.get('family_name', '').strip():
        return jsonify({'error': 'Family name is required'}), 400

    family = Family(
        user_id=g.current_user.user_id,
        family_name=data['family_name'].strip(),
        description=data.get('description', '').strip() or None
    )
    db.session.add(family)
    db.session.commit()
    return jsonify({
        'family_id': family.family_id,
        'family_name': family.family_name,
        'description': family.description
    }), 201

@family_bp.route('/<int:family_id>', methods=['GET'])
@login_required
def get_family(family_id):
    family = Family.query.filter_by(family_id=family_id, user_id=g.current_user.user_id).first()
    if not family:
        return jsonify({'error': 'Family not found'}), 404
    return jsonify({
        'family_id': family.family_id,
        'family_name': family.family_name,
        'description': family.description,
        'member_count': family.members.count(),
        'created_at': family.created_at.isoformat() if family.created_at else None
    })

@family_bp.route('/<int:family_id>', methods=['PUT'])
@login_required
def update_family(family_id):
    family = Family.query.filter_by(family_id=family_id, user_id=g.current_user.user_id).first()
    if not family:
        return jsonify({'error': 'Family not found'}), 404
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    if 'family_name' in data and data['family_name'].strip():
        family.family_name = data['family_name'].strip()
    if 'description' in data:
        family.description = data['description'].strip() or None
    db.session.commit()
    return jsonify({'family_id': family.family_id, 'family_name': family.family_name,
                    'description': family.description})

@family_bp.route('/<int:family_id>', methods=['DELETE'])
@login_required
def delete_family(family_id):
    family = Family.query.filter_by(family_id=family_id, user_id=g.current_user.user_id).first()
    if not family:
        return jsonify({'error': 'Family not found'}), 404

    # Clean up all cross-family relations before cascade delete
    member_ids = [m.member_id for m in family.members.all()]
    if member_ids:
        FamilyRelation.query.filter(
            FamilyRelation.parent_id.in_(member_ids) | FamilyRelation.child_id.in_(member_ids)
        ).delete(synchronize_session='fetch')
        Marriage.query.filter(
            Marriage.husband_id.in_(member_ids) | Marriage.wife_id.in_(member_ids)
        ).delete(synchronize_session='fetch')

    db.session.delete(family)
    db.session.commit()
    return jsonify({'message': 'Family deleted'})
