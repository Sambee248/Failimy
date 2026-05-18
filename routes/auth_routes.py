import bcrypt
from flask import Blueprint, request, jsonify, g
from models import db, User
from auth import create_token, login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip()

    if not username or len(username) < 2:
        return jsonify({'error': 'Username must be at least 2 characters'}), 400
    if not password or len(password) < 4:
        return jsonify({'error': 'Password must be at least 4 characters'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(username=username, password_hash=password_hash, email=email or None)
    db.session.add(user)
    db.session.commit()

    token = create_token(user.user_id)
    return jsonify({
        'message': 'Registration successful',
        'token': token,
        'user': {'user_id': user.user_id, 'username': user.username, 'is_admin': user.is_admin}
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'Invalid username or password'}), 401

    if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({'error': 'Invalid username or password'}), 401

    token = create_token(user.user_id)
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {'user_id': user.user_id, 'username': user.username, 'is_admin': user.is_admin}
    })

@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    user = g.current_user
    return jsonify({
        'user_id': user.user_id,
        'username': user.username,
        'email': user.email,
        'created_at': user.created_at.isoformat() if user.created_at else None
    })
