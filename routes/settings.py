import logging
import json
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, jsonify
from services.llm_service import load_settings, save_settings, save_api_configs

logger = logging.getLogger('tavern-lite')

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/settings')
def settings():
    logger.info("[SettingsRoute] GET /settings")
    config = load_settings(current_app.config['SETTINGS_FILE'])
    logger.info(f"[SettingsRoute] loaded {len(config.get('api_configs', []))} API configs, current: {config.get('current_config')}")
    return render_template('settings.html', settings=config)


@settings_bp.route('/settings', methods=['POST'])
def save_settings_route():
    logger.info("[SettingsRoute] POST /settings")
    data = request.form.to_dict()
    save_settings(current_app.config['SETTINGS_FILE'], data)
    logger.info(f"[SettingsRoute] settings saved, current_config: {data.get('current_config')}")
    flash('设置已保存', 'success')
    return redirect(url_for('settings.settings'))


@settings_bp.route('/settings/api-configs', methods=['GET'])
def get_api_configs():
    logger.info("[SettingsRoute] GET /settings/api-configs")
    config = load_settings(current_app.config['SETTINGS_FILE'])
    return jsonify({'configs': config.get('api_configs', []), 'current': config.get('current_config')})


@settings_bp.route('/settings/api-configs', methods=['POST'])
def add_api_config():
    logger.info("[SettingsRoute] POST /settings/api-configs - adding new config")
    data = request.get_json()
    config = load_settings(current_app.config['SETTINGS_FILE'])
    configs = config.get('api_configs', [])

    new_config = {
        'id': data.get('id', '').strip() or f"config_{len(configs) + 1}",
        'name': data.get('name', '').strip(),
        'api_url': data.get('api_url', '').strip(),
        'api_key': data.get('api_key', '').strip(),
        'model': data.get('model', '').strip(),
        'max_tokens': int(data.get('max_tokens', 2048)),
        'temperature': float(data.get('temperature', 0.8)),
        'top_p': float(data.get('top_p', 0.9)),
        'stream': data.get('stream', True)
    }

    if not new_config['name'] or not new_config['api_url']:
        logger.warning("[SettingsRoute] missing required fields: name or api_url")
        return jsonify({'error': '名称和API地址不能为空'}), 400

    # 检查ID是否已存在
    for c in configs:
        if c['id'] == new_config['id']:
            logger.warning(f"[SettingsRoute] config ID already exists: {new_config['id']}")
            return jsonify({'error': '配置ID已存在'}), 400

    configs.append(new_config)
    save_api_configs(current_app.config['SETTINGS_FILE'], configs)
    logger.info(f"[SettingsRoute] config added: {new_config['id']} - {new_config['name']}")
    return jsonify({'success': True, 'config': new_config})


@settings_bp.route('/settings/api-configs/<config_id>', methods=['PUT'])
def update_api_config(config_id):
    logger.info(f"[SettingsRoute] PUT /settings/api-configs/{config_id}")
    data = request.get_json()
    config = load_settings(current_app.config['SETTINGS_FILE'])
    configs = config.get('api_configs', [])

    for c in configs:
        if c['id'] == config_id:
            c['name'] = data.get('name', c['name'])
            c['api_url'] = data.get('api_url', c['api_url'])
            c['api_key'] = data.get('api_key', c['api_key'])
            c['model'] = data.get('model', c['model'])
            c['max_tokens'] = int(data.get('max_tokens', c['max_tokens']))
            c['temperature'] = float(data.get('temperature', c['temperature']))
            c['top_p'] = float(data.get('top_p', c['top_p']))
            if 'stream' in data:
                c['stream'] = bool(data.get('stream', True))
            save_api_configs(current_app.config['SETTINGS_FILE'], configs)
            logger.info(f"[SettingsRoute] config updated: {config_id}")
            return jsonify({'success': True, 'config': c})

    logger.warning(f"[SettingsRoute] config not found: {config_id}")
    return jsonify({'error': '配置不存在'}), 404


@settings_bp.route('/settings/api-configs/<config_id>', methods=['DELETE'])
def delete_api_config(config_id):
    logger.info(f"[SettingsRoute] DELETE /settings/api-configs/{config_id}")
    config = load_settings(current_app.config['SETTINGS_FILE'])
    configs = config.get('api_configs', [])

    new_configs = [c for c in configs if c['id'] != config_id]
    if len(new_configs) == len(configs):
        logger.warning(f"[SettingsRoute] config not found for deletion: {config_id}")
        return jsonify({'error': '配置不存在'}), 404

    current = config.get('current_config')
    if current == config_id:
        config['current_config'] = new_configs[0]['id'] if new_configs else ''
        logger.info(f"[SettingsRoute] switched current config to: {config['current_config']}")

    config['api_configs'] = new_configs
    with open(current_app.config['SETTINGS_FILE'], 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    logger.info(f"[SettingsRoute] config deleted: {config_id}")
    return jsonify({'success': True})


@settings_bp.route('/settings/api-configs/<config_id>/use', methods=['POST'])
def use_api_config(config_id):
    logger.info(f"[SettingsRoute] POST /settings/api-configs/{config_id}/use - switching config")
    config = load_settings(current_app.config['SETTINGS_FILE'])
    config['current_config'] = config_id
    with open(current_app.config['SETTINGS_FILE'], 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    logger.info(f"[SettingsRoute] switched to config: {config_id}")
    return jsonify({'success': True, 'current_config': config_id})