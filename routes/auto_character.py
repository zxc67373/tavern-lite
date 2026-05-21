import logging
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash
from services.auto_character_service import generate_character
from services.character_service import create_character

logger = logging.getLogger('tavern-lite')

auto_character_bp = Blueprint('auto_character', __name__)


@auto_character_bp.route('/character/auto')
def new_auto_character():
    logger.info("[AutoCharacterRoute] GET /character/auto - auto create form")
    return render_template('character_auto.html')


@auto_character_bp.route('/character/auto', methods=['POST'])
def create_auto_character():
    logger.info("[AutoCharacterRoute] POST /character/auto - generating character")
    user_input = request.form.get('description', '').strip()

    if not user_input:
        flash('请输入角色描述', 'error')
        return redirect(url_for('auto_character.new_auto_character'))

    settings_file = current_app.config['SETTINGS_FILE']
    from services.llm_service import load_settings
    settings = load_settings(settings_file)

    try:
        character = generate_character(user_input, settings)
        logger.info(f"[AutoCharacterRoute] character generated: {character.get('name')}")

        # 保存角色
        char = create_character(character, current_app.config['CHARACTERS_DIR'])
        logger.info(f"[AutoCharacterRoute] character saved: {char['id']} - {char['name']}")

        flash(f'角色 "{char["name"]}" 创建成功', 'success')
        return redirect(url_for('character.index'))

    except Exception as e:
        logger.error(f"[AutoCharacterRoute] failed to create character: {e}")
        flash(f'创建失败: {str(e)}', 'error')
        return redirect(url_for('auto_character.new_auto_character'))