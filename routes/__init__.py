from routes.auth_routes import auth_bp
from routes.family_routes import family_bp
from routes.member_routes import member_bp
from routes.relation_routes import relation_bp
from routes.stats_routes import stats_bp
from routes.utility_routes import utility_bp
from routes.admin_routes import admin_bp
from routes.import_routes import import_bp

def register_routes(app):
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(family_bp, url_prefix='/api/families')
    app.register_blueprint(member_bp, url_prefix='/api/members')
    app.register_blueprint(relation_bp, url_prefix='/api/relations')
    app.register_blueprint(stats_bp, url_prefix='/api')
    app.register_blueprint(utility_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')
    app.register_blueprint(import_bp, url_prefix='/api')
