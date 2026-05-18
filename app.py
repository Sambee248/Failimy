from flask import Flask, render_template, request
from flask_cors import CORS
from config import Config
from models import db
from routes import register_routes

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    db.init_app(app)
    register_routes(app)

    # --- Frontend routes ---
    @app.route('/')
    def index():
        return render_template('dashboard.html')

    @app.route('/login')
    def login_page():
        return render_template('login.html', hide_sidebar=True)

    @app.route('/register')
    def register_page():
        return render_template('register.html', hide_sidebar=True)

    @app.route('/dashboard')
    def dashboard_page():
        return render_template('dashboard.html')

    @app.route('/families')
    def families_page():
        return render_template('families.html')

    @app.route('/families/<int:family_id>/members')
    def member_list_page(family_id):
        return render_template('member_list.html', family_id=family_id)

    @app.route('/families/<int:family_id>/tree')
    def family_tree_page(family_id):
        return render_template('family_tree.html', family_id=family_id)

    @app.route('/members/<int:member_id>')
    def member_detail_page(member_id):
        return render_template('member_detail.html', member_id=member_id)

    @app.route('/members/new')
    def member_new_page():
        family_id = request.args.get('family_id', type=int)
        return render_template('member_form.html', family_id=family_id)

    @app.route('/members/<int:member_id>/edit')
    def member_edit_page(member_id):
        return render_template('member_form.html', member_id=member_id)

    @app.route('/relation/path')
    def relation_path_page():
        return render_template('relation_path.html')

    @app.route('/families/<int:family_id>/stats')
    def stats_page(family_id):
        return render_template('stats.html', family_id=family_id)

    @app.route('/test-search')
    def test_search_page():
        return render_template('test_search.html')

    @app.route('/families/<int:family_id>/import')
    def import_page(family_id):
        return render_template('import_data.html', family_id=family_id)

    @app.route('/admin')
    def admin_page():
        return render_template('admin.html')

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
