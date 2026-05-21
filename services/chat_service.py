import json
import uuid
import os
from datetime import datetime, timezone
import logging

logger = logging.getLogger('tavern-lite')


def _chat_path(chat_id, chats_dir):
    return os.path.join(chats_dir, f'{chat_id}.json')


def list_chats_by_character(character_id, chats_dir):
    logger.info(f"[ChatService] listing chats for character: {character_id}")
    chats = []
    if not os.path.exists(chats_dir):
        logger.warning(f"[ChatService] chats directory does not exist: {chats_dir}")
        return chats
    for fname in os.listdir(chats_dir):
        if fname.endswith('.json'):
            try:
                with open(os.path.join(chats_dir, fname), 'r', encoding='utf-8') as f:
                    chat = json.load(f)
                    if chat.get('character_id') == character_id:
                        chats.append(chat)
            except Exception as e:
                logger.error(f"[ChatService] failed to load chat {fname}: {e}")
    chats.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    logger.info(f"[ChatService] loaded {len(chats)} chats for character {character_id}")
    return chats


def get_chat(chat_id, chats_dir):
    logger.info(f"[ChatService] getting chat: {chat_id}")
    path = _chat_path(chat_id, chats_dir)
    if not os.path.exists(path):
        logger.warning(f"[ChatService] chat not found: {chat_id}")
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            chat = json.load(f)
            logger.info(f"[ChatService] chat loaded: {chat.get('title')} ({chat_id})")
            return chat
    except Exception as e:
        logger.error(f"[ChatService] failed to load chat {chat_id}: {e}")
        return None


def create_chat(character_id, character, chats_dir):
    logger.info(f"[ChatService] creating new chat for character: {character_id}")
    now = datetime.now(timezone.utc).isoformat()
    messages = []

    # 构建系统消息
    if character.get('system_prompt'):
        messages.append({'role': 'system', 'content': character['system_prompt']})
    elif character.get('description') or character.get('personality'):
        system_parts = []
        if character.get('description'):
            system_parts.append(f"你是{character['name']}。{character['description']}")
        if character.get('personality'):
            system_parts.append(f"性格：{character['personality']}")
        if character.get('scenario'):
            system_parts.append(f"场景：{character['scenario']}")
        if system_parts:
            messages.append({'role': 'system', 'content': '\n'.join(system_parts)})

    # 添加开场白
    if character.get('first_message'):
        messages.append({'role': 'assistant', 'content': character['first_message']})

    chat = {
        'id': str(uuid.uuid4()),
        'character_id': character_id,
        'title': character.get('name', '新对话'),
        'messages': messages,
        'created_at': now,
        'updated_at': now,
    }
    try:
        with open(_chat_path(chat['id'], chats_dir), 'w', encoding='utf-8') as f:
            json.dump(chat, f, ensure_ascii=False, indent=2)
        logger.info(f"[ChatService] chat created: {chat['id']} - {chat['title']}")
        return chat
    except Exception as e:
        logger.error(f"[ChatService] failed to create chat: {e}")
        raise


def append_message(chat_id, role, content, chats_dir):
    logger.info(f"[ChatService] appending message: role={role}, chat_id={chat_id}")
    chat = get_chat(chat_id, chats_dir)
    if not chat:
        logger.error(f"[ChatService] cannot append message, chat not found: {chat_id}")
        return None
    chat['messages'].append({'role': role, 'content': content})
    chat['updated_at'] = datetime.now(timezone.utc).isoformat()
    try:
        with open(_chat_path(chat_id, chats_dir), 'w', encoding='utf-8') as f:
            json.dump(chat, f, ensure_ascii=False, indent=2)
        logger.info(f"[ChatService] message appended, total messages: {len(chat['messages'])}")
        return chat
    except Exception as e:
        logger.error(f"[ChatService] failed to append message: {e}")
        raise


def delete_chat(chat_id, chats_dir):
    logger.info(f"[ChatService] deleting chat: {chat_id}")
    path = _chat_path(chat_id, chats_dir)
    if os.path.exists(path):
        try:
            os.remove(path)
            logger.info(f"[ChatService] chat deleted: {chat_id}")
            return True
        except Exception as e:
            logger.error(f"[ChatService] failed to delete chat {chat_id}: {e}")
            raise
    logger.warning(f"[ChatService] chat not found for deletion: {chat_id}")
    return False