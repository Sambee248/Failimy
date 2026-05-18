import csv
import io
import os
import shutil
from datetime import datetime
from flask import Blueprint, request, jsonify, g, Response
from models import db, Family, Member, FamilyRelation, Marriage
from auth import login_required

utility_bp = Blueprint('utility', __name__)


def _fmt(v):
    if not v:
        return ''
    if hasattr(v, 'isoformat'):
        return '\t' + v.isoformat()
    return str(v)


def _make_csv_response(lines, filename):
    """Build a CSV response with UTF-8 BOM for Excel compatibility."""
    output = io.StringIO()
    writer = csv.writer(output)
    for line in lines:
        writer.writerow(line)
    # UTF-8 BOM so Excel recognizes the encoding
    content = ('﻿' + output.getvalue()).encode('utf-8')
    output.close()
    return Response(
        content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=' + filename}
    )


def _safe_filename(name):
    """Strip non-ASCII chars for safe Content-Disposition header."""
    return re.sub(r'[^\w\-.]', '_', name)


def _get_db_path():
    """Find the SQLite database file path."""
    candidates = [
        os.path.join(os.getcwd(), 'instance', 'genealogy.db'),
        os.path.join(os.getcwd(), 'genealogy.db'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'genealogy.db'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'genealogy.db'),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return None


@utility_bp.route('/families/<int:family_id>/export/csv', methods=['GET'])
@login_required
def export_family_csv(family_id):
    """Export all members of a family as CSV."""
    family = Family.query.filter_by(family_id=family_id, user_id=g.current_user.user_id).first()
    if not family:
        return jsonify({'error': 'Family not found'}), 404

    members = Member.query.filter_by(family_id=family_id).order_by(Member.generation, Member.name).all()

    rows = [['成员ID', '姓名', '性别', '出生日期', '逝世日期', '世代', '简介', '创建时间']]
    for m in members:
        rows.append([str(m.member_id), m.name, '男' if m.gender == 'M' else '女',
                     _fmt(m.birth_date), _fmt(m.death_date), str(m.generation),
                     m.biography or '', _fmt(m.created_at)])

    return _make_csv_response(rows, 'family_' + str(family_id) + '_members.csv')


@utility_bp.route('/families/<int:family_id>/export/full-csv', methods=['GET'])
@login_required
def export_family_full_csv(family_id):
    """Export members + relations as CSV."""
    family = Family.query.filter_by(family_id=family_id, user_id=g.current_user.user_id).first()
    if not family:
        return jsonify({'error': 'Family not found'}), 404

    members = Member.query.filter_by(family_id=family_id).order_by(Member.member_id).all()

    rows = [['=== 成员数据 ==='], ['成员ID', '姓名', '性别', '出生日期', '逝世日期', '世代', '简介']]
    for m in members:
        rows.append([str(m.member_id), m.name, '男' if m.gender == 'M' else '女',
                     _fmt(m.birth_date), _fmt(m.death_date), str(m.generation),
                     m.biography or ''])

    rows.append([])
    rows.append(['=== 亲子关系 ==='])
    rows.append(['父母ID', '子女ID', '关系类型'])
    member_ids = [m.member_id for m in members]
    if member_ids:
        for r in FamilyRelation.query.filter(
                FamilyRelation.parent_id.in_(member_ids),
                FamilyRelation.child_id.in_(member_ids)).all():
            rel_label = '亲生' if r.relation_type == 'biological' else '收养'
            rows.append([str(r.parent_id), str(r.child_id), rel_label])

    rows.append([])
    rows.append(['=== 婚姻关系 ==='])
    rows.append(['丈夫ID', '妻子ID', '结婚日期', '离婚日期'])
    if member_ids:
        for m in Marriage.query.filter(
                Marriage.husband_id.in_(member_ids),
                Marriage.wife_id.in_(member_ids)).all():
            rows.append([str(m.husband_id), str(m.wife_id), _fmt(m.marriage_date), _fmt(m.divorce_date)])

    return _make_csv_response(rows, 'family_' + str(family_id) + '_full.csv')


@utility_bp.route('/database/backup', methods=['GET'])
@login_required
def database_backup():
    """Download a backup copy of the SQLite database."""
    db_path = _get_db_path()
    if not db_path:
        return jsonify({'error': 'Database file not found'}), 404

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = db_path + '.backup_' + timestamp
    shutil.copy2(db_path, backup_path)

    with open(backup_path, 'rb') as f:
        data = f.read()

    os.remove(backup_path)

    return Response(
        data,
        mimetype='application/octet-stream',
        headers={'Content-Disposition': 'attachment; filename=genealogy_backup_' + timestamp + '.db'}
    )


@utility_bp.route('/families/<int:family_id>/query-ancestors', methods=['GET'])
@login_required
def query_ancestors(family_id):
    """Run and time the recursive ancestor query."""
    family = Family.query.filter_by(family_id=family_id, user_id=g.current_user.user_id).first()
    if not family:
        return jsonify({'error': 'Family not found'}), 404

    member_id = request.args.get('member_id', type=int)
    if not member_id:
        return jsonify({'error': 'member_id query parameter required'}), 400

    depth = request.args.get('depth', 5, type=int)

    t0 = datetime.now()
    rows = db.session.execute(db.text("""
        WITH RECURSIVE ancestors AS (
            SELECT fr.parent_id, fr.child_id, fr.relation_type, 1 AS depth,
                   ',' || fr.parent_id AS path
            FROM family_relations fr WHERE fr.child_id = :mid
            UNION ALL
            SELECT fr.parent_id, fr.child_id, fr.relation_type, a.depth + 1,
                   a.path || ',' || fr.parent_id
            FROM family_relations fr
            JOIN ancestors a ON fr.child_id = a.parent_id
            WHERE a.depth < :depth
              AND ',' || a.path || ',' NOT LIKE '%,' || fr.parent_id || ',%'
        )
        SELECT a.parent_id, a.child_id, a.relation_type, a.depth,
               m.name, m.gender
        FROM ancestors a JOIN members m ON m.member_id = a.parent_id
        ORDER BY a.depth
    """), {'mid': member_id, 'depth': depth}).fetchall()
    elapsed_ms = round((datetime.now() - t0).total_seconds() * 1000, 2)

    result_list = []
    for r in rows:
        result_list.append({
            'parent_id': int(r[0]), 'child_id': int(r[1]),
            'relation_type': str(r[2]), 'depth': int(r[3]),
            'name': str(r[4]), 'gender': str(r[5])
        })

    return jsonify(dict(
        family_id=family_id, member_id=member_id, depth_limit=depth,
        results_count=len(result_list), elapsed_ms=elapsed_ms,
        results=result_list
    ))


@utility_bp.route('/families/<int:family_id>/query-path', methods=['GET'])
@login_required
def query_blood_path(family_id):
    """Run and time the blood path query between two members."""
    family = Family.query.filter_by(family_id=family_id, user_id=g.current_user.user_id).first()
    if not family:
        return jsonify({'error': 'Family not found'}), 404

    person_a = request.args.get('person_a', type=int)
    person_b = request.args.get('person_b', type=int)
    if not person_a or not person_b:
        return jsonify({'error': 'person_a and person_b required'}), 400

    t0 = datetime.now()
    rows = db.session.execute(db.text("""
        WITH RECURSIVE ancestors_a AS (
            SELECT fr.parent_id, 1 AS depth
            FROM family_relations fr WHERE fr.child_id = :pa
            UNION ALL
            SELECT fr.parent_id, a.depth + 1
            FROM family_relations fr JOIN ancestors_a a ON fr.child_id = a.parent_id
            WHERE a.depth < 50
        ),
        ancestors_b AS (
            SELECT fr.parent_id, 1 AS depth
            FROM family_relations fr WHERE fr.child_id = :pb
            UNION ALL
            SELECT fr.parent_id, b.depth + 1
            FROM family_relations fr JOIN ancestors_b b ON fr.child_id = b.parent_id
            WHERE b.depth < 50
        )
        SELECT aa.parent_id AS common_ancestor,
               MIN(aa.depth) AS depth_a, MIN(ab.depth) AS depth_b
        FROM ancestors_a aa JOIN ancestors_b ab ON aa.parent_id = ab.parent_id
        GROUP BY aa.parent_id
        ORDER BY depth_a + depth_b LIMIT 1
    """), {'pa': person_a, 'pb': person_b}).fetchall()
    elapsed_ms = round((datetime.now() - t0).total_seconds() * 1000, 2)

    result_rows = []
    for r in rows:
        result_rows.append(dict(
            common_ancestor=int(r[0]) if r[0] is not None else None,
            depth_a=int(r[1]) if len(r) > 1 and r[1] is not None else 0,
            depth_b=int(r[2]) if len(r) > 2 and r[2] is not None else 0
        ))

    return jsonify(dict(
        family_id=family_id, elapsed_ms=elapsed_ms,
        query_plan=['SQLite recursive CTE via WITH RECURSIVE (2 CTEs + JOIN + GROUP BY)'],
        result=result_rows if result_rows else []
    ))
