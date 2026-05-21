# Tavern Lite

一个轻量级的 AI 角色扮演聊天平台，类似 SilllyTavern 的核心功能。

## 原因

开发这个项目的原因，主要是 **SillyTavern（酒馆）使用起来太麻烦**。

感觉酒馆的核心功能就是**角色提示词**，但它功能太多、界面复杂，对于只是想简单玩一下 AI 角色扮演的人来说，学习成本有点高。

因此计划用 Claude 写一个**简单版本**，自己玩玩。核心需求：
- 角色卡管理（创建角色、设定 prompt）
- 简单聊天（流式输出）
- 故事模式（多角色互动）

如果你也有类似的需求，希望这个小项目能帮到你。

## 功能特性

### 1. 角色卡管理
- 创建、编辑、删除角色
- 支持角色描述、性格、场景设定
- 系统提示词和开场白配置
- 角色列表展示，卡片式布局

### 2. 聊天模式
- 与单个 AI 角色进行对话
- SSE 流式输出，逐字显示
- 聊天历史自动保存
- 支持 OpenAI 兼容格式的 API

### 3. 故事模式
- 统一对话框，旁白+角色对话混合显示
- 多角色互动，大模型判断谁应该回复
- 左侧角色栏可展开查看角色背景设定
- 剧情驱动的互动小说风格

### 4. API 配置管理
- 支持多个 API 端点配置
- 切换不同模型（GLM、Claude、OpenAI 等）
- 独立配置每个 API 的参数（temperature、top_p、max_tokens）
- 流式/非流式切换

### 5. 其他
- 夜间模式支持
- 详细日志输出，便于调试
- Flask 后端 + Jinja2 模板
- 数据持久化（JSON 文件存储）

## 技术栈

- **后端**: Python Flask
- **LLM SDK**: OpenAI Python SDK（兼容 OpenAI 格式 API）
- **前端**: HTML + CSS + JavaScript
- **存储**: JSON 文件

## 项目结构

```
tavern-lite/
├── app.py                  # Flask 应用入口
├── requirements.txt        # 依赖
├── data/                   # 数据目录
│   ├── characters/         # 角色卡 JSON
│   ├── chats/              # 聊天记录 JSON
│   ├── stories/            # 故事数据 JSON
│   └── settings.json       # API 配置
├── routes/                 # 路由蓝图
│   ├── character.py        # 角色相关
│   ├── chat.py             # 聊天相关
│   ├── story.py            # 故事模式相关
│   └── settings.py         # 设置相关
├── services/               # 业务逻辑
│   ├── character_service.py
│   ├── chat_service.py
│   ├── llm_service.py
│   └── story_service.py
├── templates/              # HTML 模板
└── static/                 # 静态资源
```

## 启动方法

### 1. 安装依赖

```bash
cd /root/tavern-lite
pip3 install -r requirements.txt
```

或使用 `--break-system-packages`（如果需要）：

```bash
pip3 install --break-system-packages flask openai python-dotenv
```

### 2. 启动服务

```bash
python3 app.py
```

默认端口 `8001`，绑定 `0.0.0.0`

### 3. 自定义端口

```bash
python3 app.py --port 8002
```

### 4. 访问

浏览器打开：`http://你的IP:8001`

## 配置 API

1. 点击顶部导航栏「设置」
2. 在「API 配置」中添加新的配置：
   - 配置 ID（如：glm, deer）
   - 显示名称
   - API 地址（OpenAI 兼容格式）
   - API Key
   - 模型名称
   - 参数配置
3. 点击「使用」切换当前 API

## 日志说明

启动服务后，控制台会输出详细日志：
- `[CharacterRoute]` - 角色相关操作
- `[ChatRoute]` - 聊天相关操作
- `[StoryRoute]` - 故事模式操作
- `[LLMService]` - LLM API 调用详情（包含输入输出）

## 默认配置

首次启动时，预设了 GLM-5.1 API 配置：
- API URL: `https://aigw-gzgy2.cucloud.cn:8443/v1`
- Model: `glm-5.1`

可在设置页面修改或添加新的 API 配置。

## 开发说明

- 所有路由都有详细的日志输出
- `services/llm_service.py` 中的 `chat_completion` 函数会打印完整的 LLM 输入输出
- 故事模式使用特殊格式：`[旁白:内容]` 或 `[角色名:内容]`
- 前端支持暗色模式，自动适配系统主题

## License

MIT
