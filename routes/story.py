import logging
from flask import Blueprint, render_template, request, redirect, url_for, current_app, Response, jsonify
from services.story_service import (
    list_stories, get_story, save_story, delete_story,
    get_npc_by_id, get_current_plot_node, update_plot_progress
)
from services.llm_service import load_settings, chat_completion

logger = logging.getLogger('tavern-lite')

story_bp = Blueprint('story', __name__)


@story_bp.route('/story')
def index():
    logger.info("[StoryRoute] GET /story")
    stories = list_stories(current_app.config['STORIES_DIR'])
    logger.info(f"[StoryRoute] loaded {len(stories)} stories")
    return render_template('story_index.html', stories=stories)


@story_bp.route('/story/new')
def new_story():
    logger.info("[StoryRoute] GET /story/new")
    return render_template('story_edit.html', story=None)


@story_bp.route('/story', methods=['POST'])
def create_story_route():
    logger.info("[StoryRoute] POST /story - creating new story")
    data = request.form.to_dict()
    keywords = data.get('keywords', '').split(',')
    story = save_story(data, keywords, current_app.config['STORIES_DIR'])
    logger.info(f"[StoryRoute] story created: {story['id']} - {story['name']}")
    return redirect(url_for('story.index'))


@story_bp.route('/story/<story_id>/edit')
def edit_story(story_id):
    logger.info(f"[StoryRoute] GET /story/{story_id}/edit")
    story = get_story(story_id, current_app.config['STORIES_DIR'])
    if not story:
        return "Story not found", 404
    return render_template('story_edit.html', story=story)


@story_bp.route('/story/<story_id>', methods=['POST'])
def update_story_route(story_id):
    logger.info(f"[StoryRoute] POST /story/{story_id}")
    data = request.form.to_dict()
    keywords = data.get('keywords', '').split(',')
    story = save_story(data, keywords, current_app.config['STORIES_DIR'], story_id)
    if not story:
        return "Story not found", 404
    return redirect(url_for('story.index'))


@story_bp.route('/story/<story_id>/delete', methods=['POST'])
def delete_story_route(story_id):
    logger.info(f"[StoryRoute] POST /story/{story_id}/delete")
    delete_story(story_id, current_app.config['STORIES_DIR'])
    return redirect(url_for('story.index'))


@story_bp.route('/story/<story_id>/play')
def play_story(story_id):
    logger.info(f"[StoryRoute] GET /story/{story_id}/play")
    story = get_story(story_id, current_app.config['STORIES_DIR'])
    if not story:
        return "Story not found", 404
    return render_template('story_play.html', story=story)


@story_bp.route('/story/<story_id>/chat', methods=['POST'])
def story_chat(story_id):
    """统一的故事对话接口"""
    logger.info(f"[StoryRoute] POST /story/{story_id}/chat")
    story = get_story(story_id, current_app.config['STORIES_DIR'])
    if not story:
        return jsonify({'error': '故事不存在'}), 404

    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'error': '消息不能为空'}), 400

    # 构建对话上下文 - 包含所有 NPC 信息
    npcs_info = []
    for npc in story.get('npcs', []):
        npcs_info.append(f"""
角色: {npc['name']}
定位: {npc['role']}
性格: {npc['personality']}
背景: {npc['background']}
与主角关系: {npc['relationship']}
""")

    npcs_text = "\n---\n".join(npcs_info)

    # 构建系统提示 - 让 LLM 输出格式化内容
    system_prompt = f"""你是故事引擎，负责推动剧情发展和角色互动。

故事背景：{story.get('world_setting', '')}

主要剧情：{story.get('main_plot', '')}

可用角色：
{npcs_text}

输出格式要求：
1. 用 [旁白:内容] 表示场景描述和旁白
2. 用 [角色名:对话内容] 表示角色说话
3. 多个角色可以相继发言
4. 旁白可以描述角色动作、心理活动、环境变化
5. 保持角色性格一致性

现在主角说了："{user_message}"

请根据剧情发展和角色性格，生成合适的回复。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    settings = load_settings(current_app.config['SETTINGS_FILE'])

    # 获取当前配置的是否流式
    use_stream = True
    for c in settings.get('api_configs', []):
        if c.get('id') == settings.get('current_config'):
            use_stream = c.get('stream', True)
            break

    logger.info(f"[StoryRoute] story chat - stream: {use_stream}")

    if use_stream:
        import json as json_mod
        def generate():
            response = chat_completion(messages, settings, stream=True)
            full_content = ''
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield f"data: {json_mod.dumps({'content': content})}\n\n"
            yield f"data: {json_mod.dumps({'done': True, 'full_content': full_content})}\n\n"
        return Response(generate(), mimetype='text/event-stream')
    else:
        response = chat_completion(messages, settings, stream=False)
        return jsonify({'content': response, 'done': True})


@story_bp.route('/story/<story_id>/choice', methods=['POST'])
def make_choice(story_id):
    logger.info(f"[StoryRoute] POST /story/{story_id}/choice")
    story = get_story(story_id, current_app.config['STORIES_DIR'])
    if not story:
        return jsonify({'error': '故事不存在'}), 404

    data = request.get_json() or {}
    choice_index = data.get('choice_index')

    # 剧情分支选择
    if choice_index is not None:
        current_node = get_current_plot_node(story)
        choices = current_node.get('choices', [])
        if 0 <= choice_index < len(choices):
            next_node = choices[choice_index].get('next')
            if next_node:
                story = update_plot_progress(story_id, next_node, current_app.config['STORIES_DIR'])
                current_node = get_current_plot_node(story)
                return jsonify({
                    'success': True,
                    'next_node': next_node,
                    'description': current_node.get('description', ''),
                    'choices': current_node.get('choices', [])
                })

    return jsonify({'error': '无效的请求'}), 400