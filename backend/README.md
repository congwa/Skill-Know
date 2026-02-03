# skill-know 后端

基于 LangChain v1.1 + FastAPI 后端。

## 快速开始

### 1. 安装依赖

```bash
cd backend
uv sync
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的硅基流动 API Key
```

### 3. 启动服务

```bash
uv run uvicorn app.main:app --reload --port 8000
```

### 4. 代码检查

```bash
uv run ruff check --fix
```
