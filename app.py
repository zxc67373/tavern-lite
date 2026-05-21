import os
import argparse
import logging
from flask import Flask

# 配置日志 - 输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('tavern-lite')


def create_app():
    app = Flask(__name__)
    app.secret_key = 'tavern-lite-secret-key-change-in-production'
    app.config['DATA_DIR'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    app.config['CHARACTERS_DIR'] = os.path.join(app.config['DATA_DIR'], 'characters')
    app.config['CHATS_DIR'] = os.path.join(app.config['DATA_DIR'], 'chats')
    app.config['SETTINGS_FILE'] = os.path.join(app.config['DATA_DIR'], 'settings.json')
    app.config['STORIES_DIR'] = os.path.join(app.config['DATA_DIR'], 'stories')

    os.makedirs(app.config['CHARACTERS_DIR'], exist_ok=True)
    os.makedirs(app.config['CHATS_DIR'], exist_ok=True)
    os.makedirs(app.config['STORIES_DIR'], exist_ok=True)

    from routes.character import character_bp
    from routes.chat import chat_bp
    from routes.settings import settings_bp
    from routes.auto_character import auto_character_bp
    from routes.story import story_bp

    app.register_blueprint(character_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(auto_character_bp)
    app.register_blueprint(story_bp)

    logger.info("[App] Flask app created successfully")
    logger.info(f"[App] Data directory: {app.config['DATA_DIR']}")
    logger.info(f"[App] Characters directory: {app.config['CHARACTERS_DIR']}")
    logger.info(f"[App] Chats directory: {app.config['CHATS_DIR']}")
    logger.info(f"[App] Stories directory: {app.config['STORIES_DIR']}")
    logger.info(f"[App] Settings file: {app.config['SETTINGS_FILE']}")

    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8001, help='Port to run the server on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    args = parser.parse_args()

    logger.info(f"[App] Starting server on {args.host}:{args.port}")

    app = create_app()
    app.run(debug=True, host=args.host, port=args.port)