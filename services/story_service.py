import json
import uuid
import os
from datetime import datetime, timezone
import re
import logging
from services.llm_service import chat_completion

logger = logging.getLogger('tavern-lite')


def _story_path(story_id, stories_dir):
    return os.path.join(stories_dir, f'{story_id}.json')


SYSTEM_PROMPT = """你是一个故事创作大师。根据用户提供的关键词，设计一个完整的线性叙事故事世界。

请以纯 JSON 格式输出，不要包含任何其他内容。JSON 包含以下字段：
- name: 故事名称（简洁有力）
- world_setting: 世界观设定（3-5句话，描述时代、背景、规则）
- main_plot: 主线剧情介绍（3-5句话，核心冲突和目标）
- branch_plots: 支线剧情数组（每个包含 title 和 description）
- main_character: 主角设定（name, background, personality）
- npcs: NPC 数组（3-5个核心角色，每个���含：name, role, personality, background, relationship, first_message）
- plot_tree: 剧情树（包含 start 节点，每个节点有 description 和 choices 数组）

剧情树结构说明：
- start: 故事开始节点
- 每个节点有 description（场景描述）和 choices（选项数组）
- choices 每个选项有 text（选项文本）和 next（下一节点ID）

要求：
1. 输出必须是合法的 JSON
2. NPC 必须与关键词主题紧密相关
3. 剧情要有内在逻辑和情感冲突
4. 支线要与主线有呼应或对比
5. 每个 NPC 至少有 2 个可选对话/行动分支
6. 语言与用户输入保持一致（用户用中文就全中文）
7. first_message 要自然，符合角色身份"""


def generate_story(keywords, settings, stories_dir):
    """根据关键词生成故事"""
    logger.info(f"[StoryService] generating story from keywords: {keywords}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"用户输入的关键词：{keywords}\n\n请根据这些关键词设计一个完整的线性故事世界。"}
    ]

    try:
        response = chat_completion(messages, settings, stream=False)
        logger.info(f"[StoryService] LLM response received, length: {len(response) if response else 0}")

        # 清理响应，提取 JSON
        json_str = _extract_json(response)
        if not json_str:
            logger.error(f"[StoryService] failed to extract JSON from response")
            raise ValueError("无法从模型响应中提取故事数据")

        story_data = json.loads(json_str)
        logger.info(f"[StoryService] story generated: {story_data.get('name')}")

        # 保存故事
        story = save_story(story_data, keywords, stories_dir)
        return story

    except json.JSONDecodeError as e:
        logger.error(f"[StoryService] JSON decode error: {e}")
        raise ValueError(f"生成的故事数据格式错误: {e}")
    except Exception as e:
        logger.error(f"[StoryService] generation error: {e}")
        raise


def _extract_json(text):
    """从文本中提取 JSON 部分"""
    if not text:
        return None

    try:
        json.loads(text)
        return text
    except:
        pass

    # 尝试找 JSON 块
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()

    # 尝试找 { ... }
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        return match.group(0)

    return None


def save_story(data, keywords, stories_dir):
    """保存故事到文件"""
    now = datetime.now(timezone.utc).isoformat()
    story_id = str(uuid.uuid4())

    # 为 NPC 添加 ID
    npcs = data.get('npcs', [])
    for i, npc in enumerate(npcs):
        npc['id'] = f"npc_{i}"

    story = {
        'id': story_id,
        'name': data.get('name', '未命名故事'),
        'keywords': keywords,
        'world_setting': data.get('world_setting', ''),
        'main_plot': data.get('main_plot', ''),
        'branch_plots': data.get('branch_plots', []),
        'main_character': data.get('main_character', {}),
        'npcs': npcs,
        'plot_tree': data.get('plot_tree', {}),
        'current_plot': 'start',
        'plot_history': [],
        'created_at': now,
        'updated_at': now,
    }

    try:
        os.makedirs(stories_dir, exist_ok=True)
        with open(_story_path(story_id, stories_dir), 'w', encoding='utf-8') as f:
            json.dump(story, f, ensure_ascii=False, indent=2)
        logger.info(f"[StoryService] story saved: {story_id} - {story['name']}")
        return story
    except Exception as e:
        logger.error(f"[StoryService] failed to save story: {e}")
        raise


def list_stories(stories_dir):
    """列出所有故事"""
    logger.info(f"[StoryService] listing stories from {stories_dir}")
    stories = []
    if not os.path.exists(stories_dir):
        return stories

    for fname in os.listdir(stories_dir):
        if fname.endswith('.json'):
            try:
                with open(os.path.join(stories_dir, fname), 'r', encoding='utf-8') as f:
                    stories.append(json.load(f))
            except Exception as e:
                logger.error(f"[StoryService] failed to load story {fname}: {e}")

    stories.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    return stories


def get_story(story_id, stories_dir):
    """获取单个故事"""
    path = _story_path(story_id, stories_dir)
    if not os.path.exists(path):
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[StoryService] failed to load story {story_id}: {e}")
        return None


def update_plot_progress(story_id, next_node, stories_dir):
    """更新剧情进度"""
    story = get_story(story_id, stories_dir)
    if not story:
        return None

    story['current_plot'] = next_node
    story['plot_history'].append({
        'node': next_node,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    story['updated_at'] = datetime.now(timezone.utc).isoformat()

    try:
        with open(_story_path(story_id, stories_dir), 'w', encoding='utf-8') as f:
            json.dump(story, f, ensure_ascii=False, indent=2)
        return story
    except Exception as e:
        logger.error(f"[StoryService] failed to update story: {e}")
        raise


def delete_story(story_id, stories_dir):
    """删除故事"""
    path = _story_path(story_id, stories_dir)
    if os.path.exists(path):
        os.remove(path)
        logger.info(f"[StoryService] story deleted: {story_id}")
        return True
    return False


def get_current_plot_node(story):
    """获取当前剧情节点"""
    current = story.get('current_plot', 'start')
    plot_tree = story.get('plot_tree', {})
    return plot_tree.get(current, {})


def get_npc_by_id(story, npc_id):
    """根据ID获取NPC"""
    for npc in story.get('npcs', []):
        if npc.get('id') == npc_id:
            return npc
    return None