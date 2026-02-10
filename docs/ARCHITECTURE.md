# HealthGuard 架构设计文档

## 系统概述

HealthGuard 是一个基于 AI 的个人健康助理系统，专门为胰岛素抵抗 (IR) 患者设计。系统采用客户端-服务器架构，结合多 Agent AI 系统和 Apple HealthKit 集成。

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      iOS Client (SwiftUI)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │ Chat UI  │  │ Health   │  │ Profile  │  │  HealthKit  │ │
│  │          │  │ Sync UI  │  │   UI     │  │   Manager   │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬──────┘ │
│       │             │              │                │         │
│       └─────────────┴──────────────┴────────────────┘         │
│                           │                                   │
│                      API Client                               │
└───────────────────────────┼───────────────────────────────────┘
                            │ HTTPS/REST
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              API Layer (REST)                        │   │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────┐    │   │
│  │  │   Auth   │  │   Chat   │  │  Health Data   │    │   │
│  │  │   API    │  │   API    │  │     API        │    │   │
│  │  └────┬─────┘  └────┬─────┘  └────────┬───────┘    │   │
│  └───────┼─────────────┼──────────────────┼────────────┘   │
│          │             │                  │                 │
│  ┌───────▼─────────────▼──────────────────▼───────────┐    │
│  │          Agent Orchestrator                        │    │
│  │  ┌─────────────────────────────────────────────┐   │    │
│  │  │         Router Agent (Intent Analysis)      │   │    │
│  │  └──────┬──────────────┬──────────────┬────────┘   │    │
│  │         │              │              │             │    │
│  │  ┌──────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐     │    │
│  │  │ Diet Agent  │ │ Fitness  │ │  Medical   │     │    │
│  │  │   (GI,      │ │  Agent   │ │   Agent    │     │    │
│  │  │  Calories)  │ │ (Activity│ │  (Records) │     │    │
│  │  └─────────────┘ └──────────┘ └────────────┘     │    │
│  └───────────────────────┬───────────────────────────┘    │
│                          │                                 │
│  ┌───────────────────────▼───────────────────────────┐    │
│  │           Memory Manager                          │    │
│  │  - Daily Logs (Markdown)                          │    │
│  │  - Medical Records                                │    │
│  │  - Chat History                                   │    │
│  └───────────────────────┬───────────────────────────┘    │
│                          │                                 │
│  ┌───────────────────────▼───────────────────────────┐    │
│  │         Storage Interface                         │    │
│  │  ┌───────────────────────────────────────────┐   │    │
│  │  │      Local Storage Implementation         │   │    │
│  │  │  (Future: S3, OSS, Database)              │   │    │
│  │  └───────────────────────────────────────────┘   │    │
│  └───────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 File System (Local)                          │
│  /data/users/{user_id}/                                     │
│    ├── memories/daily_logs/YYYY-MM-DD.md                    │
│    ├── medical/records/                                     │
│    └── raw_chats/                                           │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. iOS 客户端层

#### 1.1 HealthKit Manager
- **职责**: 与 Apple HealthKit 交互
- **功能**:
  - 请求健康数据访问权限
  - 读取步数、心率、活动能量等指标
  - 提供异步 API (async/await)
- **数据流**: HealthKit → HealthKitManager → APIClient → Backend

#### 1.2 API Client
- **职责**: 后端 API 通信
- **功能**:
  - JWT 认证管理
  - RESTful API 调用
  - 请求/响应序列化
- **端点**:
  - `/auth/*`: 认证相关
  - `/chat/*`: 对话相关
  - `/health/*`: 健康数据相关

#### 1.3 View Models
- **AuthViewModel**: 用户认证状态管理
- **ChatViewModel**: 聊天消息管理
- **HealthViewModel**: 健康数据同步

### 2. 后端服务层

#### 2.1 FastAPI 应用
- **框架**: FastAPI
- **特性**:
  - 自动 API 文档 (Swagger/ReDoc)
  - 异步支持 (async/await)
  - 请求验证 (Pydantic)
  - CORS 支持

#### 2.2 认证系统
- **方式**: JWT (JSON Web Token)
- **密码加密**: bcrypt
- **流程**:
  1. 用户注册/登录
  2. 服务器生成 JWT token
  3. 客户端在后续请求中携带 token
  4. 服务器验证 token 获取用户 ID

#### 2.3 Multi-Agent 系统

##### Router Agent
```python
用户消息 → 意图分析 → 路由决策 → 返回目标 Agent
```

**意图分类**:
- `diet`: 食物、饮食、营养相关
- `fitness`: 运动、活动、健身相关
- `medical`: 医疗记录、健康指标相关
- `general`: 问候、一般对话

##### Diet Agent
```python
输入: 食物描述/图片
处理:
  1. 识别食物类型
  2. 估算热量
  3. 评估 GI 值
  4. 判断 IR 适合度
输出: 分析报告 + 建议
```

**关键指标**:
- GI 值分类: Low (<55), Medium (55-70), High (>70)
- 推荐: 低 GI 食物为主
- 避免: 精制碳水、含糖饮料

##### Fitness Agent
```python
输入: HealthKit 数据
处理:
  1. 分析活动量
  2. 评估运动强度
  3. 对比目标值
  4. 生成鼓励话语
输出: 活动分析 + 运动计划
```

**目标值**:
- 步数: 8,000-10,000/天
- 活动能量: 400-600 kcal/天
- 运动时长: 30-60 分钟/天

##### Medical Agent
```python
输入: 医疗记录图片/PDF
处理:
  1. OCR 文本识别
  2. 提取关键指标
  3. 对比正常范围
  4. 识别趋势
输出: 指标摘要 + 健康洞察
```

**关键指标**:
- 空腹胰岛素: <25 mIU/L
- HOMA-IR: <2
- HbA1c: <5.7%
- 空腹血糖: <100 mg/dL

### 3. 记忆管理层

#### 3.1 Memory Manager
```python
class MemoryManager:
    - create_daily_log()      # 创建每日日志
    - append_to_daily_log()   # 追加内容
    - save_medical_record()   # 保存医疗记录
    - save_chat_log()         # 保存对话
    - search_memories()       # 搜索记忆
    - get_user_context()      # 获取用户上下文
```

#### 3.2 Markdown 模板

##### 每日日志模板
```markdown
# Daily Log - 2023-10-27

## Summary
[AI 生成的每日摘要]

## 🍽️ Diet Log
### Meal 1 - 08:00
**Food**: 燕麦粥
**Calories**: 300 kcal
**GI Value**: Low
**Analysis**: 优秀的低 GI 选择

## 🏃 Fitness & Activity
**Steps**: 10,000
**Active Energy**: 500 kcal
**Analysis**: 达到推荐目标

## 💬 Key Conversations
[对话摘要]
```

### 4. 存储层

#### 4.1 Storage Interface (抽象)
```python
class StorageInterface(ABC):
    async def save(path, content, metadata)
    async def load(path)
    async def list(path, pattern, recursive)
    async def search(path, query, file_pattern)
```

**设计原则**:
- 解耦: 业务逻辑与存储实现分离
- 可扩展: 支持切换到 S3/OSS/数据库
- 统一接口: 所有存储操作通过接口

#### 4.2 Local Storage (实现)
```python
class LocalStorage(StorageInterface):
    base_dir = "./data"
    
    # 安全检查: 防止路径遍历
    # 元数据支持: .meta 文件
    # 递归搜索: glob 模式匹配
```

## 数据流图

### 1. 用户注册/登录流程
```
iOS App → POST /auth/register → FastAPI
                ↓
          创建用户 (bcrypt 加密密码)
                ↓
          返回用户信息
                ↓
iOS App → POST /auth/login → FastAPI
                ↓
          验证密码
                ↓
          生成 JWT token
                ↓
iOS App ← 返回 token
                ↓
          保存 token 到 UserDefaults
```

### 2. 对话交互流程
```
用户输入消息 → iOS App
        ↓
  POST /chat/message (with token)
        ↓
  Router Agent 分析意图
        ↓
  路由到专业 Agent (Diet/Fitness/Medical)
        ↓
  Agent 处理 + 生成响应
        ↓
  Memory Manager 保存对话
        ↓
  返回响应 → iOS App
        ↓
  显示 AI 回复
```

### 3. HealthKit 同步流程
```
iOS App → HealthKitManager.fetchLast24HoursData()
        ↓
  读取步数、心率等数据
        ↓
  POST /health/sync-health (with token)
        ↓
  Memory Manager.append_to_daily_log()
        ↓
  更新每日日志
        ↓
  返回成功 → iOS App
```

## 安全设计

### 认证与授权
1. **密码安全**: bcrypt 加盐哈希
2. **Token 安全**: JWT with HMAC-SHA256
3. **Token 过期**: 7 天有效期
4. **路径安全**: 防止路径遍历攻击

### 数据隐私
1. **本地存储**: 用户数据按 user_id 隔离
2. **访问控制**: 每个请求验证 token
3. **数据加密**: HTTPS 传输 (生产环境)

## 可扩展性设计

### 1. Storage Interface
```python
# 当前: Local Storage
storage = LocalStorage("./data")

# 未来: S3 Storage
storage = S3Storage(bucket="healthguard", region="us-west-2")

# 未来: Database Storage
storage = DatabaseStorage(connection_string="...")
```

### 2. Agent System
```python
# 添加新 Agent
class NutritionAgent(BaseAgent):
    async def process_request(self, message, context):
        # 专门的营养分析逻辑
        pass

# 在 Orchestrator 中注册
orchestrator.register_agent("nutrition", NutritionAgent())
```

### 3. LLM Integration
```python
# 当前: 占位符实现
async def call_llm(messages):
    return "Placeholder response"

# 未来: OpenAI
async def call_llm(messages):
    response = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=messages
    )
    return response.choices[0].message.content

# 未来: Anthropic
async def call_llm(messages):
    response = await anthropic.messages.create(
        model="claude-3-opus",
        messages=messages
    )
    return response.content[0].text
```

## 性能优化

### 后端优化
1. **异步 I/O**: FastAPI + asyncio
2. **并发处理**: uvicorn workers
3. **缓存**: 用户上下文缓存 (未来)
4. **连接池**: 数据库连接池 (未来)

### iOS 优化
1. **异步网络**: URLSession + async/await
2. **后台同步**: Background fetch
3. **本地缓存**: CoreData/SwiftData (未来)
4. **图片压缩**: 上传前压缩

## 监控与日志

### 后端日志
- API 请求日志
- Agent 执行日志
- 错误追踪
- 性能指标

### iOS 日志
- 网络请求日志
- HealthKit 同步日志
- 崩溃报告
- 用户行为分析

## 部署架构

### 开发环境
```
iOS Simulator → localhost:8000 (FastAPI)
Physical Device → {Mac IP}:8000 (FastAPI)
```

### 生产环境
```
iOS App → HTTPS → Load Balancer
                      ↓
              FastAPI (Docker)
                      ↓
              S3 / Database
```

## 未来路线图

### Phase 1-4 ✅ (已完成)
- 基础架构
- 认证系统
- Multi-Agent 系统
- HealthKit 集成

### Phase 5 🔄 (进行中)
- 完整 UI 实现
- 语音输入
- 图片上传
- 单元测试

### Phase 6+ 📅 (计划中)
- LLM API 集成
- Web Search Tool
- OCR 实现
- 推送通知
- 数据可视化
- 云部署

## 参考文档

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SwiftUI 文档](https://developer.apple.com/documentation/swiftui)
- [HealthKit 文档](https://developer.apple.com/documentation/healthkit)
- [JWT 规范](https://jwt.io/)
