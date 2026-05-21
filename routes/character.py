import logging
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash

logger = logging.getLogger('tavern-lite')

character_bp = Blueprint('character', __name__)


@character_bp.route('/')
def index():
    logger.info("[CharacterRoute] GET / - index page")
    characters = _list_characters()
    logger.info(f"[CharacterRoute] rendered index with {len(characters)} characters")
    return render_template('index.html', characters=characters)


@character_bp.route('/character/new')
def new_character():
    logger.info("[CharacterRoute] GET /character/new - new character form")
    return render_template('character_edit.html', character=None)


@character_bp.route('/character', methods=['POST'])
def create_character():
    logger.info("[CharacterRoute] POST /character - creating new character")
    from services.character_service import create_character
    data = request.form.to_dict()
    logger.info(f"[CharacterRoute] create data: name={data.get('name')}")
    char = create_character(data, current_app.config['CHARACTERS_DIR'])
    logger.info(f"[CharacterRoute] character created: {char['id']} - {char['name']}")
    flash('角色创建成功', 'success')
    return redirect(url_for('character.index'))


@character_bp.route('/character/<char_id>/edit')
def edit_character(char_id):
    logger.info(f"[CharacterRoute] GET /character/{char_id}/edit")
    char = _get_character(char_id)
    if not char:
        logger.warning(f"[CharacterRoute] character not found: {char_id}")
        flash('角色不存在', 'error')
        return redirect(url_for('character.index'))
    logger.info(f"[CharacterRoute] editing character: {char.get('name')}")
    return render_template('character_edit.html', character=char)


@character_bp.route('/character/<char_id>', methods=['POST'])
def update_character(char_id):
    logger.info(f"[CharacterRoute] POST /character/{char_id} - updating character")
    from services.character_service import update_character
    data = request.form.to_dict()
    logger.info(f"[CharacterRoute] update data: name={data.get('name')}")
    char = update_character(char_id, data, current_app.config['CHARACTERS_DIR'])
    if not char:
        logger.warning(f"[CharacterRoute] character not found for update: {char_id}")
        flash('角色不存在', 'error')
        return redirect(url_for('character.index'))
    logger.info(f"[CharacterRoute] character updated: {char_id} - {char.get('name')}")
    flash('角色更新成功', 'success')
    return redirect(url_for('character.index'))


@character_bp.route('/character/<char_id>/delete', methods=['POST'])
def delete_character(char_id):
    logger.info(f"[CharacterRoute] POST /character/{char_id}/delete")
    from services.character_service import delete_character
    delete_character(char_id, current_app.config['CHARACTERS_DIR'])
    logger.info(f"[CharacterRoute] character deleted: {char_id}")
    flash('角色已删除', 'success')
    return redirect(url_for('character.index'))


def _list_characters():
    from services.character_service import list_characters
    return list_characters(current_app.config['CHARACTERS_DIR'])


def _get_character(char_id):
    from services.character_service import get_character
    return get_character(char_id, current_app.config['CHARACTERS_DIR'])