"""Bulk import routes - CSV import for members, relations, and marriages."""
import csv
import io
import time
from datetime import datetime
from flask import Blueprint, request, jsonify, g, Response
from models import db, Family, Member, FamilyRelation, Marriage
from auth import login_required

import_bp = Blueprint('import_data', __name__)

# Expected CSV headers
MEMBER_HEADERS = ['name', 'gender', 'birth_date', 'death_date', 'generation', 'biography', 'ref_id']
RELATION_HEADERS = ['parent_ref_id', 'child_ref_id', 'relation_type']
MARRIAGE_HEADERS = ['husband_ref_id', 'wife_ref_id', 'marriage_date', 'divorce_date']

DATE_FORMATS = [
    '%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d',
    '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S',
    '%Y年%m月%d日', '%d/%m/%Y', '%m/%d/%Y',
]


def _parse_date(val):
    """Try multiple date formats. Returns date object or None."""
    if not val or not str(val).strip():
        return None
    val = str(val).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {val}")


def _parse_csv(file_storage):
    """Parse a CSV file from Flask FileStorage. Returns (list_of_dicts, error)."""
    try:
        raw = file_storage.read()
        # Handle UTF-8 BOM
        if raw[:3] == b'\xef\xbb\xbf':
            raw = raw[3:]
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        try:
            text = raw.decode('gbk')
        except Exception:
            return None, '文件编码错误，请使用 UTF-8 或 GBK 编码'
    except Exception as e:
        return None, f'文件读取失败: {str(e)}'

    try:
        reader = csv.DictReader(io.StringIO(text))
        rows = [row for row in reader]
    except Exception as e:
        return None, f'CSV 解析失败: {str(e)}'

    return rows, None


def _validate_headers(rows, expected_headers, file_label):
    """Validate CSV headers exist (case-insensitive, whitespace-tolerant)."""
    if not rows:
        return f'{file_label}: 文件为空'
    headers = [k.strip().lower() for k in rows[0].keys()]
    missing = [h for h in expected_headers if h not in headers]
    if missing:
        return f'{file_label}: 缺少列: {", ".join(missing)}，需要: {", ".join(expected_headers)}'
    return None


def _validate_member_rows(rows):
    """Validate member rows. Returns list of (row_index, error_message)."""
    errors = []
    ref_ids_seen = set()
    for i, row in enumerate(rows):
        line = i + 2  # header is line 1
        name = (row.get('name') or '').strip()
        gender = (row.get('gender') or '').strip().upper()
        ref_id = (row.get('ref_id') or '').strip()

        if not name:
            errors.append((line, f'第{line}行: 姓名不能为空'))
        if gender not in ('M', 'F'):
            errors.append((line, f'第{line}行: 性别必须为 M 或 F，当前值: "{gender}"'))
        if not ref_id:
            errors.append((line, f'第{line}行: ref_id 不能为空'))
        elif ref_id in ref_ids_seen:
            errors.append((line, f'第{line}行: ref_id "{ref_id}" 重复'))
        ref_ids_seen.add(ref_id)

        # Optional: validate dates if provided
        birth = (row.get('birth_date') or '').strip()
        death = (row.get('death_date') or '').strip()
        gen = (row.get('generation') or '').strip()

        if birth:
            try:
                _parse_date(birth)
            except ValueError as e:
                errors.append((line, str(e)))
        if death:
            try:
                _parse_date(death)
            except ValueError as e:
                errors.append((line, str(e)))
        if gen:
            try:
                int(gen)
            except ValueError:
                errors.append((line, f'第{line}行: 世代必须为数字，当前值: "{gen}"'))

    return errors


def _hash_csv_rows(rows):
    """Normalize keys to lowercase, strip whitespace from keys and values."""
    data = []
    for row in rows:
        cleaned = {k.strip().lower(): (v.strip() if v else '') for k, v in row.items()}
        data.append(cleaned)
    return data, len(data)


@import_bp.route('/families/<int:family_id>/import/template', methods=['GET'])
@login_required
def download_template(family_id):
    """Download a template CSV with correct headers and example data."""
    family = Family.query.filter_by(family_id=family_id, user_id=g.current_user.user_id).first()
    if not family:
        return jsonify({'error': 'Family not found'}), 404

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(MEMBER_HEADERS)
    writer.writerow(['张三', 'M', '1950-01-01', '2020-12-31', '1', '族长', 'm001'])
    writer.writerow(['李四', 'F', '1952-05-15', '', '1', '', 'm002'])
    writer.writerow(['张小明', 'M', '1975-08-20', '', '2', '', 'm003'])
    content = ('﻿' + output.getvalue()).encode('utf-8')
    output.close()

    return Response(
        content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=import_template.csv'}
    )


@import_bp.route('/families/<int:family_id>/import/preview', methods=['POST'])
@login_required
def preview_import(family_id):
    """Upload and preview CSV files before import."""
    family = Family.query.filter_by(family_id=family_id, user_id=g.current_user.user_id).first()
    if not family:
        return jsonify({'error': 'Family not found'}), 404

    result = {'members': None, 'relations': None, 'marriages': None, 'errors': []}

    # Parse members CSV (required)
    if 'members_file' not in request.files:
        return jsonify({'error': '请上传成员 CSV 文件 (members_file)'}), 400

    members_rows, err = _parse_csv(request.files['members_file'])
    if err:
        return jsonify({'error': err}), 400

    header_err = _validate_headers(members_rows, MEMBER_HEADERS, '成员文件')
    if header_err:
        return jsonify({'error': header_err}), 400

    members_data, count = _hash_csv_rows(members_rows)

    validation_errors = _validate_member_rows(members_data)
    if validation_errors:
        result['errors'].extend([e[1] for e in validation_errors[:20]])
        if len(validation_errors) > 20:
            result['errors'].append(f'... 还有 {len(validation_errors) - 20} 个错误')

    result['members'] = {
        'count': count,
        'preview': members_data[:5],
        'columns': MEMBER_HEADERS,
    }

    # Parse relations CSV (optional)
    if 'relations_file' in request.files and request.files['relations_file'].filename:
        rel_rows, err = _parse_csv(request.files['relations_file'])
        if err:
            result['errors'].append(f'关系文件: {err}')
        else:
            header_err = _validate_headers(rel_rows, RELATION_HEADERS, '关系文件')
            if header_err:
                result['errors'].append(header_err)
            else:
                rel_data, rel_count = _hash_csv_rows(rel_rows)
                result['relations'] = {
                    'count': rel_count,
                    'preview': rel_data[:5],
                    'columns': RELATION_HEADERS,
                }

    # Parse marriages CSV (optional)
    if 'marriages_file' in request.files and request.files['marriages_file'].filename:
        mar_rows, err = _parse_csv(request.files['marriages_file'])
        if err:
            result['errors'].append(f'婚姻文件: {err}')
        else:
            header_err = _validate_headers(mar_rows, MARRIAGE_HEADERS, '婚姻文件')
            if header_err:
                result['errors'].append(header_err)
            else:
                mar_data, mar_count = _hash_csv_rows(mar_rows)
                result['marriages'] = {
                    'count': mar_count,
                    'preview': mar_data[:5],
                    'columns': MARRIAGE_HEADERS,
                }

    return jsonify(result)


@import_bp.route('/families/<int:family_id>/import/execute', methods=['POST'])
@login_required
def execute_import(family_id):
    """Execute bulk import from uploaded CSV files."""
    family = Family.query.filter_by(family_id=family_id, user_id=g.current_user.user_id).first()
    if not family:
        return jsonify({'error': 'Family not found'}), 404

    if 'members_file' not in request.files:
        return jsonify({'error': '请上传成员 CSV 文件'}), 400

    # Parse members
    members_rows, err = _parse_csv(request.files['members_file'])
    if err:
        return jsonify({'error': err}), 400

    header_err = _validate_headers(members_rows, MEMBER_HEADERS, '成员文件')
    if header_err:
        return jsonify({'error': header_err}), 400

    members_data, _ = _hash_csv_rows(members_rows)

    validation_errors = _validate_member_rows(members_data)
    if validation_errors:
        return jsonify({
            'error': f'数据验证失败，共 {len(validation_errors)} 个错误',
            'details': [e[1] for e in validation_errors[:10]]
        }), 400

    # Parse optional relations
    relations_data = []
    if 'relations_file' in request.files and request.files['relations_file'].filename:
        rel_rows, err = _parse_csv(request.files['relations_file'])
        if err:
            return jsonify({'error': f'关系文件: {err}'}), 400
        relations_data, _ = _hash_csv_rows(rel_rows)

    # Parse optional marriages
    marriages_data = []
    if 'marriages_file' in request.files and request.files['marriages_file'].filename:
        mar_rows, err = _parse_csv(request.files['marriages_file'])
        if err:
            return jsonify({'error': f'婚姻文件: {err}'}), 400
        marriages_data, _ = _hash_csv_rows(mar_rows)

    t_start = time.time()

    try:
        # Performance PRAGMAs for SQLite
        is_sqlite = 'sqlite' in db.engine.url.drivername
        if is_sqlite:
            db.session.execute(db.text('PRAGMA journal_mode=WAL'))
            db.session.execute(db.text('PRAGMA synchronous=OFF'))
            db.session.execute(db.text('PRAGMA cache_size=100000'))
            db.session.execute(db.text('PRAGMA temp_store=MEMORY'))

        # Bulk insert members
        BATCH = 5000
        for i in range(0, len(members_data), BATCH):
            batch = members_data[i:i + BATCH]
            mappings = []
            for row in batch:
                birth = _parse_date(row.get('birth_date') or '')
                death = _parse_date(row.get('death_date') or '')
                gen = int(row.get('generation')) if (row.get('generation') or '').strip() else 1
                mappings.append({
                    'family_id': family_id,
                    'name': row['name'].strip(),
                    'gender': row['gender'].strip().upper(),
                    'birth_date': birth,
                    'death_date': death,
                    'generation': gen,
                    'biography': (row.get('biography') or '').strip() or None,
                    'created_by': g.current_user.user_id,
                })
            db.session.bulk_insert_mappings(Member, mappings)

        db.session.flush()

        # Fetch newly inserted members to build ref_id → member_id map.
        # SQLite assigns autoincrement IDs sequentially, so the newest N members
        # (ordered by member_id DESC) correspond to our insertions in reverse order.
        new_members = Member.query.filter_by(family_id=family_id) \
            .order_by(Member.member_id.desc()).limit(len(members_data)).all()
        new_members = list(reversed(new_members))  # now in insertion order

        ref_to_id = {}
        for idx, row in enumerate(members_data):
            if idx < len(new_members):
                ref_to_id[row['ref_id'].strip()] = new_members[idx].member_id

        # Insert relations
        rel_inserted = 0
        if relations_data:
            rel_mappings = []
            for row in relations_data:
                parent_ref = (row.get('parent_ref_id') or '').strip()
                child_ref = (row.get('child_ref_id') or '').strip()
                rel_type = (row.get('relation_type') or 'biological').strip()

                parent_id = ref_to_id.get(parent_ref)
                child_id = ref_to_id.get(child_ref)
                if not parent_id:
                    raise ValueError(f'关系引用错误: 找不到 parent_ref_id="{parent_ref}"')
                if not child_id:
                    raise ValueError(f'关系引用错误: 找不到 child_ref_id="{child_ref}"')
                if parent_id == child_id:
                    raise ValueError(f'亲子关系错误: parent 和 child 指向同一人 (ref_id="{parent_ref}")')

                rel_mappings.append({
                    'parent_id': parent_id,
                    'child_id': child_id,
                    'relation_type': rel_type if rel_type in ('biological', 'adopted') else 'biological',
                })
                rel_inserted += 1

            if rel_mappings:
                db.session.bulk_insert_mappings(FamilyRelation, rel_mappings)

        # Insert marriages
        mar_inserted = 0
        if marriages_data:
            mar_mappings = []
            for row in marriages_data:
                husband_ref = (row.get('husband_ref_id') or '').strip()
                wife_ref = (row.get('wife_ref_id') or '').strip()
                mar_date = _parse_date(row.get('marriage_date') or '')
                div_date = _parse_date(row.get('divorce_date') or '')

                husband_id = ref_to_id.get(husband_ref)
                wife_id = ref_to_id.get(wife_ref)
                if not husband_id:
                    raise ValueError(f'婚姻引用错误: 找不到 husband_ref_id="{husband_ref}"')
                if not wife_id:
                    raise ValueError(f'婚姻引用错误: 找不到 wife_ref_id="{wife_ref}"')
                if husband_id == wife_id:
                    raise ValueError(f'婚姻错误: 夫妻指向同一人 (ref_id="{husband_ref}")')

                mar_mappings.append({
                    'husband_id': husband_id,
                    'wife_id': wife_id,
                    'marriage_date': mar_date,
                    'divorce_date': div_date,
                })
                mar_inserted += 1

            if mar_mappings:
                db.session.bulk_insert_mappings(Marriage, mar_mappings)

        db.session.commit()

        elapsed = round(time.time() - t_start, 2)
        return jsonify({
            'success': True,
            'members_inserted': len(members_data),
            'relations_inserted': rel_inserted,
            'marriages_inserted': mar_inserted,
            'elapsed_seconds': elapsed,
            'records_per_second': round(len(members_data) / elapsed) if elapsed > 0 else 0,
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'导入失败: {str(e)}'}), 500

    finally:
        # Restore PRAGMAs
        if is_sqlite:
            try:
                db.session.execute(db.text('PRAGMA journal_mode=DELETE'))
                db.session.execute(db.text('PRAGMA synchronous=NORMAL'))
            except Exception:
                pass
