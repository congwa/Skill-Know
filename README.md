# Skill-Know 知识库系统

以 Skill 搜索为主的知识库系统，支持文档管理、技能管理、智能搜索和 AI 对话。

## 功能特性

- **技能管理**: 系统技能和文档技能的管理，支持分类、搜索和编辑
- **文档管理**: 文档上传、分类、全文搜索
- **知识搜索**: 自然语言搜索和 SQL 搜索
- **智能对话**: 基于 LangChain 的流式 AI 对话
- **提示词管理**: 系统提示词的查看和编辑
- **快速设置**: 最小化配置即可使用

## 技术栈

### 后端
- Python 3.13+
- FastAPI
- SQLAlchemy + SQLite (aiosqlite)
- LangChain + OpenAI

### 前端
- Next.js 15
- React 19
- TailwindCSS
- Radix UI
- Tiptap (富文本编辑器)

## 快速开始

### 1. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -e .

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY

# 启动服务
python -m app.main
```

后端服务运行在 http://localhost:8000

### 2. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务运行在 http://localhost:3000

### 3. 首次使用

访问 http://localhost:3000，系统会自动跳转到快速设置页面。
填入 LLM API Key 并测试连接后即可开始使用。

## 项目结构

```
Skill-Know/
├── backend/
│   ├── app/
│   │   ├── core/          # 核心模块（配置、数据库、日志）
│   │   ├── models/        # 数据模型
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # 业务逻辑
│   │   ├── routers/       # API 路由
│   │   └── main.py        # 应用入口
│   └── pyproject.toml
├── frontend/
│   ├── app/               # Next.js App Router
│   │   └── admin/         # 管理后台页面
│   ├── components/        # React 组件
│   ├── lib/               # 工具函数和 API 客户端
│   └── package.json
└── README.md
```

## API 端点

- `GET /api/skills` - 技能列表
- `POST /api/skills/search` - 技能搜索
- `GET /api/documents` - 文档列表
- `POST /api/documents/upload` - 上传文档
- `GET /api/search` - 统一搜索
- `POST /api/search/sql` - SQL 搜索
- `POST /api/chat/stream` - 流式聊天
- `GET /api/prompts` - 提示词列表
- `GET /api/quick-setup/state` - 设置状态

## 许可证

MIT
