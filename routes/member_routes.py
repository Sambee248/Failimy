from datetime import datetime, date
from flask import Blueprint, request, jsonify, g
from models import db, Family, Member, FamilyRelation, Marriage
from auth import login_required


def _format_date(val):
    """Safely format a date value (handles both date objects and strings)."""
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return val.isoformat()

member_bp = Blueprint('member', __name__)

def check_family_access(family_id):
    family = Family.query.get(family_id)
    if family and (family.user_id == g.current_user.user_id or g.current_user.is_admin):
        return family
    return None

@member_bp.route('/families/<int:family_id>', methods=['GET'])
@login_required
def list_members(family_id):
    family = check_family_access(family_id)
    if not family:
        return jsonify({'error': 'Family not found'}), 404

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').strip()
    gender = request.args.get('gender', '').strip()
    generation = request.args.get('generation', type=int)

    query = Member.query.filter_by(family_id=family_id)
    if search:
        query = query.filter(Member.name.contains(search))
    if gender in ('M', 'F'):
        query = query.filter(Member.gender == gender)
    if generation:
        query = query.filter(Member.generation == generation)

    total = query.count()
    members = query.order_by(Member.generation, Member.name)\
        .offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'members': [{
            'member_id': m.member_id,
            'name': m.name,
            'gender': m.gender,
            'birth_date': m.birth_date.isoformat() if m.birth_date else None,
            'death_date': m.death_date.isoformat() if m.death_date else None,
            'generation': m.generation,
            'biography': m.biography
        } for m in members],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })

@member_bp.route('/families/<int:family_id>', methods=['POST'])
@login_required
def create_member(family_id):
    family = check_family_access(family_id)
    if not family:
        return jsonify({'error': 'Family not found'}), 404

    data = request.get_json()
    if not data or not data.get('name', '').strip():
        return jsonify({'error': 'Name is required'}), 400

    birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date() if data.get('birth_date') else None
    death_date = datetime.strptime(data['death_date'], '%Y-%m-%d').date() if data.get('death_date') else None

    member = Member(
        family_id=family_id,
        name=data['name'].strip(),
        gender=data.get('gender', 'M'),
        birth_date=birth_date,
        death_date=death_date,
        generation=data.get('generation', 1),
        biography=data.get('biography', '').strip() or None,
        created_by=g.current_user.user_id
    )
    db.session.add(member)
    db.session.commit()

    return jsonify({
        'member_id': member.member_id,
        'name': member.name,
        'gender': member.gender,
        'generation': member.generation
    }), 201

@member_bp.route('/<int:member_id>', methods=['GET'])
@login_required
def get_member(member_id):
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404

    family = check_family_access(member.family_id)
    if not family:
        return jsonify({'error': 'Access denied'}), 403

    # Parents
    parents = []
    for rel in member.parent_relations:
        p = rel.parent
        parents.append({
            'member_id': p.member_id, 'name': p.name, 'gender': p.gender,
            'birth_date': _format_date(p.birth_date),
            'death_date': _format_date(p.death_date),
            'generation': p.generation,
            'relation_type': rel.relation_type
        })

    # Children
    children = []
    for rel in member.children_relations:
        c = rel.child
        children.append({
            'member_id': c.member_id, 'name': c.name, 'gender': c.gender,
            'birth_date': _format_date(c.birth_date),
            'death_date': _format_date(c.death_date),
            'generation': c.generation,
            'relation_type': rel.relation_type
        })

    # Spouses
    spouses = []
    for m in member.marriages_as_husband:
        spouses.append({
            'member_id': m.wife.member_id, 'name': m.wife.name,
            'gender': m.wife.gender,
            'birth_date': _format_date(m.wife.birth_date),
            'death_date': _format_date(m.wife.death_date),
            'generation': m.wife.generation,
            'marriage_date': m.marriage_date.isoformat() if m.marriage_date else None
        })
    for m in member.marriages_as_wife:
        spouses.append({
            'member_id': m.husband.member_id, 'name': m.husband.name,
            'gender': m.husband.gender,
            'birth_date': _format_date(m.husband.birth_date),
            'death_date': _format_date(m.husband.death_date),
            'generation': m.husband.generation,
            'marriage_date': m.marriage_date.isoformat() if m.marriage_date else None
        })

    return jsonify({
        'member_id': member.member_id,
        'family_id': member.family_id,
        'name': member.name,
        'gender': member.gender,
        'birth_date': member.birth_date.isoformat() if member.birth_date else None,
        'death_date': member.death_date.isoformat() if member.death_date else None,
        'generation': member.generation,
        'biography': member.biography,
        'parents': parents,
        'children': children,
        'spouses': spouses
    })

@member_bp.route('/<int:member_id>', methods=['PUT'])
@login_required
def update_member(member_id):
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    family = check_family_access(member.family_id)
    if not family:
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    if 'name' in data and data['name'].strip():
        member.name = data['name'].strip()
    if 'gender' in data:
        member.gender = data['gender']
    if 'birth_date' in data:
        member.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date() if data['birth_date'] else None
    if 'death_date' in data:
        member.death_date = datetime.strptime(data['death_date'], '%Y-%m-%d').date() if data['death_date'] else None
    if 'generation' in data:
        member.generation = data['generation']
    if 'biography' in data:
        member.biography = data['biography'].strip() or None

    db.session.commit()
    return jsonify({'member_id': member.member_id, 'name': member.name})

@member_bp.route('/<int:member_id>', methods=['DELETE'])
@login_required
def delete_member(member_id):
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    family = check_family_access(member.family_id)
    if not family:
        return jsonify({'error': 'Access denied'}), 403

    # Clean up relations first
    FamilyRelation.query.filter(
        (FamilyRelation.parent_id == member_id) | (FamilyRelation.child_id == member_id)
    ).delete()
    Marriage.query.filter(
        (Marriage.husband_id == member_id) | (Marriage.wife_id == member_id)
    ).delete()

    db.session.delete(member)
    db.session.commit()
    return jsonify({'message': 'Member deleted'})

@member_bp.route('/<int:member_id>/ancestors', methods=['GET'])
@login_required
def get_ancestors(member_id):
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    family = check_family_access(member.family_id)
    if not family:
        return jsonify({'error': 'Access denied'}), 403

    max_depth = request.args.get('depth', 15, type=int)
    result = db.session.execute(db.text("""
        WITH RECURSIVE ancestors AS (
            SELECT fr.parent_id, m.name, m.gender, m.birth_date, m.death_date,
                   m.generation, 1 AS depth, CAST(fr.parent_id AS TEXT) AS path
            FROM family_relations fr
            JOIN members m ON fr.parent_id = m.member_id
            WHERE fr.child_id = :member_id
            UNION ALL
            SELECT fr.parent_id, m.name, m.gender, m.birth_date, m.death_date,
                   m.generation, a.depth + 1, a.path || ',' || fr.parent_id
            FROM family_relations fr
            JOIN members m ON fr.parent_id = m.member_id
            JOIN ancestors a ON fr.child_id = a.parent_id
            WHERE a.depth < :max_depth
              AND ',' || a.path || ',' NOT LIKE '%,' || fr.parent_id || ',%'
        )
        SELECT * FROM ancestors ORDER BY depth
    """), {'member_id': member_id, 'max_depth': max_depth})

    ancestors = [{
        'member_id': row.parent_id, 'name': row.name, 'gender': row.gender,
        'birth_date': _format_date(row.birth_date),
        'death_date': _format_date(row.death_date),
        'generation': row.generation, 'depth': row.depth
    } for row in result]

    return jsonify({'member_id': member_id, 'ancestors': ancestors, 'count': len(ancestors)})

@member_bp.route('/<int:member_id>/descendants', methods=['GET'])
@login_required
def get_descendants(member_id):
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    family = check_family_access(member.family_id)
    if not family:
        return jsonify({'error': 'Access denied'}), 403

    max_depth = request.args.get('depth', 15, type=int)
    result = db.session.execute(db.text("""
        WITH RECURSIVE descendants AS (
            SELECT fr.child_id, m.name, m.gender, m.birth_date, m.death_date,
                   m.generation, 1 AS depth
            FROM family_relations fr
            JOIN members m ON fr.child_id = m.member_id
            WHERE fr.parent_id = :member_id
            UNION ALL
            SELECT fr.child_id, m.name, m.gender, m.birth_date, m.death_date,
                   m.generation, d.depth + 1
            FROM family_relations fr
            JOIN members m ON fr.child_id = m.member_id
            JOIN descendants d ON fr.parent_id = d.child_id
            WHERE d.depth < :max_depth
        )
        SELECT * FROM descendants ORDER BY depth
    """), {'member_id': member_id, 'max_depth': max_depth})

    descendants = [{
        'member_id': row.child_id, 'name': row.name, 'gender': row.gender,
        'birth_date': _format_date(row.birth_date),
        'death_date': _format_date(row.death_date),
        'generation': row.generation, 'depth': row.depth
    } for row in result]

    return jsonify({'member_id': member_id, 'descendants': descendants, 'count': len(descendants)})

@member_bp.route('/<int:member_id>/children', methods=['GET'])
@login_required
def get_children(member_id):
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    family = check_family_access(member.family_id)
    if not family:
        return jsonify({'error': 'Access denied'}), 403

    children = []
    for rel in member.children_relations:
        c = rel.child
        children.append({
            'member_id': c.member_id, 'name': c.name, 'gender': c.gender,
            'birth_date': c.birth_date.isoformat() if c.birth_date else None,
            'generation': c.generation
        })
    return jsonify({'member_id': member_id, 'children': children})


def _build_tree_node(member):
    """Build a tree node with children recursively."""
    node = {
        'member_id': member.member_id,
        'name': member.name,
        'gender': member.gender,
        'generation': member.generation,
        'birth_date': _format_date(member.birth_date),
        'death_date': _format_date(member.death_date),
        'children': []
    }
    for rel in member.children_relations:
        node['children'].append(_build_tree_node(rel.child))
    return node


def _build_ancestor_tree(member, max_depth, current_depth=0):
    """Build ancestor tree bottom-up."""
    node = {
        'member_id': member.member_id,
        'name': member.name,
        'gender': member.gender,
        'generation': member.generation,
        'birth_date': _format_date(member.birth_date),
        'death_date': _format_date(member.death_date),
        'children': []
    }
    if current_depth < max_depth:
        for rel in member.parent_relations:
            node['children'].append(_build_ancestor_tree(rel.parent, max_depth, current_depth + 1))
    return node


@member_bp.route('/<int:member_id>/tree', methods=['GET'])
@login_required
def get_member_tree(member_id):
    """Return complete tree structure for visualization."""
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404
    family = check_family_access(member.family_id)
    if not family:
        return jsonify({'error': 'Access denied'}), 403

    direction = request.args.get('direction', 'descendants')
    max_depth = request.args.get('depth', 5, type=int)

    if direction == 'ancestors':
        tree_data = _build_ancestor_tree(member, max_depth)
    else:
        tree_data = _build_tree_node(member)
        # For descendants, we limit depth in _build_tree_node (all recursive)
        # Add artificial depth limiting
        def limit_depth(node, depth):
            if depth <= 0:
                node['children'] = []
            else:
                for child in node['children']:
                    limit_depth(child, depth - 1)
        if max_depth > 0:
            limit_depth(tree_data, max_depth)

    return jsonify(tree_data)


@member_bp.route('/search', methods=['GET'])
@login_required
def search_all_members():
    """Search members across ALL families owned by the current user."""
    q = request.args.get('q', '').strip()
    if not q or len(q) < 1:
        return jsonify({'members': [], 'total': 0})

    limit = request.args.get('limit', 20, type=int)
    family_ids = [f.family_id for f in Family.query.filter_by(user_id=g.current_user.user_id).all()]

    if not family_ids:
        return jsonify({'members': [], 'total': 0})

    query = Member.query.filter(
        Member.family_id.in_(family_ids),
        Member.name.contains(q)
    ).order_by(Member.name).limit(limit)

    members = [{
        'member_id': m.member_id,
        'name': m.name,
        'gender': m.gender,
        'generation': m.generation,
        'family_id': m.family_id,
        'birth_date': _format_date(m.birth_date),
        'death_date': _format_date(m.death_date)
    } for m in query.all()]

    return jsonify({'members': members, 'total': len(members)})
