from flask import Blueprint, request, jsonify, g
from models import db, Family, Member
from auth import login_required

stats_bp = Blueprint('stats', __name__)

def check_family_access(family_id):
    family = Family.query.get(family_id)
    if family and (family.user_id == g.current_user.user_id or g.current_user.is_admin):
        return family
    return None

@stats_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    user_id = g.current_user.user_id
    families = Family.query.filter_by(user_id=user_id).all()
    total_members = sum(f.members.count() for f in families)
    total_families = len(families)

    male_count = Member.query.join(Family).filter(
        Family.user_id == user_id, Member.gender == 'M'
    ).count()
    female_count = Member.query.join(Family).filter(
        Family.user_id == user_id, Member.gender == 'F'
    ).count()

    # Recent members
    recent = Member.query.join(Family).filter(Family.user_id == user_id)\
        .order_by(Member.created_at.desc()).limit(10).all()

    return jsonify({
        'total_families': total_families,
        'total_members': total_members,
        'male_count': male_count,
        'female_count': female_count,
        'recent_members': [{
            'member_id': m.member_id,
            'name': m.name,
            'gender': m.gender,
            'family_name': m.family.family_name,
            'generation': m.generation,
            'created_at': m.created_at.isoformat() if m.created_at else None
        } for m in recent]
    })

@stats_bp.route('/families/<int:family_id>/stats', methods=['GET'])
@login_required
def family_stats(family_id):
    family = check_family_access(family_id)
    if not family:
        return jsonify({'error': 'Family not found'}), 404

    total = Member.query.filter_by(family_id=family_id).count()
    male = Member.query.filter_by(family_id=family_id, gender='M').count()
    female = Member.query.filter_by(family_id=family_id, gender='F').count()

    # Generation stats
    gen_stats = db.session.execute(db.text("""
        SELECT generation,
               COUNT(*) AS cnt,
               COUNT(CASE WHEN gender = 'M' THEN 1 END) AS male_cnt,
               COUNT(CASE WHEN gender = 'F' THEN 1 END) AS female_cnt
        FROM members
        WHERE family_id = :family_id
        GROUP BY generation
        ORDER BY generation
    """), {'family_id': family_id}).fetchall()

    # Average lifespan per generation
    lifespan = db.session.execute(db.text("""
        SELECT generation,
               ROUND(AVG(julianday(death_date) - julianday(birth_date)) / 365.25, 1) AS avg_lifespan
        FROM members
        WHERE family_id = :family_id
          AND death_date IS NOT NULL
          AND birth_date IS NOT NULL
        GROUP BY generation
        ORDER BY generation
    """), {'family_id': family_id}).fetchall()

    return jsonify({
        'family_id': family_id,
        'family_name': family.family_name,
        'total_members': total,
        'male_count': male,
        'female_count': female,
        'gender_ratio': round(male / max(female, 1), 2),
        'generations': [{
            'generation': row.generation,
            'count': row.cnt,
            'male': row.male_cnt,
            'female': row.female_cnt
        } for row in gen_stats],
        'avg_lifespan': [{
            'generation': row.generation,
            'avg_lifespan': float(row.avg_lifespan) if row.avg_lifespan else 0
        } for row in lifespan if row.avg_lifespan]
    })


@stats_bp.route('/families/<int:family_id>/unmarried-seniors', methods=['GET'])
@login_required
def unmarried_seniors(family_id):
    """Members over 50 years old (by birth date) who have no spouse."""
    family = check_family_access(family_id)
    if not family:
        return jsonify({'error': 'Family not found'}), 404

    cutoff_year = db.text("date('now', '-50 years')")
    rows = db.session.execute(db.text("""
        SELECT m.member_id, m.name, m.gender, m.birth_date, m.generation,
               CAST((julianday('now') - julianday(m.birth_date)) / 365.25 AS INTEGER) AS age
        FROM members m
        WHERE m.family_id = :fid
          AND m.birth_date IS NOT NULL
          AND m.birth_date <= date('now', '-50 years')
          AND m.death_date IS NULL
          AND m.member_id NOT IN (
              SELECT husband_id FROM marriages WHERE husband_id = m.member_id
              UNION
              SELECT wife_id FROM marriages WHERE wife_id = m.member_id
          )
        ORDER BY age DESC
    """), {'fid': family_id}).fetchall()

    return jsonify({'family_id': family_id, 'total': len(rows), 'members': [{
        'member_id': r.member_id, 'name': r.name, 'gender': r.gender,
        'birth_date': r.birth_date, 'generation': r.generation, 'age': r.age
    } for r in rows]})


@stats_bp.route('/families/<int:family_id>/outliers', methods=['GET'])
@login_required
def outlier_detection(family_id):
    """Detect data anomalies: impossible lifespans, generation mismatches, duplicate names."""
    family = check_family_access(family_id)
    if not family:
        return jsonify({'error': 'Family not found'}), 404

    anomalies = []

    # 1. Members with implausibly long lifespans (> 110 years)
    long_lived = db.session.execute(db.text("""
        SELECT member_id, name, gender, birth_date, death_date,
               CAST((julianday(death_date) - julianday(birth_date)) / 365.25 AS INTEGER) AS age
        FROM members WHERE family_id = :fid AND birth_date IS NOT NULL AND death_date IS NOT NULL
          AND (julianday(death_date) - julianday(birth_date)) / 365.25 > 110
    """), {'fid': family_id}).fetchall()
    for r in long_lived:
        anomalies.append({'type': 'long_lifespan', 'member_id': r.member_id,
                          'name': r.name, 'detail': f'Age {r.age} years ({r.birth_date} - {r.death_date})'})

    # 2. Members with death before birth
    death_before_birth = db.session.execute(db.text("""
        SELECT member_id, name, gender, birth_date, death_date
        FROM members WHERE family_id = :fid AND birth_date IS NOT NULL AND death_date IS NOT NULL
          AND death_date < birth_date
    """), {'fid': family_id}).fetchall()
    for r in death_before_birth:
        anomalies.append({'type': 'death_before_birth', 'member_id': r.member_id,
                          'name': r.name, 'detail': f'Birth {r.birth_date} after death {r.death_date}'})

    # 3. Duplicate names (same name, same gender)
    dup_names = db.session.execute(db.text("""
        SELECT name, gender, COUNT(*) AS cnt, GROUP_CONCAT(member_id) AS ids
        FROM members WHERE family_id = :fid
        GROUP BY name, gender HAVING COUNT(*) > 1
    """), {'fid': family_id}).fetchall()
    for r in dup_names:
        anomalies.append({'type': 'duplicate_name', 'name': r.name,
                          'detail': f'{r.cnt} members ({r.gender}), IDs: {r.ids}'})

    # 4. Generations gap too large (parent-child gen difference > 3)
    gen_gap = db.session.execute(db.text("""
        SELECT fr.parent_id, fr.child_id,
               p.name AS parent_name, p.generation AS parent_gen,
               c.name AS child_name, c.generation AS child_gen
        FROM family_relations fr
        JOIN members p ON p.member_id = fr.parent_id
        JOIN members c ON c.member_id = fr.child_id
        WHERE p.family_id = :fid
          AND ABS(p.generation - c.generation) > 3
    """), {'fid': family_id}).fetchall()
    for r in gen_gap:
        anomalies.append({'type': 'generation_gap', 'member_id': r.child_id,
                          'name': r.child_name,
                          'detail': f'Parent {r.parent_name}(gen {r.parent_gen}) → Child {r.child_name}(gen {r.child_gen}), gap {abs(r.parent_gen - r.child_gen)}'})

    return jsonify({'family_id': family_id, 'total': len(anomalies), 'anomalies': anomalies})
