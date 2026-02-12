# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-02-12

### 核心亮点

本版本为 **初始发布版本**，完成 Skill-Know 项目的基础架构搭建，集成 langgraph-agent-kit SDK，实现知识管理和技能处理的核心功能。

### Added

- **项目初始化**
  - 创建完整的前后端项目结构
  - 集成 langgraph-agent-kit SDK 统一开发框架
  - 配置前端 React + TypeScript 开发环境
  - 配置后端 Python FastAPI 服务

- **核心功能模块**
  - 知识管理系统基础架构
  - 技能处理和执行框架
  - 前端 Chat SDK 集成
  - 后端 API 路由设计

- **开发工具配置**
  - 添加 Windsurf skills 工具集
  - 配置项目开发环境
  - 设置代码规范和构建流程

### Changed

- **架构重构**
  - 统一使用 langgraph-agent-kit SDK 替代原有分散实现
  - 移除 OCR 和系统配置路由中不必要的数据库依赖
  - 优化项目模块化结构

### Infrastructure

- **前端技术栈**
  - React 18 + TypeScript
  - Vite 构建工具
  - Tailwind CSS 样式框架

- **后端技术栈**
  - Python 3.11+
  - FastAPI 框架
  - langgraph-agent-kit SDK

---

## [Unreleased] - Development Phase

### Planned Features

- 知识库管理功能
- 技能市场集成
- 用户权限系统
- 数据持久化层
