from datetime import datetime
from flask import Blueprint, request, jsonify, g
from models import db, Member, Family, FamilyRelation, Marriage
from auth import login_required

relation_bp = Blueprint('relation', __name__)

def check_member_access(member_id):
    """Check if current user has access to the member's family."""
    member = Member.query.get(member_id)
    if not member:
        return None, False
    family = Family.query.get(member.family_id)
    if family and (family.user_id == g.current_user.user_id or g.current_user.is_admin):
        return member, True
    return member, False

@relation_bp.route('/parent-child', methods=['POST'])
@login_required
def add_parent_child():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    parent_id = data.get('parent_id')
    child_id = data.get('child_id')
    relation_type = data.get('relation_type', 'biological')

    if not parent_id or not child_id:
        return jsonify({'error': 'parent_id and child_id are required'}), 400
    if parent_id == child_id:
        return jsonify({'error': 'A person cannot be their own parent'}), 400

    parent, ok = check_member_access(parent_id)
    if not ok:
        return jsonify({'error': 'Parent not found or access denied'}), 404
    child, ok = check_member_access(child_id)
    if not ok:
        return jsonify({'error': 'Child not found or access denied'}), 404
    # Cross-family parent-child relations are allowed (families can connect)

    existing = FamilyRelation.query.filter_by(parent_id=parent_id, child_id=child_id).first()
    if existing:
        return jsonify({'error': 'This relationship already exists'}), 409

    # Check for cycles
    result = db.session.execute(db.text("""
        WITH RECURSIVE ancestor_chain AS (
            SELECT parent_id, child_id, 1 AS depth
            FROM family_relations WHERE child_id = :parent_id
            UNION ALL
            SELECT fr.parent_id, fr.child_id, ac.depth + 1
            FROM family_relations fr
            JOIN ancestor_chain ac ON fr.child_id = ac.parent_id
            WHERE ac.depth < 100
        )
        SELECT COUNT(*) as cnt FROM ancestor_chain WHERE parent_id = :child_id
    """), {'parent_id': parent_id, 'child_id': child_id}).fetchone()

    if result[0] > 0:
        return jsonify({'error': 'Cyclic relation detected: this would create a loop'}), 400

    # Check parent birth < child birth
    if parent.birth_date and child.birth_date and parent.birth_date >= child.birth_date:
        return jsonify({'error': 'Parent birth date must be before child birth date'}), 400

    rel = FamilyRelation(parent_id=parent_id, child_id=child_id, relation_type=relation_type)
    db.session.add(rel)
    db.session.commit()

    return jsonify({
        'relation_id': rel.relation_id,
        'parent_id': rel.parent_id,
        'child_id': rel.child_id,
        'relation_type': rel.relation_type
    }), 201

@relation_bp.route('/parent-child/<int:relation_id>', methods=['DELETE'])
@login_required
def delete_parent_child(relation_id):
    rel = FamilyRelation.query.get(relation_id)
    if not rel:
        return jsonify({'error': 'Relation not found'}), 404
    _, ok = check_member_access(rel.parent_id)
    if not ok:
        return jsonify({'error': 'Access denied'}), 403
    db.session.delete(rel)
    db.session.commit()
    return jsonify({'message': 'Relation deleted'})


@relation_bp.route('/parent-child/remove', methods=['DELETE'])
@login_required
def delete_parent_child_by_members():
    """Delete parent-child relation by parent_id and child_id query params."""
    parent_id = request.args.get('parent_id', type=int)
    child_id = request.args.get('child_id', type=int)
    if not parent_id or not child_id:
        return jsonify({'error': 'parent_id and child_id are required'}), 400
    rel = FamilyRelation.query.filter_by(parent_id=parent_id, child_id=child_id).first()
    if not rel:
        return jsonify({'error': 'Relation not found'}), 404
    _, ok = check_member_access(rel.parent_id)
    if not ok:
        return jsonify({'error': 'Access denied'}), 403
    db.session.delete(rel)
    db.session.commit()
    return jsonify({'message': 'Relation deleted'})

@relation_bp.route('/marriage', methods=['POST'])
@login_required
def add_marriage():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    husband_id = data.get('husband_id')
    wife_id = data.get('wife_id')

    if not husband_id or not wife_id:
        return jsonify({'error': 'husband_id and wife_id are required'}), 400
    if husband_id == wife_id:
        return jsonify({'error': 'Cannot marry oneself'}), 400

    husband, ok = check_member_access(husband_id)
    if not ok:
        return jsonify({'error': 'Husband not found or access denied'}), 404
    wife, ok = check_member_access(wife_id)
    if not ok:
        return jsonify({'error': 'Wife not found or access denied'}), 404
    # Cross-family marriages are allowed (inter-family unions are common)

    marriage_date = datetime.strptime(data['marriage_date'], '%Y-%m-%d').date() if data.get('marriage_date') else None
    divorce_date = datetime.strptime(data['divorce_date'], '%Y-%m-%d').date() if data.get('divorce_date') else None

    marriage = Marriage(
        husband_id=husband_id, wife_id=wife_id,
        marriage_date=marriage_date, divorce_date=divorce_date
    )
    db.session.add(marriage)
    db.session.commit()

    return jsonify({
        'marriage_id': marriage.marriage_id,
        'husband_id': marriage.husband_id,
        'wife_id': marriage.wife_id
    }), 201

@relation_bp.route('/marriage/<int:marriage_id>', methods=['DELETE'])
@login_required
def delete_marriage(marriage_id):
    marriage = Marriage.query.get(marriage_id)
    if not marriage:
        return jsonify({'error': 'Marriage not found'}), 404
    _, ok = check_member_access(marriage.husband_id)
    if not ok:
        return jsonify({'error': 'Access denied'}), 403
    db.session.delete(marriage)
    db.session.commit()
    return jsonify({'message': 'Marriage deleted'})


@relation_bp.route('/marriage/remove', methods=['DELETE'])
@login_required
def delete_marriage_by_members():
    """Delete marriage by member_id and spouse_id query params."""
    member_id = request.args.get('member_id', type=int)
    spouse_id = request.args.get('spouse_id', type=int)
    if not member_id or not spouse_id:
        return jsonify({'error': 'member_id and spouse_id are required'}), 400

    marriage = Marriage.query.filter(
        ((Marriage.husband_id == member_id) & (Marriage.wife_id == spouse_id)) |
        ((Marriage.husband_id == spouse_id) & (Marriage.wife_id == member_id))
    ).first()
    if not marriage:
        return jsonify({'error': 'Marriage not found'}), 404
    _, ok = check_member_access(marriage.husband_id)
    if not ok:
        return jsonify({'error': 'Access denied'}), 403
    db.session.delete(marriage)
    db.session.commit()
    return jsonify({'message': 'Marriage deleted'})

@relation_bp.route('/path', methods=['GET'])
@login_required
def find_blood_path():
    person_a_id = request.args.get('person_a', type=int)
    person_b_id = request.args.get('person_b', type=int)

    if not person_a_id or not person_b_id:
        return jsonify({'error': 'Both person_a and person_b are required'}), 400
    if person_a_id == person_b_id:
        return jsonify({'path': [], 'relation': 'self', 'message': 'Same person'})

    person_a, ok = check_member_access(person_a_id)
    if not ok:
        return jsonify({'error': 'Person A not found or access denied'}), 404
    person_b, ok = check_member_access(person_b_id)
    if not ok:
        return jsonify({'error': 'Person B not found or access denied'}), 404
    # Blood relations can span across families

    # Find all ancestors of person_a with their paths
    ancestors_a = db.session.execute(db.text("""
        WITH RECURSIVE ancestor_path AS (
            SELECT fr.parent_id, m.name, m.gender, 1 AS depth,
                   fr.child_id || ',' || fr.parent_id AS path
            FROM family_relations fr
            JOIN members m ON fr.parent_id = m.member_id
            WHERE fr.child_id = :person_a
            UNION ALL
            SELECT fr.parent_id, m.name, m.gender, ap.depth + 1,
                   ap.path || ',' || fr.parent_id
            FROM family_relations fr
            JOIN members m ON fr.parent_id = m.member_id
            JOIN ancestor_path ap ON fr.child_id = ap.parent_id
            WHERE ap.depth < 50
              AND ap.path NOT LIKE '%' || fr.parent_id || '%'
        )
        SELECT parent_id, name, gender, depth, path FROM ancestor_path
    """), {'person_a': person_a_id}).fetchall()

    # Find all ancestors of person_b
    ancestors_b = db.session.execute(db.text("""
        WITH RECURSIVE ancestor_path AS (
            SELECT fr.parent_id, m.name, m.gender, 1 AS depth,
                   fr.child_id || ',' || fr.parent_id AS path
            FROM family_relations fr
            JOIN members m ON fr.parent_id = m.member_id
            WHERE fr.child_id = :person_b
            UNION ALL
            SELECT fr.parent_id, m.name, m.gender, ap.depth + 1,
                   ap.path || ',' || fr.parent_id
            FROM family_relations fr
            JOIN members m ON fr.parent_id = m.member_id
            JOIN ancestor_path ap ON fr.child_id = ap.parent_id
            WHERE ap.depth < 50
              AND ap.path NOT LIKE '%' || fr.parent_id || '%'
        )
        SELECT parent_id, name, gender, depth, path FROM ancestor_path
    """), {'person_b': person_b_id}).fetchall()

    # Convert to dicts keyed by member_id
    ancestors_a_dict = {}
    for row in ancestors_a:
        ancestors_a_dict[row.parent_id] = {
            'member_id': row.parent_id, 'name': row.name, 'gender': row.gender,
            'depth': row.depth, 'path': [int(x) for x in row.path.split(',')]
        }
    # Also include person_a themselves
    ancestors_a_dict[person_a_id] = {
        'member_id': person_a_id, 'name': person_a.name, 'gender': person_a.gender,
        'depth': 0, 'path': [person_a_id]
    }

    ancestors_b_dict = {}
    for row in ancestors_b:
        ancestors_b_dict[row.parent_id] = {
            'member_id': row.parent_id, 'name': row.name, 'gender': row.gender,
            'depth': row.depth, 'path': [int(x) for x in row.path.split(',')]
        }
    ancestors_b_dict[person_b_id] = {
        'member_id': person_b_id, 'name': person_b.name, 'gender': person_b.gender,
        'depth': 0, 'path': [person_b_id]
    }

    # Find common ancestors
    common_ids = set(ancestors_a_dict.keys()) & set(ancestors_b_dict.keys())

    if not common_ids:
        return jsonify({'path': [], 'relation': 'none', 'message': 'No blood relationship found'})

    # Find the closest common ancestor (minimum combined depth)
    best_common = None
    min_total_depth = float('inf')
    for cid in common_ids:
        total = ancestors_a_dict[cid]['depth'] + ancestors_b_dict[cid]['depth']
        if total < min_total_depth:
            min_total_depth = total
            best_common = cid

    common = ancestors_a_dict[best_common]
    path_a = ancestors_a_dict[best_common]['path']
    path_b = ancestors_b_dict[best_common]['path']

    # path_a goes from person_a up to common ancestor
    # path_b goes from person_b up to common ancestor
    # Merge: person_a -> ... -> common -> ... -> person_b (reversed path_b)
    full_path = path_a + path_b[-2::-1]  # exclude common ancestor from second half, reverse

    # Build detailed path entries
    path_entries = []
    for i, mid in enumerate(full_path):
        m = Member.query.get(mid)
        entry = {
            'member_id': mid,
            'name': m.name if m else 'Unknown',
            'gender': m.gender if m else '?',
            'position': i
        }
        if i == 0:
            entry['role'] = 'person_a'
        elif i == len(full_path) - 1:
            entry['role'] = 'person_b'
        elif mid == best_common:
            entry['role'] = 'common_ancestor'
        else:
            entry['role'] = 'intermediate'
        path_entries.append(entry)

    return jsonify({
        'path': path_entries,
        'common_ancestor': {
            'member_id': best_common,
            'name': common['name'],
            'depth_from_a': ancestors_a_dict[best_common]['depth'],
            'depth_from_b': ancestors_b_dict[best_common]['depth']
        },
        'relation': 'blood',
        'total_distance': len(full_path) - 1
    })

@relation_bp.route('/members/<int:member_id>/spouses', methods=['GET'])
@login_required
def get_spouses(member_id):
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    family = Family.query.filter_by(family_id=member.family_id, user_id=g.current_user.user_id).first()
    if not family:
        return jsonify({'error': 'Access denied'}), 403

    spouses = []
    for m in member.marriages_as_husband:
        spouses.append({
            'member_id': m.wife.member_id, 'name': m.wife.name,
            'marriage_date': m.marriage_date.isoformat() if m.marriage_date else None,
            'divorce_date': m.divorce_date.isoformat() if m.divorce_date else None
        })
    for m in member.marriages_as_wife:
        spouses.append({
            'member_id': m.husband.member_id, 'name': m.husband.name,
            'marriage_date': m.marriage_date.isoformat() if m.marriage_date else None,
            'divorce_date': m.divorce_date.isoformat() if m.divorce_date else None
        })
    return jsonify({'member_id': member_id, 'spouses': spouses})
