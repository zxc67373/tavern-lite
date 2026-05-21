import json
import os
from openai import OpenAI
import logging

logger = logging.getLogger('tavern-lite')

DEFAULT_CONFIG = {
    'id': 'default',
    'name': '默认配置',
    'api_url': 'https://aigw-gzgy2.cucloud.cn:8443/v1',
    'api_key': 'xxxxx',
    'model': 'glm-5.1',
    'max_tokens': 2048,
    'temperature': 0.8,
    'top_p': 0.9,
    'stream': True,
}

DEFAULT_SETTINGS = {
    'api_configs': [DEFAULT_CONFIG],
    'current_config': 'default'
}


def load_settings(settings_file):
    logger.info(f"[LLMService] loading settings from: {settings_file}")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                if 'api_configs' not in saved or not saved['api_configs']:
                    saved['api_configs'] = DEFAULT_SETTINGS['api_configs']
                if 'current_config' not in saved:
                    saved['current_config'] = saved['api_configs'][0]['id']
                logger.info(f"[LLMService] settings loaded, current config: {saved.get('current_config')}")
                return saved
        except Exception as e:
            logger.error(f"[LLMService] failed to load settings: {e}")
    logger.info("[LLMService] using default settings")
    return {**DEFAULT_SETTINGS}


def save_settings(settings_file, data):
    logger.info(f"[LLMService] saving settings, current_config: {data.get('current_config')}")
    existing = {}
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except Exception as e:
            logger.error(f"[LLMService] failed to load existing settings: {e}")

    api_configs = existing.get('api_configs', DEFAULT_SETTINGS['api_configs'])

    settings = {
        'api_configs': api_configs,
        'current_config': data.get('current_config', existing.get('current_config', 'default'))
    }

    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        logger.info(f"[LLMService] settings saved successfully")
    except Exception as e:
        logger.error(f"[LLMService] failed to save settings: {e}")
        raise
    return settings


def save_api_configs(settings_file, api_configs):
    logger.info(f"[LLMService] saving {len(api_configs)} API configs")
    existing = load_settings(settings_file)
    existing['api_configs'] = api_configs
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        logger.info("[LLMService] API configs saved successfully")
    except Exception as e:
        logger.error(f"[LLMService] failed to save API configs: {e}")
        raise
    return existing


def get_current_config(settings):
    current_id = settings.get('current_config')
    configs = settings.get('api_configs', [])

    for config in configs:
        if config.get('id') == current_id:
            logger.info(f"[LLMService] current config: {config.get('name')} ({current_id})")
            return config

    logger.warning(f"[LLMService] config not found: {current_id}, using first available")
    return configs[0] if configs else DEFAULT_CONFIG


def _build_client(config):
    logger.debug(f"[LLMService] building client for: {config.get('api_url')}")
    return OpenAI(
        base_url=config['api_url'],
        api_key=config['api_key'],
    )


def chat_completion(messages, settings, stream=True):
    config = get_current_config(settings)
    logger.info(f"[LLMService] chat completion request - model: {config.get('model')}, stream: {stream}")

    # 打印完整的输入 messages
    logger.info(f"[LLMService] ===== LLM INPUT START =====")
    logger.info(f"[LLMService] API URL: {config.get('api_url')}")
    logger.info(f"[LLMService] Model: {config.get('model')}")
    logger.info(f"[LLMService] Messages count: {len(messages)}")
    for i, msg in enumerate(messages):
        logger.info(f"[LLMService] Message[{i}] role={msg.get('role')}: {msg.get('content', '')[:200]}")
    logger.info(f"[LLMService] ===== LLM INPUT END =====")

    try:
        client = _build_client(config)
        logger.info(f"[LLMService] sending request to {config.get('api_url')}")

        response = client.chat.completions.create(
            model=config.get('model', 'gpt-4'),
            messages=messages,
            max_tokens=config.get('max_tokens', 2048),
            temperature=config.get('temperature', 0.8),
            top_p=config.get('top_p', 0.9),
            stream=stream,
        )

        if stream:
            logger.info("[LLMService] stream response started")
            return response

        content = response.choices[0].message.content
        logger.info(f"[LLMService] ===== LLM OUTPUT START =====")
        logger.info(f"[LLMService] Response content length: {len(content) if content else 0}")
        logger.info(f"[LLMService] Response content: {content}")
        logger.info(f"[LLMService] ===== LLM OUTPUT END =====")
        return content

    except Exception as e:
        logger.error(f"[LLMService] chat completion error: {e}")
        raise