# HealthGuard AI - 个人健康助理系统

HealthGuard 是一个专门为胰岛素抵抗 (IR) 用户设计的 AI 驱动的个人健康助理系统。通过多模态交互（文字/语音/图片）和 Apple Health 数据同步，提供针对性的饮食建议、运动鼓励和医疗数据分析。

## 🎯 项目目标

为胰岛素抵抗患者提供：
- 🍽️ **智能饮食分析**：食物 GI 值评估、热量计算、个性化饮食建议
- 🏃 **运动数据追踪**：Apple Health 集成、活动分析、运动计划制定
- 📋 **医疗记录管理**：OCR 识别、健康指标追踪、趋势分析
- 💬 **AI 对话助手**：多 Agent 系统、上下文感知、长期记忆

## 🏗️ 系统架构

### 技术栈

**后端 (Backend)**
- **语言**: Python 3.10+
- **框架**: FastAPI
- **认证**: JWT (JSON Web Token) + bcrypt 密码加密
- **存储**: 本地文件系统 (可扩展至 S3/OSS)
- **AI**: 多 Agent 系统 (Router, Diet, Fitness, Medical)

**客户端 (iOS App)**
- **语言**: Swift 5.9+
- **框架**: SwiftUI
- **集成**: HealthKit, AVFoundation, PhotosUI
- **最低版本**: iOS 16.0+

### 目录结构

```
healthguard/
├── backend/                    # Python FastAPI 后端
│   ├── app/
│   │   ├── agents/            # AI Agent 系统
│   │   │   ├── base_agent.py       # Agent 基类
│   │   │   ├── router_agent.py     # 路由 Agent
│   │   │   ├── diet_agent.py       # 饮食 Agent
│   │   │   ├── fitness_agent.py    # 运动 Agent
│   │   │   ├── medical_agent.py    # 医疗 Agent
│   │   │   └── orchestrator.py     # Agent 编排器
│   │   ├── api/               # REST API 端点
│   │   │   ├── auth.py            # 认证 API
│   │   │   ├── chat.py            # 对话 API
│   │   │   └── health.py          # 健康数据 API
│   │   ├── core/              # 核心业务逻辑
│   │   │   └── memory_manager.py  # 记忆管理器
│   │   ├── models/            # 数据模型
│   │   │   ├── user.py            # 用户模型
│   │   │   └── health.py          # 健康数据模型
│   │   ├── storage/           # 存储接口
│   │   │   ├── interface.py       # 存储接口定义
│   │   │   └── local_storage.py   # 本地存储实现
│   │   ├── templates/         # Markdown 模板
│   │   │   └── markdown_templates.py
│   │   ├── utils/             # 工具函数
│   │   │   └── auth.py            # 认证工具
│   │   ├── config/            # 配置
│   │   │   └── settings.py
│   │   └── main.py            # FastAPI 应用入口
│   ├── requirements.txt       # Python 依赖
│   └── README.md
│
├── ios-app/                   # iOS SwiftUI 应用
│   ├── HealthGuard/
│   │   ├── App/               # 应用入口
│   │   │   └── HealthGuardApp.swift
│   │   ├── Models/            # 数据模型
│   │   │   ├── User.swift
│   │   │   ├── Message.swift
│   │   │   └── HealthData.swift
│   │   ├── Views/             # UI 视图
│   │   │   └── ContentView.swift
│   │   ├── ViewModels/        # 视图模型
│   │   │   └── AuthViewModel.swift
│   │   ├── Services/          # 服务层
│   │   │   ├── APIClient.swift
│   │   │   └── HealthKitManager.swift
│   │   ├── Utils/             # 工具
│   │   │   └── Constants.swift
│   │   └── Info.plist
│   ├── README.md
│   └── SETUP.md               # iOS 设置指南
│
├── data/                      # 本地数据存储 (被 gitignore)
│   └── users/{user_id}/
│       ├── memories/daily_logs/
│       ├── medical/records/
│       └── raw_chats/
│
├── docs/                      # 文档
├── .gitignore
├── LICENSE
└── README.md
```

## 🚀 快速开始

### 后端设置

```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置 SECRET_KEY 等

# 3. 启动服务器
python -m app.main
# 或
uvicorn app.main:app --reload

# 服务器运行在 http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### iOS 应用设置

```bash
# 1. 查看设置指南
cd ios-app
cat SETUP.md

# 2. 在 Xcode 中打开项目
# 3. 更新 Constants.swift 中的 API URL
# 4. 在真实设备上运行 (HealthKit 需要真实设备)
```

## 📡 API 端点

### 认证 (Authentication)

```
POST /auth/register     # 注册新用户
POST /auth/login        # 用户登录
GET  /auth/me           # 获取当前用户信息
```

### 对话 (Chat)

```
POST /chat/message      # 发送消息给 AI 助手
GET  /chat/history      # 获取对话历史
```

### 健康数据 (Health)

```
POST /health/sync-health      # 同步 HealthKit 数据
POST /health/food             # 记录食物
POST /health/medical-record   # 上传医疗记录
GET  /health/records          # 获取医疗记录列表
GET  /health/daily-logs       # 获取每日日志
```

## 🤖 AI Agent 系统

### 多 Agent 架构

1. **Router Agent（路由代理）**
   - 分析用户意图
   - 将请求路由到合适的专业 Agent
   - 支持：饮食、运动、医疗、一般对话

2. **Diet Agent（饮食代理）**
   - 分析食物热量和 GI 值
   - 评估 IR 适合度
   - 提供低 GI 饮食建议

3. **Fitness Agent（运动代理）**
   - 分析 HealthKit 数据
   - 评估运动量
   - 提供个性化运动计划

4. **Medical Agent（医疗代理）**
   - OCR 识别医疗记录
   - 追踪健康指标
   - 分析趋势变化

### Agent 工作流程

```
用户消息 → Router Agent → 识别意图 → 路由到专业 Agent → 生成响应 → 返回用户
                ↓
         记忆管理器（保存上下文）
```

## 🏥 HealthKit 集成

### 支持的健康指标

- ✅ 步数 (Steps)
- ✅ 活动能量 (Active Energy)
- ✅ 心率 (Heart Rate - 平均/最小/最大)
- ✅ 运动时长 (Exercise Time)
- ✅ 步行距离 (Walking/Running Distance)
- ✅ 爬楼层数 (Flights Climbed)

### 数据同步

```swift
// iOS 代码示例
let healthData = try await healthKitManager.fetchLast24HoursData()
try await APIClient.shared.syncHealthData(healthData)
```

## 💾 数据存储架构

### Storage Interface

```python
class StorageInterface(ABC):
    async def save(path, content, metadata)
    async def load(path)
    async def exists(path)
    async def delete(path)
    async def list(path, pattern, recursive)
    async def search(path, query, file_pattern)
    async def get_metadata(path)
    async def append(path, content)
```

### Memory Manager

```python
# 每日日志
/data/users/{user_id}/memories/daily_logs/2023-10-27.md

# 医疗记录
/data/users/{user_id}/medical/records/

# 原始对话
/data/users/{user_id}/raw_chats/
```

## 🔐 安全性

- JWT Token 认证
- bcrypt 密码加密
- 路径遍历防护
- CORS 配置
- HTTPS 推荐 (生产环境)

## 🧪 测试

### 测试后端 API

```bash
# 注册用户
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demo123456"}'

# 登录
curl -X POST "http://localhost:8000/auth/login?username=demo&password=demo123456"

# 发送消息 (需要 token)
curl -X POST "http://localhost:8000/chat/message" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "Hello!"}'
```

## 📝 开发路线图

### ✅ 已完成 (Phase 1-4)

- [x] 后端 API 架构和认证
- [x] 存储接口和本地实现
- [x] 记忆管理系统
- [x] 多 Agent 系统
- [x] iOS HealthKit 集成
- [x] 基础 UI 框架

### 🔄 进行中 (Phase 5)

- [ ] 完整的聊天界面 UI
- [ ] 语音输入 (AVFoundation)
- [ ] 图片上传和食物识别
- [ ] 单元测试和集成测试

### 📅 未来计划

- [ ] LLM API 集成 (OpenAI/Anthropic)
- [ ] Web Search Tool (Tavily/Bing)
- [ ] OCR 功能 (pytesseract)
- [ ] 推送通知
- [ ] 数据可视化
- [ ] 云存储 (S3/OSS)

## 📖 文档

- [后端 API 文档](backend/README.md)
- [iOS 应用文档](ios-app/README.md)
- [iOS 设置指南](ios-app/SETUP.md)

## 🤝 贡献

欢迎贡献！请阅读贡献指南。

## 📄 许可证

MIT License

## 👨‍💻 作者

lRoccoon

---

**注意**: 本项目为教育和演示目的。AI 生成的健康建议仅供参考，不构成医疗建议。请务必咨询专业医疗人员。
