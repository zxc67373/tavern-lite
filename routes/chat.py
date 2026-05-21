import logging
import json
from flask import Blueprint, render_template, request, redirect, url_for, current_app, Response, flash
from services.llm_service import load_settings as load_settings_from_service

logger = logging.getLogger('tavern-lite')

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chat/<character_id>')
def chat(character_id):
    logger.info(f"[ChatRoute] GET /chat/{character_id}")
    from services.character_service import get_character
    from services.chat_service import list_chats_by_character, create_chat

    character = get_character(character_id, current_app.config['CHARACTERS_DIR'])
    if not character:
        logger.warning(f"[ChatRoute] character not found: {character_id}")
        flash('角色不存在', 'error')
        return redirect(url_for('character.index'))

    chats = list_chats_by_character(character_id, current_app.config['CHATS_DIR'])

    # 默认加载最新对话（如果有）
    current_chat = chats[0] if chats else None

    if not current_chat:
        logger.info(f"[ChatRoute] creating new chat for character: {character_id}")
        current_chat = create_chat(character_id, character, current_app.config['CHATS_DIR'])

    logger.info(f"[ChatRoute] rendered chat page, chat: {current_chat['id']}, messages: {len(current_chat['messages'])}")
    return render_template('chat.html', character=character, chat=current_chat, chats=chats)


@chat_bp.route('/chat/<character_id>/new')
def new_chat(character_id):
    """创建全新对话，忽略已有对话"""
    logger.info(f"[ChatRoute] GET /chat/{character_id}/new - creating new chat")
    from services.character_service import get_character
    from services.chat_service import create_chat

    character = get_character(character_id, current_app.config['CHARACTERS_DIR'])
    if not character:
        logger.warning(f"[ChatRoute] character not found: {character_id}")
        flash('角色不存在', 'error')
        return redirect(url_for('character.index'))

    # 强制创建新对话
    current_chat = create_chat(character_id, character, current_app.config['CHATS_DIR'])
    chats = list_chats_by_character(character_id, current_app.config['CHATS_DIR'])

    logger.info(f"[ChatRoute] new chat created: {current_chat['id']}")
    return render_template('chat.html', character=character, chat=current_chat, chats=chats)


@chat_bp.route('/chat/<character_id>/history')
def chat_history(character_id):
    logger.info(f"[ChatRoute] GET /chat/{character_id}/history")
    from services.character_service import get_character
    from services.chat_service import list_chats_by_character

    character = get_character(character_id, current_app.config['CHARACTERS_DIR'])
    if not character:
        logger.warning(f"[ChatRoute] character not found: {character_id}")
        return {'error': '角色不存在'}, 404

    chats = list_chats_by_character(character_id, current_app.config['CHATS_DIR'])
    logger.info(f"[ChatRoute] returned {len(chats)} chats for character {character_id}")
    return {'chats': [{'id': c['id'], 'title': c['title'], 'updated_at': c['updated_at']} for c in chats]}


@chat_bp.route('/chat/session/<chat_id>')
def load_session(chat_id):
    logger.info(f"[ChatRoute] GET /chat/session/{chat_id}")
    from services.chat_service import get_chat
    from services.character_service import get_character

    chat = get_chat(chat_id, current_app.config['CHATS_DIR'])
    if not chat:
        logger.warning(f"[ChatRoute] chat not found: {chat_id}")
        flash('对话不存在', 'error')
        return redirect(url_for('character.index'))

    character = get_character(chat['character_id'], current_app.config['CHARACTERS_DIR'])
    chats = list_chats_by_character(chat['character_id'], current_app.config['CHATS_DIR'])

    logger.info(f"[ChatRoute] loaded session: {chat_id}, messages: {len(chat['messages'])}")
    return render_template('chat.html', character=character, chat=chat, chats=chats)


def list_chats_by_character(character_id, chats_dir):
    from services.chat_service import list_chats_by_character as _list
    return _list(character_id, chats_dir)


@chat_bp.route('/chat/<chat_id>/send', methods=['POST'])
def send_message(chat_id):
    logger.info(f"[ChatRoute] POST /chat/{chat_id}/send")
    from services.chat_service import get_chat, append_message
    from services.llm_service import chat_completion
    from services.character_service import get_character

    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    if not user_message:
        logger.warning(f"[ChatRoute] empty message received")
        return {'error': '消息不能为空'}, 400

    chat = get_chat(chat_id, current_app.config['CHATS_DIR'])
    if not chat:
        logger.warning(f"[ChatRoute] chat not found: {chat_id}")
        return {'error': '对话不存在'}, 404

    logger.info(f"[ChatRoute] user message: {user_message[:50]}...")
    append_message(chat_id, 'user', user_message, current_app.config['CHATS_DIR'])
    chat = get_chat(chat_id, current_app.config['CHATS_DIR'])
    settings = load_settings_from_service(current_app.config['SETTINGS_FILE'])
    chats_dir = current_app.config['CHATS_DIR']

    def generate():
        full_content = ''
        try:
            logger.info(f"[ChatRoute] calling LLM API, messages count: {len(chat['messages'])}")
            config = settings.get('api_configs', [])
            current_id = settings.get('current_config')
            use_stream = True
            for c in config:
                if c.get('id') == current_id:
                    use_stream = c.get('stream', True)
                    break

            logger.info(f"[ChatRoute] using stream mode: {use_stream}")

            if use_stream:
                # 流式输出
                response = chat_completion(chat['messages'], settings, stream=True)
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        full_content += content
                        yield f"data: {json.dumps({'content': content})}\n\n"
            else:
                # 非流式一次性返回
                full_content = chat_completion(chat['messages'], settings, stream=False)
                yield f"data: {json.dumps({'content': full_content})}\n\n"

            logger.info(f"[ChatRoute] LLM response complete, total length: {len(full_content)}")
            append_message(chat_id, 'assistant', full_content, chats_dir)
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.error(f"[ChatRoute] LLM API error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@chat_bp.route('/chat/<chat_id>/delete', methods=['POST'])
def delete_chat(chat_id):
    logger.info(f"[ChatRoute] POST /chat/{chat_id}/delete")
    from services.chat_service import delete_chat
    delete_chat(chat_id, current_app.config['CHATS_DIR'])
    logger.info(f"[ChatRoute] chat deleted: {chat_id}")
    flash('对话已删除', 'success')
    return redirect(url_for('character.index'))


def load_settings():
    from services.llm_service import load_settings
    return load_settings(current_app.config['SETTINGS_FILE'])