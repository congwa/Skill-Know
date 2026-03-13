# Skill-Know 技术架构文档

> 基于 OpenViking 记忆系统的设计理念，Skill-Know 实现了一套完整的知识库管理系统。
> 本文档描述系统的核心技术流程、数据流向和关键模块。

---

## 目录

1. [系统总览](#1-系统总览)
2. [核心基础设施](#2-核心基础设施)
3. [知识入库流程](#3-知识入库流程)
4. [知识检索流程](#4-知识检索流程)
5. [对话与 Agent 流程](#5-对话与-agent-流程)
6. [知识生命周期管理](#6-知识生命周期管理)
7. [前端界面](#7-前端界面)
8. [数据模型](#8-数据模型)
9. [配置体系](#9-配置体系)

---

## 1. 系统总览

### 1.1 架构概览

```mermaid
flowchart TB
    subgraph Frontend ["前端 (Next.js)"]
        UI_CHAT["对话页"]
        UI_SEARCH["搜索页"]
        UI_SKILLS["技能管理"]
        UI_DOCS["文档管理"]
        UI_SETTINGS["系统设置"]
    end

    subgraph Backend ["后端 (FastAPI)"]
        subgraph Routers ["API 路由层"]
            R_CHAT["/chat"]
            R_SEARCH["/search"]
            R_SKILLS["/skills"]
            R_DOCS["/documents"]
            R_UPLOAD["/upload"]
        end

        subgraph Services ["业务服务层"]
            S_CHAT["ChatService"]
            S_RETRIEVER["SkillRetriever"]
            S_INTENT["IntentAnalyzer"]
            S_PROCESSOR["SkillProcessor"]
            S_EXTRACTOR["KnowledgeExtractor"]
            S_COMPRESSOR["SessionCompressor"]
            S_BATCH["BatchUploadService"]
            S_DEDUP["KnowledgeDeduplicator"]
        end

        subgraph Core ["核心基础设施"]
            C_CONTEXT["Context (L0/L1/L2)"]
            C_VECTOR["VectorStore"]
            C_QUEUE["QueueManager"]
            C_SCORING["Scoring"]
            C_RERANK["RerankClient"]
            C_PROMPTS["PromptManager"]
            C_CONFIG["Settings"]
        end

        subgraph Agent ["Agent 框架"]
            A_ORCH["Orchestrator (SDK)"]
            A_TOOLS["动态工具注入"]
            A_MIDDLE["StatefulToolMiddleware"]
        end
    end

    subgraph Storage ["存储层"]
        DB[(SQLite)]
        FILES["文件系统"]
        EMBED["Embedding API"]
    end

    Frontend --> Routers
    Routers --> Services
    Services --> Core
    Services --> Agent
    Core --> Storage
    Agent --> Services
```

### 1.2 项目目录结构

```
Skill-Know/
├── backend/
│   ├── app/
│   │   ├── core/               # 核心基础设施
│   │   │   ├── config.py           # Pydantic 配置
│   │   │   ├── context.py          # Context + URI + L0/L1/L2
│   │   │   ├── vector_store.py     # 向量存储
│   │   │   ├── vector_backends/    # 向量 DB 适配层
│   │   │   ├── queue.py            # 异步任务队列
│   │   │   ├── scoring.py          # 热度评分
│   │   │   ├── rerank.py           # Rerank 客户端
│   │   │   ├── service.py          # 全局服务单例
│   │   │   └── database.py         # 数据库连接
│   │   ├── models/             # SQLAlchemy 数据模型
│   │   ├── routers/            # FastAPI 路由
│   │   ├── schemas/            # Pydantic 请求/响应
│   │   ├── services/           # 业务逻辑
│   │   │   ├── chat.py             # 对话服务
│   │   │   ├── retriever.py        # 分层检索器
│   │   │   ├── intent_analyzer.py  # 意图分析
│   │   │   ├── skill_processor.py  # 技能处理管线
│   │   │   ├── knowledge_extractor.py    # 知识提取
│   │   │   ├── knowledge_deduplicator.py # 知识去重
│   │   │   ├── session_compressor.py     # 会话压缩
│   │   │   ├── batch_upload.py     # 批量上传
│   │   │   └── agent/              # Agent 工具和中间件
│   │   ├── prompts/            # Prompt 模板系统
│   │   │   ├── manager.py         # PromptManager
│   │   │   └── templates/         # YAML 模板
│   │   └── parse/              # 文档解析器
│   └── packages/
│       └── langgraph-agent-kit/   # 内部 Agent SDK
├── frontend/
│   ├── app/admin/              # 管理页面
│   ├── components/             # UI 组件
│   ├── lib/
│   │   ├── api/                # API 请求
│   │   └── stores/             # Zustand 状态管理
│   └── packages/
│       └── chat-sdk/           # 聊天 SDK
└── docs/
```

### 1.3 启动流程

```mermaid
sequenceDiagram
    participant App as FastAPI App
    participant DB as 数据库
    participant Service as SkillKnowService
    participant Queue as QueueManager
    participant Embed as Embedder

    App->>DB: init_db() 创建表
    App->>DB: init_system_skills() 初始化系统技能
    App->>Service: SkillKnowService().initialize()
    Service->>Service: ParserRegistry 注册解析器
    Service->>Queue: QueueManager 注册处理器
    Queue->>Queue: EMBEDDING handler
    Queue->>Queue: SKILL_INDEXING handler
    Service->>Embed: _init_embedder() 初始化嵌入模型
    Service->>Queue: queue_manager.start()
    Note over App: 应用就绪，开始接收请求
```

---

## 2. 核心基础设施

### 2.1 Context 模型 — 三层知识表示

Skill-Know 借鉴 OpenViking 的三层内容模型，将每条知识拆分为三个层级：

| 层级 | 名称 | 大小 | 用途 |
|------|------|------|------|
| **L0** | Abstract (摘要) | ~100 tokens | 快速向量检索候选 |
| **L1** | Overview (概览) | ~2k tokens | Rerank 精细筛选、预览 |
| **L2** | Detail (完整内容) | 不限 | 完整知识内容交付 |

**URI 命名规范**：

```
sk://skills/{skill_name}       → 技能知识
sk://documents/{document_id}   → 原始文档
sk://knowledge/{id}            → 提取的知识点
```

```mermaid
graph LR
    subgraph Context
        L0["L0: 一句话概括<br/>~100 tokens"]
        L1["L1: 结构化概览<br/>~2k tokens"]
        L2["L2: 完整内容<br/>全文"]
    end
    L0 -->|"向量索引"| VectorIndex
    L1 -->|"Rerank 精细排序"| RetrievalResult
    L2 -->|"Agent 使用"| AgentResponse
```

### 2.2 VectorStore — 向量存储与检索

```mermaid
flowchart LR
    Text["文本"] -->|"Embedding API"| Vector["向量 (1536维)"]
    Vector -->|"写入"| VectorIndex[("VectorIndex 表")]
    Query["查询文本"] -->|"Embedding API"| QVec["查询向量"]
    QVec -->|"余弦相似度"| VectorIndex
    VectorIndex -->|"Top-K"| Results["检索结果"]
```

**关键方法**：

- `index_context(context, level)` — 生成嵌入并写入索引
- `search(query, context_type, level, limit)` — 全量扫描 + 余弦相似度
- `update_activity(uri)` — 更新检索命中计数
- `get_stale_entries(days=90)` — 获取长期未使用的条目

**向量 DB 适配层**（`vector_backends/`）：

```mermaid
classDiagram
    class VectorBackend {
        <<abstract>>
        +upsert(record)
        +query(vector, context_type, level, limit)
        +text_query(text, ...)
        +delete(uri, level)
        +update_activity(uri)
        +count(context_type)
        +get_by_uri(uri, level)
    }
    class SQLiteVectorBackend {
        -session: AsyncSession
        +upsert(record)
        +query(vector, ...)
    }
    VectorBackend <|-- SQLiteVectorBackend
    VectorBackend <|-- QdrantBackend
    VectorBackend <|-- ChromaBackend
    note for QdrantBackend "预留扩展"
    note for ChromaBackend "预留扩展"
```

### 2.3 QueueManager — 异步任务队列

```mermaid
flowchart LR
    Producer["生产者<br/>(SkillProcessor)"] -->|"enqueue"| Queue["asyncio.Queue"]
    Queue -->|"消费"| Consumer["_consume() 循环"]
    Consumer -->|"EMBEDDING"| H1["生成向量嵌入"]
    Consumer -->|"SKILL_INDEXING"| H2["Context → VectorStore"]
    Consumer -->|"失败"| Retry["重试 (max 3次)"]
```

### 2.4 Scoring — 热度评分

```mermaid
graph LR
    semantic["语义相似度"] -->|"(1 - α)"| blend["blend_scores()"]
    hotness["热度评分"] -->|"α = 0.2"| blend
    blend --> final["最终得分"]

    active["active_count"] --> hs["hotness_score()"]
    time["updated_at"] -->|"时间衰减"| hs
    hs --> hotness
```

**公式**：
- `hotness = sigmoid(log1p(active_count)) × time_decay`
- `time_decay = 0.5 ^ (days_since_update / half_life)`
- `final_score = (1 - α) × semantic_score + α × hotness_score`

### 2.5 Prompt 模板系统

```mermaid
flowchart LR
    Code["服务代码"] -->|"render_prompt('category.name', vars)"| PM["PromptManager"]
    PM -->|"加载"| YAML["templates/category/name.yaml"]
    YAML -->|"Jinja2 渲染"| Prompt["最终 Prompt 文本"]
```

**已有模板**：

| 模板 ID | 用途 |
|---------|------|
| `retrieval.intent_analysis` | 意图分析与查询拆解 |
| `compression.knowledge_extraction` | 对话知识提取 |
| `compression.dedup_decision` | 去重决策 |
| `compression.session_summary` | 会话摘要 |
| `semantic.abstract_generation` | L0 摘要生成 |
| `semantic.overview_generation` | L1 概览生成 |

---

## 3. 知识入库流程

### 3.1 批量上传全流程

```mermaid
flowchart TB
    Upload["用户上传文件"] --> Save["保存到 data/uploads/"]
    Save --> Parse["DocumentParser.parse()<br/>识别格式: txt/md/pdf/docx"]
    Parse --> Analyze["ContentAnalyzer.analyze()<br/>提取关键词、结构摘要"]
    Analyze --> Processor["SkillProcessor.process()"]

    subgraph SkillProcessor ["SkillProcessor 管线"]
        SP1["Step 1: 解析输入"]
        SP2["Step 2: LLM 生成 L0 摘要 + L1 概览"]
        SP3["Step 2.5: 去重检查"]
        SP4["Step 3: 存储到数据库"]
        SP5["Step 4: 入队异步索引"]

        SP1 --> SP2 --> SP3
        SP3 -->|"CREATE"| SP4
        SP3 -->|"SKIP"| Skip["跳过重复"]
        SP3 -->|"MERGE"| Merge["合并到已有 Skill"]
        SP4 --> SP5
        Merge --> SP5
    end

    Processor --> DocUpdate["更新 Document<br/>skill_id, is_converted, status"]

    SP5 --> Queue["QueueManager"]
    Queue --> Index["VectorStore.index_context()<br/>生成 L0 向量嵌入"]
```

### 3.2 去重决策流程

```mermaid
flowchart TB
    New["新知识<br/>(title + abstract)"] --> VSearch["VectorStore.search()<br/>Top-3 相似知识"]

    VSearch -->|"无相似"| CREATE["CREATE<br/>直接入库"]
    VSearch -->|"有相似"| LLM["LLM 去重决策"]

    LLM -->|"覆盖率 > 90%"| SKIP["SKIP<br/>丢弃重复"]
    LLM -->|"覆盖率 50-90%"| MERGE["MERGE<br/>合并到已有知识"]
    LLM -->|"包含独特信息"| CREATE2["CREATE<br/>作为独立条目入库"]

    MERGE --> MergeExec["合并执行:<br/>1. 更新目标 Skill 内容<br/>2. 记录 ContextRelation<br/>3. 重新索引"]
```

### 3.3 文档转技能流程

```mermaid
flowchart LR
    Doc["Document"] -->|"convert()"| Parse["ParserRegistry.parse()"]
    Parse --> Analyze["ContentAnalyzer"]
    Analyze --> Generator["SkillGenerator.generate()"]
    Generator --> Skill["创建 Skill"]
    Skill --> Relation["ContextRelation<br/>(derived_from)"]
    Skill --> Index["入队向量索引"]
```

---

## 4. 知识检索流程

### 4.1 分层检索全流程

```mermaid
flowchart TB
    Query["用户查询"] --> Intent["IntentAnalyzer.analyze()"]

    Intent -->|"needs_retrieval = false"| Direct["直接回答<br/>(闲聊/打招呼)"]
    Intent -->|"needs_retrieval = true"| SubQueries["生成 SearchQuery 列表<br/>每条含 query + priority + context_type"]

    SubQueries --> Parallel["asyncio.gather<br/>并行执行子查询"]

    subgraph Retriever ["SkillRetriever.retrieve()"]
        R1["Step 1: L0 向量搜索<br/>limit × 3 扩大候选集"]
        R2["Step 2: 关联 Skill 数据<br/>加载完整 Skill + ContextRelation"]
        R3["Step 3: blend_scores<br/>语义 × (1-α) + 热度 × α"]
        R4["Step 4: L1 Rerank<br/>(Rerank 模型 或 向量相似度)"]
        R5["Step 5: 更新活跃度<br/>active_count += 1"]

        R1 --> R2 --> R3 --> R4 --> R5
    end

    Parallel --> Retriever
    Retriever --> Merge["合并去重<br/>按 skill_id 取最高分"]
    Merge --> Results["最终结果<br/>包含 L0/L1/L2 + 关联上下文"]
```

### 4.2 意图分析详细流程

```mermaid
flowchart LR
    Input["当前消息 + 对话历史"] --> LLM["LLM 意图分析<br/>(retrieval.intent_analysis)"]

    LLM --> Plan["QueryPlan"]
    Plan --> Q1["SearchQuery 1<br/>query='Python 数据分析'<br/>priority=1<br/>context_type='skill'"]
    Plan --> Q2["SearchQuery 2<br/>query='Pandas 教程'<br/>priority=2<br/>context_type='document'"]
    Plan --> Q3["SearchQuery 3<br/>query='数据清洗方法'<br/>priority=3<br/>context_type=''"]
```

### 4.3 Rerank 两种模式

```mermaid
flowchart TB
    Candidates["L0 候选集"] --> Mode{"搜索模式?"}

    Mode -->|"fast"| Fast["向量相似度 Rerank<br/>embed(query) × embed(L1)<br/>→ cosine similarity"]
    Mode -->|"thinking"| Thinking["Rerank 模型 Rerank<br/>RerankClient.rerank()<br/>→ relevance_score"]

    Fast --> ScoreProp["Score Propagation<br/>α × L1_score + (1-α) × L0_score"]
    Thinking --> ScoreProp
    ScoreProp --> TopK["Top-K 结果"]

    Thinking -->|"失败"| Fast
```

### 4.4 搜索 API 流程

```mermaid
flowchart TB
    Request["GET /search?q=..."] --> Check{"语义检索可用?"}

    Check -->|"是"| Semantic["SkillRetriever.retrieve()<br/>VectorStore + 向量检索"]
    Check -->|"否"| Fallback["SkillService.search_skills()<br/>SQL ILIKE 文本匹配"]

    Semantic -->|"成功"| Format["格式化结果<br/>score, matched_by, abstract, overview"]
    Semantic -->|"异常"| Fallback

    Fallback --> Format2["基础格式<br/>name, description, content_preview"]

    Format --> Response["统一响应"]
    Format2 --> Response
```

---

## 5. 对话与 Agent 流程

### 5.1 对话全流程

```mermaid
sequenceDiagram
    actor User as 用户
    participant Chat as ChatService
    participant Retriever as SkillRetriever
    participant Orch as Orchestrator
    participant Agent as LangGraph Agent
    participant Tools as 动态工具
    participant DB as 数据库

    User->>Chat: 发送消息
    Chat->>DB: 保存用户消息
    Chat->>Retriever: _pre_retrieve(message, limit=3)
    Retriever-->>Chat: 相关知识 Top-3

    Note over Chat: 将检索结果注入 system prompt

    Chat->>Orch: Orchestrator.run(message)
    Orch->>Agent: agent.astream()

    loop Agent 自主决策
        Agent->>Tools: extract_keywords / search_skills / get_skill_content
        Tools-->>Agent: 工具结果
    end

    Agent-->>Orch: 流式响应
    Orch-->>Chat: StreamEvent
    Chat-->>User: SSE 流式返回

    Note over Chat: on_stream_end
    Chat->>DB: 保存 assistant 消息
    Chat-->>Chat: asyncio.create_task(extract_knowledge)
    Chat-->>Chat: asyncio.create_task(compress_if_needed)
```

### 5.2 Agent 工具注入与阶段转换

```mermaid
stateDiagram-v2
    [*] --> INIT

    INIT --> SKILL_RETRIEVAL: extract_keywords 被调用
    note right of INIT
        注入工具: extract_keywords
        LLM 提取关键词
    end note

    SKILL_RETRIEVAL --> TOOL_PREPARATION: search_skills 被调用
    note right of SKILL_RETRIEVAL
        注入工具: search_skills
        执行语义检索
    end note

    TOOL_PREPARATION --> EXECUTION: get_skill_content 被调用
    note right of TOOL_PREPARATION
        注入工具: get_skill_content
        获取完整 Skill 内容
    end note

    EXECUTION --> [*]: Agent 回答用户
    note right of EXECUTION
        注入工具: 从 Skill 创建的动态工具
        Agent 自主决策调用
    end note
```

### 5.3 预检索 RAG 注入

```mermaid
flowchart LR
    Msg["用户消息"] --> PreRetriever["_pre_retrieve()"]
    PreRetriever --> VectorSearch["SkillRetriever.retrieve(limit=3)"]
    VectorSearch --> Format["格式化为 Markdown"]
    Format --> Inject["注入 system_prompt"]

    Inject --> Agent["Agent 运行"]
    Agent -->|"需要更多细节"| ToolCall["调用 get_skill_content"]
    Agent -->|"知识已足够"| Answer["直接回答"]
```

---

## 6. 知识生命周期管理

### 6.1 对话知识提取

```mermaid
flowchart TB
    StreamEnd["对话结束<br/>(on_stream_end)"] -->|"异步"| Extractor["KnowledgeExtractor"]

    Extractor -->|"LLM 分析对话"| Categories["知识分类"]
    Categories --> FAQ["FAQ: 有价值的问答"]
    Categories --> CORRECTION["CORRECTION: 纠错知识"]
    Categories --> SUPPLEMENT["SUPPLEMENT: 补充知识"]

    FAQ --> Processor["SkillProcessor.process()"]
    CORRECTION --> Processor
    SUPPLEMENT --> Processor

    Processor --> Dedup["去重检查"]
    Dedup -->|"CREATE"| NewSkill["创建新 Skill"]
    Dedup -->|"MERGE"| MergeSkill["合并到已有"]
    Dedup -->|"SKIP"| Discard["丢弃"]
```

### 6.2 会话压缩与归档

```mermaid
flowchart TB
    Check["消息数 ≥ 阈值?<br/>(默认 20 条)"] -->|"否"| Skip["跳过"]
    Check -->|"是"| Archive["归档旧消息<br/>(保留最近 6 条)"]

    Archive --> Summary["LLM 生成摘要<br/>(compression.session_summary)"]
    Summary --> Store["保存摘要到 conversation.metadata"]
    Store --> Delete["删除已归档消息"]
    Delete --> Extract["触发知识提取<br/>(对归档消息)"]

    subgraph 压缩后的上下文
        CTX["conversation.metadata.summary<br/>+ 最近 6 条消息"]
    end
```

### 6.3 知识活跃度与衰减

```mermaid
graph TB
    subgraph 生命周期
        Create["知识入库<br/>active_count = 0"] --> Active["被检索命中<br/>active_count += 1"]
        Active --> Hot["热门知识<br/>hotness_score 高"]
        Active --> Cold["冷门知识<br/>长期未被检索"]
        Cold -->|"90天未访问"| Stale["标记为 stale"]
    end

    subgraph 评分影响
        Score["检索排序"] --> |"blend_scores()"| Mix["语义 80% + 热度 20%"]
        Mix --> Higher["高频知识排名更高"]
        Mix --> Lower["冷门知识排名下降"]
    end
```

---

## 7. 前端界面

### 7.1 页面功能矩阵

| 页面 | 路径 | 核心功能 |
|------|------|----------|
| **对话** | `/admin/chat` | SSE 流式对话、Timeline 展示（用户/AI/工具调用/错误） |
| **搜索** | `/admin/search` | 语义搜索 + SQL 搜索、L0→L1→L2 渐进展示、相关度分数 |
| **技能管理** | `/admin/skills` | 新建/编辑/删除 Dialog、类型过滤、Markdown 内容预览 |
| **文档管理** | `/admin/documents` | 文件夹管理、批量上传、转换为 Skill |
| **系统设置** | `/admin/settings` | LLM 配置（Provider/Key/URL/Model）、测试连接、保存 |
| **提示词** | `/admin/prompts` | Prompt 模板管理 |
| **快速设置** | `/admin/quick-setup` | 引导式初始化 |

### 7.2 搜索结果渐进展示

```mermaid
flowchart LR
    subgraph 折叠状态
        L0_Card["名称 + 摘要 (L0)<br/>相关度 87% | semantic"]
    end

    subgraph 展开状态
        L1_Section["L1 概览<br/>结构化的知识概要<br/>~500 字"]
        L2_Section["L2 内容预览<br/>完整内容的前 200 字"]
    end

    L0_Card -->|"点击展开"| L1_Section
    L1_Section --> L2_Section
```

---

## 8. 数据模型

### 8.1 核心模型关系

```mermaid
erDiagram
    Skill {
        string id PK
        string uri UK
        string name
        string description
        string type "system/document/user"
        string category "search/prompt/retrieval/tool"
        string abstract "L0"
        string overview "L1"
        string content "L2"
        json trigger_keywords
        json trigger_intents
        boolean is_active
        int priority
        string source_document_id FK
        string folder_id FK
    }

    Document {
        string id PK
        string uri
        string title
        string filename
        string file_path
        string content
        string status "pending/processing/completed/failed"
        string skill_id FK
        boolean is_converted
        string converted_at
    }

    VectorIndex {
        string id PK
        string uri
        string context_type
        int level "0/1/2"
        string text
        string vector_json
        int vector_dim
        json meta
        int active_count
    }

    ContextRelation {
        string id PK
        string source_uri
        string target_uri
        string relation_type "derived_from/merged_from/related_to"
        string reason
    }

    Conversation {
        string id PK
        string title
        json metadata "summary/compressed_at"
    }

    Message {
        string id PK
        string conversation_id FK
        string role "user/assistant/system/tool"
        string content
        json tool_calls
        int latency_ms
    }

    Skill ||--o{ VectorIndex : "uri → 索引"
    Skill }o--|| Document : "source_document_id"
    Skill ||--o{ ContextRelation : "uri → 关联"
    Document }o--|| DocumentFolder : "folder_id"
    Conversation ||--o{ Message : "conversation_id"
```

### 8.2 VectorIndex 索引结构

每个 Skill 在 VectorIndex 中最多有 2 条记录（L0 和 L1），通过 `(uri, level)` 复合唯一键区分：

| uri | level | text | 用途 |
|-----|-------|------|------|
| `sk://skills/python-basics` | 0 | "Python 基础教程的核心概念..." | L0 向量检索 |
| `sk://skills/python-basics` | 1 | "## 功能概述\n..." | L1 Rerank |

---

## 9. 配置体系

### 9.1 配置来源

```mermaid
flowchart LR
    ENV[".env 环境变量"] --> Settings["config.py Settings"]
    DB_CONFIG["system_config 表"] --> SystemConfigService
    Settings --> Runtime["运行时参数"]
    SystemConfigService --> Runtime
```

### 9.2 配置项一览

| 分类 | 配置项 | 默认值 | 说明 |
|------|--------|--------|------|
| **应用** | `APP_NAME` | Skill-Know | 应用名称 |
| **LLM** | `LLM_PROVIDER` | openai | 提供商 |
| | `LLM_API_KEY` | | API 密钥 |
| | `LLM_BASE_URL` | https://api.openai.com/v1 | API 地址 |
| | `LLM_CHAT_MODEL` | gpt-4o-mini | 聊天模型 |
| | `LLM_EMBEDDING_MODEL` | text-embedding-3-small | 嵌入模型 |
| **检索** | `DEFAULT_SEARCH_MODE` | fast | fast / thinking |
| | `DEFAULT_SEARCH_LIMIT` | 5 | 默认检索数量 |
| | `AUTO_GENERATE_L0` | true | 自动生成 L0 摘要 |
| | `AUTO_GENERATE_L1` | true | 自动生成 L1 概览 |
| **生命周期** | `ENABLE_KNOWLEDGE_DECAY` | true | 启用知识衰减 |
| | `KNOWLEDGE_DECAY_DAYS` | 90 | 衰减天数阈值 |
| **Rerank** | `RERANK_ENABLED` | false | 启用 Rerank |
| | `RERANK_MODEL` | | Rerank 模型 |
| | `RERANK_API_KEY` | | Rerank API Key |
| | `RERANK_BASE_URL` | | Rerank API 地址 |
| **会话** | `SESSION_COMPRESS_THRESHOLD` | 20 | 压缩触发消息数 |

---

## 附录：OpenViking 借鉴清单

| OpenViking 模式 | Skill-Know 对应实现 | 阶段 |
|-----------------|---------------------|------|
| Context + URI + L0/L1/L2 | `core/context.py` | Phase 1 |
| ParserRegistry | `parse/registry.py` | Phase 1 |
| SkillProcessor 管线 | `services/skill_processor.py` | Phase 1 |
| VectorStore + Scoring | `core/vector_store.py` + `core/scoring.py` | Phase 1 |
| QueueManager | `core/queue.py` | Phase 1 |
| MemoryDeduplicator | `services/knowledge_deduplicator.py` | Phase 2 |
| IntentAnalyzer (multi-query) | `services/intent_analyzer.py` | Phase 2 |
| HierarchicalRetriever (L0+L1) | `services/retriever.py` | Phase 2 |
| MemoryExtractor | `services/knowledge_extractor.py` | Phase 2 |
| Chat RAG 预检索 | `services/chat.py` _pre_retrieve | Phase 2 |
| 活跃度生命周期 | `VectorStore` + `SkillRetriever` | Phase 2 |
| Prompt 模板注册表 (YAML) | `prompts/manager.py` | Phase 3 |
| Rerank 客户端 (模型级) | `core/rerank.py` | Phase 3 |
| SessionCompressor | `services/session_compressor.py` | Phase 3 |
| 向量 DB 适配层 | `core/vector_backends/` | Phase 3 |
| 集中式 Pydantic 配置 | `core/config.py` Settings | Phase 3 |
