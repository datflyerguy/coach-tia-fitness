import os
from flask import Flask

import config as app_config
from .db import register_db, init_db


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["SECRET_KEY"] = app_config.SECRET_KEY
    app.config["JWT_SECRET"] = app_config.JWT_SECRET
    app.config["JWT_ALGORITHM"] = app_config.JWT_ALGORITHM
    app.config["JWT_EXPIRES_SECONDS"] = app_config.JWT_EXPIRES_SECONDS
    app.config["DATABASE_PATH"] = app_config.DATABASE_PATH
    app.config["BRAND_NAME"] = app_config.BRAND_NAME
    app.config["GHL_WEBHOOK_URL"] = app_config.GHL_WEBHOOK_URL

    register_db(app)

    is_first_boot = not os.path.exists(app_config.DATABASE_PATH)
    if is_first_boot:
        init_db(app)
        # Fresh database (e.g. first deploy on a new host) — load the
        # program catalog + demo admin/member accounts the same way local
        # dev does, so the app isn't blank on first visit.
        try:
            with app.app_context():
                import seed
                seed.run()
        except Exception as exc:  # never let seeding crash boot
            app.logger.warning("Seed skipped/failed: %s", exc)

    from .blueprints.public.routes import public_bp
    from .blueprints.member.routes import member_bp
    from .blueprints.admin.routes import admin_bp
    from .blueprints.api.routes import api_bp
    from .blueprints.funnel.routes import funnel_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(member_bp, url_prefix="/app")
    app.register_blueprint(admin_bp, url_prefix="/coach")
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(funnel_bp)

    from .auth import current_user

    @app.context_processor
    def inject_globals():
        return {"brand_name": app_config.BRAND_NAME, "logged_in_user": current_user()}

    return app
