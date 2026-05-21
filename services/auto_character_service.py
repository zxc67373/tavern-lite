import json
import logging
from services.llm_service import chat_completion

logger = logging.getLogger('tavern-lite')

SYSTEM_PROMPT = """你是一个角色设计助手。根据用户提供的角色描述，生成一个完整的角色设定。

请以纯 JSON 格式输出，不要包含任何其他内容。JSON 包含以下字段：
- name: 角色名称
- description: 角色背景描述（2-3句话）
- personality: 性格特征（1-2句话）
- scenario: 对话场景设定（1-2句话）
- first_message: 开场白（1句话，符合角色设定，要自然口语化）
- system_prompt: 系统提示词（3-5句话，定义角色行为方式、说话风格）
- example_messages: 示例对话（2-3轮对话，格式：user: xxx\\nassistant: xxx）

要求：
1. 只输出 JSON，不要有任何解释或 markdown 标记
2. 所有字段内容要与角色设定一致
3. first_message 要自然、口语化，符合角色身份
4. 语言与用户输入保持一致
5. first_message 不要包含动作描写，只说话"""


def generate_character(user_input, settings):
    logger.info(f"[AutoCharacterService] generating character from: {user_input[:50]}...")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"请根据以下描述生成角色设定：{user_input}"}
    ]

    try:
        response = chat_completion(messages, settings, stream=False)
        logger.info(f"[AutoCharacterService] LLM response received, length: {len(response) if response else 0}")

        # 清理响应，提取 JSON
        json_str = _extract_json(response)
        if not json_str:
            logger.error(f"[AutoCharacterService] failed to extract JSON from response")
            raise ValueError("无法从模型响应中提取角色数据")

        character = json.loads(json_str)
        logger.info(f"[AutoCharacterService] character generated: {character.get('name')}")
        return character

    except json.JSONDecodeError as e:
        logger.error(f"[AutoCharacterService] JSON decode error: {e}")
        raise ValueError(f"生成的角色数据格式错误: {e}")
    except Exception as e:
        logger.error(f"[AutoCharacterService] generation error: {e}")
        raise


def _extract_json(text):
    """从文本中提取 JSON 部分"""
    if not text:
        return None

    # 尝试直接解析
    try:
        json.loads(text)
        return text
    except:
        pass

    # 尝试找 JSON 块
    import re
    # 匹配 ```json ... ``` 或 ``` ... ```
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()

    # 尝试找 { ... }
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        return match.group(0)

    return None