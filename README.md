# IntelliFlow AI 智能学习助手

IntelliFlow 是一个基于 **Multi-Agent Workflow** 的 AI 学习路线生成系统。用户输入学习目标、当前基础和学习周期后，系统会通过多个 Agent 协作完成学习目标解析、阶段规划、网页资源检索、Markdown 路线生成和后续修订。

这个项目不是一个简单的 ChatGPT 聊天壳，而是将 LLM、LangGraph 工作流、Tavily Search 和 FastAPI 接口组合起来，构建了一个面向学习规划场景的 Search Augmented Generation 应用。

## 核心功能

- 根据学习目标、基础水平、学习周期生成结构化 Markdown 学习路线。
- 使用 LangGraph 编排 `Planner -> Researcher -> Writer` 主流程。
- 使用 Tavily Search 检索学习资源，并将搜索结果整理到学习路线中。
- 提供结果页 Chat Assistant，支持围绕当前学习路线继续提问。
- 支持对已有学习路线进行二次修订，将聊天中有价值的链接、课程、项目建议整合回 Markdown。
- 提供 FastAPI 接口和简单 Web UI，方便本地运行与接口调试。
- 在 OpenAI 或 Tavily 配置缺失时保留 fallback 输出，保证基础流程可运行。

## Agent 分工

| 模块 | 文件 | 作用 |
| --- | --- | --- |
| Planner Agent | `app/agents/planner.py` | 解析用户学习目标、基础水平和周期，拆解学习阶段、模块和执行步骤。 |
| Researcher Agent | `app/agents/researcher.py` | 从 Planner 输出中提取主题，调用 Tavily Search 获取学习资源，并整理推荐资料、官方文档方向、实践项目方向和复习重点。 |
| Writer Agent | `app/agents/writer.py` | 整合规划结果和搜索/研究结果，生成最终 Markdown 学习路线。 |
| Reviser Agent | `app/agents/reviser.py` | 根据当前 Markdown、聊天记录和用户修订要求，对学习路线进行二次优化。 |
| Chat Assistant | `app/agents/chat_assistant.py` | 在结果页围绕当前学习路线回答问题；当问题包含“链接、教程、官方、GitHub、视频”等搜索意图时，会调用 Tavily 搜索。 |

主工作流由 `app/core/workflow.py` 使用 LangGraph 编排：

```text
User Input
   |
   v
Planner Agent
   |
   v
Researcher Agent + Tavily Search
   |
   v
Writer Agent
   |
   v
Markdown Learning Plan
```

`Reviser Agent` 和 `Chat Assistant` 不在主生成链路中，而是在结果页生成完成后，通过独立接口继续提供问答和路线修订能力。

## 技术栈

- Python 3.10+
- FastAPI：后端 API 与 Web 服务
- LangGraph：多 Agent 工作流编排
- OpenAI SDK：LLM 调用封装
- Tavily Search API：网页搜索与资源增强
- Pydantic：请求与响应数据模型
- Jinja2 + 原生 HTML/CSS/JavaScript：本地 Web UI
- Markdown：学习路线输出格式

## 项目结构

```text
IntelliFlow/
├── app/
│   ├── agents/
│   │   ├── chat_assistant.py    # 结果页问答 Assistant
│   │   ├── planner.py           # 学习目标解析与阶段拆解
│   │   ├── researcher.py        # Tavily 搜索结果整理
│   │   ├── reviser.py           # 学习路线二次修订
│   │   └── writer.py            # Markdown 学习路线生成
│   ├── api/
│   │   └── routes.py            # FastAPI 路由
│   ├── core/
│   │   ├── llm.py               # OpenAI 调用封装与 fallback
│   │   └── workflow.py          # LangGraph 工作流定义
│   ├── models/
│   │   └── schemas.py           # Pydantic 请求/响应模型
│   ├── templates/
│   │   ├── index.html           # 输入页
│   │   └── result.html          # 结果页、Chat、路线修订
│   ├── tools/
│   │   ├── chat_web_search.py   # Chat Assistant 使用的 Tavily 搜索
│   │   └── web_search.py        # Researcher 使用的 Tavily 搜索
│   └── main.py                  # FastAPI 应用入口
├── outputs/                     # 本地生成的 Markdown 输出，建议不提交
├── .env.example                 # 环境变量示例
├── .gitignore
├── requirements.txt
└── README.md
```

## 本地运行

### 1. 克隆项目并进入目录

```bash
git clone <your-repo-url>
cd IntelliFlow
```

### 2. 创建并激活虚拟环境

Windows PowerShell：

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

macOS / Linux：

```bash
python -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

Windows PowerShell 可以使用：

```powershell
Copy-Item .env.example .env
```

`.env` 示例：

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
TAVILY_API_KEY=your_tavily_api_key_here
```

说明：

- `OPENAI_API_KEY` 缺失或调用失败时，系统会返回本地 fallback 模拟内容。
- `TAVILY_API_KEY` 缺失或调用失败时，Researcher 会回退到预设资料建议，不会中断主流程。
- `.env` 不应提交到 GitHub。

### 5. 启动服务

```bash
uvicorn app.main:app --reload
```

启动后可访问：

- Web UI：`http://127.0.0.1:8000`
- Swagger 文档：`http://127.0.0.1:8000/docs`

## API 使用示例

### 生成学习路线

`POST /generate-plan`

```bash
curl -X POST "http://127.0.0.1:8000/generate-plan" \
  -H "Content-Type: application/json" \
  -d "{\"goal\":\"学习 Redis\",\"level\":\"零基础\",\"duration\":\"2周\"}"
```

响应结构：

```json
{
  "planner_result": "学习目标：学习 Redis\n当前水平：零基础\n...",
  "researcher_result": "推荐资料类型：\n- 官方文档与入门指南\n...",
  "final_markdown": "# 学习路线：学习 Redis\n\n## 目标说明\n...",
  "output_file": "outputs/学习_Redis_plan.md"
}
```

### Chat Assistant 问答

`POST /chat`

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"推荐几个 Redis 官方文档和教程链接\",\"context\":\"# 学习路线：学习 Redis...\"}"
```

响应结构：

```json
{
  "answer": "[Web Search Enabled]\n我根据当前学习路线检索到这些网页结果..."
}
```

当 Chat Assistant 真实调用 Tavily 并获得非 fallback 搜索结果时，返回内容前会带有 `[Web Search Enabled]`，方便前端或调试时确认 Web Search 已启用。

### 修订学习路线

`POST /revise-plan`

```bash
curl -X POST "http://127.0.0.1:8000/revise-plan" \
  -H "Content-Type: application/json" \
  -d "{\"current_markdown\":\"# 学习路线：学习 Redis...\",\"chat_history\":[{\"role\":\"user\",\"content\":\"推荐 Redis 官方文档\"},{\"role\":\"assistant\",\"content\":\"https://redis.io/docs/latest/\"}],\"instruction\":\"把官方文档加入学习路线\",\"output_file\":\"outputs/学习_Redis_plan.md\"}"
```

响应结构：

```json
{
  "revised_markdown": "# 学习路线：学习 Redis\n\n...",
  "output_file": "outputs/学习_Redis_plan_revised.md"
}
```

## 学习路线生成示例

输入：

```json
{
  "goal": "学习 Redis",
  "level": "零基础",
  "duration": "2周"
}
```

可能生成的 Markdown 结构如下。实际内容会受到 LLM 输出、Tavily 搜索结果和环境变量配置影响。

```markdown
# 学习路线：学习 Redis

## 目标说明
- 学习目标：学习 Redis
- 当前水平：零基础
- 推荐周期：2周

## 阶段划分
学习目标：学习 Redis
当前水平：零基础
周期建议：2周

学习阶段拆解：
- 阶段 1：基础理解 - 从 Redis 的核心概念、数据结构、安装和常见命令入手。
- 阶段 2：进阶实践 - 结合缓存、过期策略、持久化和简单项目进行练习。

执行步骤：
1. 明确 Redis 的使用场景和核心概念。
2. 完成本地环境安装与基本命令练习。
3. 使用 Redis 实现一个小型缓存或计数器案例。

## 推荐资料与研究方向
推荐资料类型：
- 官方文档与入门指南
- 教程视频与实战博客
- 代码示例与小项目实践

官方文档方向：
- Redis 官方文档
- Redis 命令参考

实践项目方向：
- 使用 Redis 缓存接口查询结果。
- 实现简单排行榜、计数器或 Session 存储案例。

## 每周/每日任务建议
- 第 1 周：理解概念、安装环境、练习常用数据结构和命令。
- 第 2 周：完成一个小项目，并复盘缓存设计、过期策略和常见问题。

## 实践项目建议
- 构建一个小型项目，巩固 Redis 的读写、缓存和过期时间设置。

## 复习重点
- Redis 数据结构与典型命令。
- 缓存穿透、缓存击穿、缓存雪崩等常见问题。
- 持久化、过期策略和基础性能排查思路。
```

## Web Search 调试

Tavily 调用位于：

- `app/tools/web_search.py`：主流程 Researcher 使用。
- `app/tools/chat_web_search.py`：Chat Assistant 在资源类问题中使用。

服务运行后，终端会输出搜索日志：

```text
[TAVILY SEARCH]
query=...
response=...
```

如果缺少 API Key：

```text
[TAVILY ERROR] Missing API Key
```

如果调用失败：

```text
[TAVILY ERROR] ...
```

可以通过以下方式确认 Tavily 是否真实工作：

1. `.env` 中配置有效的 `TAVILY_API_KEY`。
2. 启动 FastAPI 服务。
3. 在首页生成学习路线，或在结果页提问“推荐官方文档、GitHub 项目或教程链接”。
4. 查看终端是否出现 `[TAVILY SEARCH]` 日志。
5. 查看 Tavily Dashboard 的 API Usage 是否增加。

## 项目亮点

- **Multi-Agent Workflow**：使用 LangGraph 将学习规划拆成 Planner、Researcher、Writer 三个明确阶段，避免把所有逻辑塞进单次提示词。
- **Tool Calling / 外部工具接入**：Researcher 和 Chat Assistant 通过 Tavily Search 获取外部网页信息，增强学习资源推荐的实时性。
- **Search Augmented Generation**：先搜索，再将搜索结果交给 LLM 摘要和整理，降低纯模型回答带来的信息过时问题。
- **结构化输出**：最终产物是 Markdown 学习路线，包含目标说明、阶段划分、推荐资料、任务建议、实践项目和复习重点。
- **可降级运行**：OpenAI 或 Tavily 未配置时，系统保留 fallback 输出，方便本地演示和开发调试。
- **工程化接口设计**：使用 FastAPI + Pydantic 定义清晰的生成、问答、修订接口，便于前端或其他服务集成。

## 当前边界

以下能力当前没有实现，因此不在项目能力中宣传：

- 没有用户登录或权限系统。
- 没有数据库持久化，生成结果目前保存到本地 `outputs/` 目录。
- 没有长期记忆或跨会话用户画像。
- 没有学习进度追踪、打卡或任务完成状态管理。
- 没有对搜索资源做复杂去重、可信度评分或排序。
- 没有后台任务队列，接口调用为同步执行。

## 后续优化方向

这些是 future work，不代表当前已经实现：

- 引入数据库保存用户学习路线、聊天记录和修订历史。
- 增加学习进度追踪、任务状态和阶段复盘功能。
- 对 Tavily 搜索结果做更细粒度的去重、来源分类和质量评分。
- 将 Reviser Agent 接入主工作流或增加可配置的审核节点。
- 支持异步任务队列，优化长耗时生成请求的体验。
- 增加单元测试和端到端测试，覆盖 Agent fallback、API schema 和搜索调用逻辑。
- 支持 Docker 部署和环境配置模板。

