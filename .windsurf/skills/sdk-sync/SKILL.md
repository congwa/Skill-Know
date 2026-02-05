---
name: sdk-sync
description: embedease-sdk 代码同步指南。当需要更新 SDK 或遇到 SDK 相关问题时触发。
触发场景：
- 需要从源头仓库更新 SDK
- SDK 相关的构建或依赖问题
- 调试 SDK 代码
alwaysApply: false
---

# embedease-sdk 代码同步指南

本项目使用的 SDK 代码从 embedease-ai 项目复制而来。

## SDK 源头

- **源头仓库**：embedease-ai
- **独立备份**：https://github.com/congwa/embedease-sdk

## SDK 目录结构

```
Skill-Know/
├── frontend/packages/
│   ├── chat-sdk/           # 前端核心 SDK
│   └── chat-sdk-react/     # React 封装
└── backend/packages/
    └── langgraph-agent-kit/ # 后端 Python SDK
```

## 依赖配置

### 前端 (frontend/package.json)

```json
{
  "dependencies": {
    "@embedease/chat-sdk": "file:./packages/chat-sdk",
    "@embedease/chat-sdk-react": "file:./packages/chat-sdk-react"
  }
}
```

### 后端 (backend/pyproject.toml)

```toml
[project]
dependencies = [
    "langgraph-agent-kit",
    # ...
]

[tool.uv.sources]
langgraph-agent-kit = { path = "./packages/langgraph-agent-kit", editable = true }
```

## 从源头更新 SDK

当 embedease-ai 项目的 SDK 有更新时：

```bash
# 假设 embedease-ai 在同级目录
SOURCE="../embedease-ai"

# 更新前端 SDK
rm -rf frontend/packages/chat-sdk frontend/packages/chat-sdk-react
cp -r $SOURCE/frontend/packages/chat-sdk frontend/packages/
cp -r $SOURCE/frontend/packages/chat-sdk-react frontend/packages/

# 清理 node_modules 和 dist
rm -rf frontend/packages/chat-sdk/node_modules frontend/packages/chat-sdk/dist
rm -rf frontend/packages/chat-sdk-react/node_modules frontend/packages/chat-sdk-react/dist

# 更新后端 SDK
rm -rf backend/packages/langgraph-agent-kit
cp -r $SOURCE/backend/packages/langgraph-agent-kit backend/packages/

# 重新构建
cd frontend/packages/chat-sdk && pnpm install && pnpm build
cd ../chat-sdk-react && pnpm install && pnpm build
cd ../../../frontend && pnpm install

cd ../backend && uv sync
```

## 从独立仓库更新

也可以从 embedease-sdk 仓库更新：

```bash
SDK_REPO="../embedease-sdk"

# 先拉取最新代码
cd $SDK_REPO && git pull origin main

# 更新前端 SDK
rm -rf frontend/packages/chat-sdk frontend/packages/chat-sdk-react
cp -r $SDK_REPO/frontend/chat-sdk frontend/packages/
cp -r $SDK_REPO/frontend/chat-sdk-react frontend/packages/

# 更新后端 SDK
rm -rf backend/packages/langgraph-agent-kit
cp -r $SDK_REPO/backend/langgraph-agent-kit backend/packages/

# 重新构建...
```

## 构建 SDK

### 前端 SDK 构建

```bash
cd frontend/packages/chat-sdk
pnpm install && pnpm build

cd ../chat-sdk-react
pnpm install && pnpm build

cd ../../
pnpm install
```

### 后端 SDK 安装

```bash
cd backend
uv sync
```

## 常见问题

### 问题 1：找不到 @embedease/chat-sdk 模块

**解决**：
```bash
cd frontend/packages/chat-sdk && pnpm install && pnpm build
cd ../chat-sdk-react && pnpm install && pnpm build
cd ../../ && pnpm install
```

### 问题 2：后端找不到 langgraph-agent-kit

**解决**：
```bash
cd backend && uv sync
```

### 问题 3：SDK 版本不一致

检查各处版本号是否一致：
- `frontend/packages/chat-sdk/package.json`
- `frontend/packages/chat-sdk-react/package.json`
- `backend/packages/langgraph-agent-kit/pyproject.toml`

## 本地修改 SDK

如果需要在本项目中临时修改 SDK：

1. 直接修改 `packages/` 下的代码
2. 重新构建 SDK
3. 测试功能
4. **重要**：将修改同步回 embedease-ai 源头仓库

```bash
# 将修改同步回源头
SOURCE="../embedease-ai"
cp -r frontend/packages/chat-sdk/* $SOURCE/frontend/packages/chat-sdk/
cp -r frontend/packages/chat-sdk-react/* $SOURCE/frontend/packages/chat-sdk-react/
cp -r backend/packages/langgraph-agent-kit/* $SOURCE/backend/packages/langgraph-agent-kit/
```

## 版本追踪

当前使用的 SDK 版本：
- 查看 `frontend/packages/chat-sdk/package.json` 中的 `version` 字段
- 查看 `backend/packages/langgraph-agent-kit/pyproject.toml` 中的 `version` 字段
