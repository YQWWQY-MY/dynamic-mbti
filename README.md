# AI 动态 MBTI 人格测试系统

软件综合训练（深度学习方向）团队作品。

与传统固定题库的 MBTI 测试不同，本系统由大模型**动态出题**：AI 实时分析每一道回答，
优先针对「置信度最低」的性格维度追问，四个维度全部收敛后自动生成个性化人格报告。

## 核心特性

- **AI 自适应出题**（类 CAT 计算机化自适应测验）：每轮选出置信度最低的维度，由 LLM 生成新情境题，避免重复、避免连续两题测同一维度
- **双通道作答**：预设选项（评分确定）+ 自由文本回答（LLM 语义评分，信息量更大）
- **AI 人格报告**：类型画像、优势短板、职业方向、同类型名人、成长建议
- **数据库支撑的性格档案**：用户/会话/题目/回答/维度状态/报告 六表关联，支持历史报告与**重测性格变化曲线**
- **模拟模式兜底**：未配置 API Key 时使用内置题库离线运行，答辩断网也能演示

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + Element Plus + ECharts |
| 后端 | Python FastAPI + SQLAlchemy |
| 数据库 | SQLite（开发）/ MySQL（部署，改一行配置切换） |
| AI | 智谱 GLM-4-Flash（OpenAI 兼容协议，可一行切换 Qwen/DeepSeek 等） |

## 目录结构

```
dynamic-mbti/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── main.py          # 应用入口
│   │   ├── config.py        # 配置（env 驱动）
│   │   ├── database.py      # SQLAlchemy 引擎
│   │   ├── models.py        # 6 张表的 ORM 模型
│   │   ├── mbti.py          # 自适应测试引擎（维度状态机）
│   │   ├── llm.py           # LLM 客户端（出题/评分/报告 + mock）
│   │   ├── security.py      # 密码哈希 + JWT
│   │   └── routers/         # auth / tests / reports 路由
│   ├── smoke_test.py        # 后端全流程冒烟测试
│   └── requirements.txt
└── frontend/                # Vue3 前端
    └── src/views/           # Login / Test / Result / History 四个页面
```

## 快速开始

### 1. 后端

```bash
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m uvicorn app.main:app --port 8000
```

启动后会提示「模拟模式」。此时整个系统已可完整运行（内置题库、确定性评分、模板报告）。

### 2. 前端

```bash
cd ../frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173 ，注册账号即可开始测试。

### 3. 启用真实 AI（推荐）

1. 注册 https://open.bigmodel.cn （智谱开放平台，手机号即可）
2. 在「API Keys」页面创建 Key（GLM-4-Flash 模型永久免费）
3. 复制配置文件并填入 Key：

```bash
cd backend
copy .env.example .env
# 编辑 .env，填入 LLM_API_KEY=你的Key
```

4. 重启后端，启动日志会显示已接入的模型名称。

### 4. 切换 MySQL（部署/答辩用）

```bash
# MySQL 中建库：CREATE DATABASE mbti DEFAULT CHARACTER SET utf8mb4;
# .env 中修改
DATABASE_URL=mysql+pymysql://root:密码@localhost:3306/mbti?charset=utf8mb4
```

重启后端会自动建表。SQLAlchemy 层抹平差异，业务代码零改动。

## 自适应算法说明（答辩可讲）

1. 四个维度（E/I、S/N、T/F、J/P）各维护 `score`（-8~8 的倾向得分）与 `confidence`（已收集证据量）
2. 每轮出题前，选出**置信度未达标且最低**的维度（排除上一题刚测过的），交由 LLM 生成情境题；每个选项在生成时即带有隐藏的 lean 值（-2~2），**不下发给前端**，防止被选项位置猜出倾向
3. 选择题作答直接采用 lean 作为证据（确定、零成本）；自由文本由 LLM 语义评分
4. `score += evidence`，`confidence += 1.5（选项）/1.2（自由文本）`，四维度 confidence 全部 ≥ 5 或题数达 20 上限即收敛
5. 按各维度得分符号确定 MBTI 类型，交由 LLM 生成报告；维度分数由引擎计算（不信任 LLM 编数字）

## 验证

- 后端冒烟测试（注册→答题→报告→历史→趋势→自由文本评分）：
  `venv\Scripts\python smoke_test.py`
- 前端已浏览器实测：注册、对话式答题（含自由回答）、结果页、历史页全流程通过

## 团队分工建议

- 后端 + 自适应引擎 + 数据库
- 前端四页面 + 可视化
- LLM 提示词调优 + 测试数据 + 答辩 PPT（建议现场演示：同一人隔几天重测，用历史曲线讲「性格测量稳定性」）
