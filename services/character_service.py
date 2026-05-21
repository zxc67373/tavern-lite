import json
import uuid
import os
from datetime import datetime, timezone
import logging

logger = logging.getLogger('tavern-lite')


def _char_path(char_id, characters_dir):
    return os.path.join(characters_dir, f'{char_id}.json')


def list_characters(characters_dir):
    logger.info(f"[CharacterService] listing characters from {characters_dir}")
    chars = []
    if not os.path.exists(characters_dir):
        logger.warning(f"[CharacterService] characters directory does not exist: {characters_dir}")
        return chars
    for fname in os.listdir(characters_dir):
        if fname.endswith('.json'):
            try:
                with open(os.path.join(characters_dir, fname), 'r', encoding='utf-8') as f:
                    chars.append(json.load(f))
            except Exception as e:
                logger.error(f"[CharacterService] failed to load character {fname}: {e}")
    chars.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    logger.info(f"[CharacterService] loaded {len(chars)} characters")
    return chars


def get_character(char_id, characters_dir):
    logger.info(f"[CharacterService] getting character: {char_id}")
    path = _char_path(char_id, characters_dir)
    if not os.path.exists(path):
        logger.warning(f"[CharacterService] character not found: {char_id}")
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            char = json.load(f)
            logger.info(f"[CharacterService] character loaded: {char.get('name')} ({char_id})")
            return char
    except Exception as e:
        logger.error(f"[CharacterService] failed to load character {char_id}: {e}")
        return None


def create_character(data, characters_dir):
    logger.info(f"[CharacterService] creating character: {data.get('name')}")
    now = datetime.now(timezone.utc).isoformat()
    char = {
        'id': str(uuid.uuid4()),
        'name': data.get('name', ''),
        'avatar': data.get('avatar', ''),
        'description': data.get('description', ''),
        'personality': data.get('personality', ''),
        'scenario': data.get('scenario', ''),
        'first_message': data.get('first_message', ''),
        'example_messages': data.get('example_messages', ''),
        'system_prompt': data.get('system_prompt', ''),
        'created_at': now,
        'updated_at': now,
    }
    try:
        with open(_char_path(char['id'], characters_dir), 'w', encoding='utf-8') as f:
            json.dump(char, f, ensure_ascii=False, indent=2)
        logger.info(f"[CharacterService] character created successfully: {char['id']} - {char['name']}")
        return char
    except Exception as e:
        logger.error(f"[CharacterService] failed to create character: {e}")
        raise


def update_character(char_id, data, characters_dir):
    logger.info(f"[CharacterService] updating character: {char_id}")
    char = get_character(char_id, characters_dir)
    if not char:
        logger.warning(f"[CharacterService] character not found for update: {char_id}")
        return None
    for key in ('name', 'avatar', 'description', 'personality', 'scenario',
                'first_message', 'example_messages', 'system_prompt'):
        if key in data:
            char[key] = data[key]
    char['updated_at'] = datetime.now(timezone.utc).isoformat()
    try:
        with open(_char_path(char_id, characters_dir), 'w', encoding='utf-8') as f:
            json.dump(char, f, ensure_ascii=False, indent=2)
        logger.info(f"[CharacterService] character updated: {char_id} - {char.get('name')}")
        return char
    except Exception as e:
        logger.error(f"[CharacterService] failed to update character {char_id}: {e}")
        raise


def delete_character(char_id, characters_dir):
    logger.info(f"[CharacterService] deleting character: {char_id}")
    path = _char_path(char_id, characters_dir)
    if os.path.exists(path):
        try:
            os.remove(path)
            logger.info(f"[CharacterService] character deleted: {char_id}")
            return True
        except Exception as e:
            logger.error(f"[CharacterService] failed to delete character {char_id}: {e}")
            raise
    logger.warning(f"[CharacterService] character not found for deletion: {char_id}")
    return False