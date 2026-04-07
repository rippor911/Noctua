# 🦉 Noctua - 智慧猫头鹰论文阅读助手

一个能够读论文、做笔记、建数据库的智能系统，支持基于检索增强生成（RAG）的无幻觉问答。

**特色**：拟人化猫头鹰形象，基于时间的动态语气（白天困倦/夜晚精神），趣味进度反馈（咕咕咕进度条）。

---

## 🌟 功能特点

- **🦉 猫头鹰个性化**：时间感知语气、咕咕咕进度条、可爱错误反馈
- **📄 PDF论文解析**：自动提取PDF文本内容和结构
- **📝 智能笔记生成**：使用LLM自动生成结构化笔记（摘要、要点、方法、结论）
- **🗄️ 向量数据库存储**：基于ChromaDB构建可检索的知识库
- **❓ 无幻觉问答**：基于RAG技术，答案严格限定在论文内容范围内，并标注引用来源
- **🧠 多跳推理**：支持复杂问题的分解和推理

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API密钥

**方式一：使用 .env 文件（推荐）**

复制 `.env.example` 文件为 `.env`，然后填写你的API密钥：

```powershell
copy .env.example .env
```

编辑 `.env` 文件：
```
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
```

**方式二：使用环境变量**

```powershell
# PowerShell
$env:OPENAI_API_KEY="your-api-key"
$env:OPENAI_BASE_URL="your-model-url"

# CMD
set OPENAI_API_KEY="your-api-key"
set OPENAI_BASE_URL="your-model-url"

# bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="your-model-url"
```

### 3. 使用示例

```python
from paper_agent import create_agent

# 创建智能体（启用 Noctua 个性化）
agent = create_agent(api_key="your-api-key", noctua_enabled=True)

# 处理论文
result = agent.process_paper("path/to/paper.pdf")

# 问答
answer = agent.ask("论文的主要贡献是什么？")
print(answer["answer"])
```

---

## 🦉 Noctua 个性化功能

### 时间感知语气

Noctua 会根据当前时间自动调整语气：

- **白天 (6:00 - 18:00)**：困倦模式 😴
  - "哈欠……咕~ 现在是白天，Noctua 好困……但我会努力帮你读论文的……"
  
- **夜晚 (18:01 - 5:59)**：精神模式 ✨
  - "咕咕咕！夜晚才是我的主场！现在很有精神，马上为你服务~"

### 咕咕咕进度条

在等待处理时，Noctua 会显示可爱的咕咕咕进度条：

```
🦉 😴 [●●●●●○○○○○] 咕咕咕 (50%)
```

### API 调用前反应

每次调用 API 前，Noctua 会随机显示一个可爱的反应：

- "咕咕~ 让我翻翻这篇论文……"
- "歪头中……咕……请稍等~"
- "翅膀敲击键盘的声音……哒哒哒……咕！"

### 错误反馈

当发生错误时，Noctua 会用可爱的方式表达：

- **API 饥饿**："咕咕咕……我的肚子饿了……需要 API 密钥才能继续工作……"
- **找不到信息**："咕？我没有找到相关信息……你能换个问法吗？"
- **一般错误**："困到眼花……要不你重新传一下 PDF？咕~"

---

## 💻 命令行使用

```bash
# 处理论文（带 Noctua 个性化）
python -m paper_agent process paper.pdf --tags "机器学习" "深度学习"

# 问答
python -m paper_agent ask "论文的主要贡献是什么？"

# 列出所有论文
python -m paper_agent list

# 列出所有笔记
python -m paper_agent list --notes

# 导出笔记
python -m paper_agent export note_xxx --format markdown --output note.md

# 查看统计信息
python -m paper_agent stats

# 打扫巢穴（清理临时文件）
python -m paper_agent clean

# 禁用个性化（严肃模式）
python -m paper_agent --no-personality process paper.pdf
```

---

## 📁 项目结构

```
Noctua/
├── paper_agent/             # 主包目录
│   ├── __init__.py          # 包入口，导出主要类
│   ├── paper_agent.py       # PaperAgent主类
│   ├── cli.py               # 命令行接口
│   ├── noctua_personality.py # 🦉 Noctua个性化模块
│   └── core/                # 核心模块
│       ├── __init__.py      # 核心模块导出
│       ├── pdf_parser.py    # PDF解析（PyMuPDF/pdfplumber）
│       ├── llm_client.py    # LLM客户端（OpenAI API）
│       ├── note_manager.py  # 笔记生成与管理
│       ├── vector_store.py  # 向量存储（ChromaDB）
│       ├── qa_system.py     # 问答系统（RAG）
│       └── prompts.py       # LLM提示词模板
├── papers/                  # PDF论文存放目录
├── notes/                   # 生成的笔记目录（自动创建）
├── database/                # 向量数据库目录（自动创建）
├── base/                    # 基础数据目录（自动创建）
├── demo.py                  # 交互式演示脚本
├── requirements.txt         # Python依赖
├── .env.example             # 环境变量配置模板
├── .gitignore               # Git忽略文件
└── README.md                # 项目说明
```

---

## 🎭 Noctua 个性化 API

### 创建 Noctua 实例

```python
from paper_agent.noctua_personality import create_noctua

# 启用个性化
noctua = create_noctua(enabled=True)

# 禁用个性化（严肃模式）
noctua = create_noctua(enabled=False)
```

### 常用方法

```python
# 打印启动问候
noctua.print_greeting()

# 打印 API 调用前反应
noctua.print_reaction()

# 打印进度条
noctua.print_progress(0.5, "处理中")  # 50% 进度

# 显示等待动画
noctua.animate_waiting(duration=3.0)

# 打印错误消息
noctua.print_error("general", "错误详情")
noctua.print_error("api_hungry")  # API 饥饿
noctua.print_error("empty")       # 空结果

# 打印答案（带猫头鹰前缀）
noctua.print_answer("这是答案内容")

# 打印统计信息
noctua.print_stats(stats_dict)

# 检查时间切换
msg = noctua.check_time_transition()
if msg:
    print(msg)  # "🌙 咕~ 天黑了，Noctua 现在满血复活啦！"
```

### 进度条上下文管理器

```python
from paper_agent.noctua_personality import NoctuaProgressBar

with NoctuaProgressBar(noctua, "生成笔记") as bar:
    for i in range(100):
        bar.update(i / 100)
        # 执行任务...
```

---

## 🔧 核心模块说明

### 1. PDF解析 (pdf_parser.py)

支持PyMuPDF和pdfplumber两种解析器，提取论文的：
- 全文文本
- 页面内容
- 章节结构
- 元数据（标题、作者、摘要等）

### 2. LLM客户端 (llm_client.py)

封装OpenAI API调用，支持：
- 标准对话
- 流式输出
- 摘要生成
- 关键点提取
- 带引用的问答

### 3. 笔记管理 (note_manager.py)

管理论文笔记的创建、存储和检索：
- 自动生成结构化笔记
- JSON/Markdown导出
- 标签系统
- 引用管理

### 4. 向量存储 (vector_store.py)

基于ChromaDB的向量数据库：
- 文本分块
- 向量索引
- 相似度搜索
- 多论文检索

### 5. 问答系统 (qa_system.py)

实现无幻觉问答的核心模块：
- 检索增强生成（RAG）
- 幻觉检测
- 引用标注
- 多跳推理

---

## 🛡️ 无幻觉策略

本系统采用多种策略确保回答无幻觉：

1. **检索增强生成**：只基于检索到的上下文生成答案
2. **严格提示词**：明确限制LLM只能使用提供的上下文
3. **引用标注**：要求LLM标注每个事实的来源
4. **幻觉检测**：自动检测不确定表达和外部知识
5. **置信度评估**：对答案进行置信度评分
6. **验证机制**：支持多轮验证

---

## 📚 API参考

### PaperAgent 类

```python
from paper_agent import create_agent

# 创建智能体
agent = create_agent(
    api_key="your-api-key",
    model="gpt-4o-mini",
    papers_dir="./papers",
    notes_dir="./notes",
    database_dir="./database",
    noctua_enabled=True  # 启用 Noctua 个性化
)

# 处理论文
result = agent.process_paper(
    file_path="paper.pdf",
    create_note=True,
    add_to_db=True,
    tags=["标签1", "标签2"]
)

# 问答
answer = agent.ask(
    question="问题",
    paper_id=None,  # 指定论文ID，None表示搜索所有论文
    top_k=5,        # 检索数量
    require_citation=True  # 是否要求引用
)

# 复杂问题问答
complex_answer = agent.ask_complex(question, paper_id=None)

# 列出论文
papers = agent.list_papers()

# 列出笔记
notes = agent.list_notes(tags=["标签1"])

# 导出笔记
content = agent.export_note(note_id, format="markdown")

# 获取统计
stats = agent.get_stats()
```

---

## ⚙️ 配置说明

支持两种配置方式（优先级：传入参数 > 环境变量 > .env文件）：

### .env 文件配置（推荐Windows用户使用）

在项目根目录创建 `.env` 文件：

```
# OpenAI API 配置（必填）
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# 模型配置（可选）
MODEL=gpt-4o-mini

# 目录配置（可选）
PAPERS_DIR=./papers
NOTES_DIR=./notes
DATABASE_DIR=./database

# 处理配置（可选）
CHUNK_SIZE=500
CHUNK_OVERLAP=100
TOP_K_RETRIEVAL=5
```

### 环境变量配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| API密钥 | OPENAI_API_KEY | - | OpenAI API密钥 |
| API地址 | OPENAI_BASE_URL | https://api.openai.com/v1 | API基础URL |
| 模型 | MODEL | gpt-4o-mini | 使用的模型 |
| 论文目录 | PAPERS_DIR | ./papers | PDF文件存放目录 |
| 笔记目录 | NOTES_DIR | ./notes | 笔记存放目录 |
| 数据库目录 | DATABASE_DIR | ./database | 向量数据库目录 |
| 分块大小 | CHUNK_SIZE | 500 | 文本分块大小 |
| 分块重叠 | CHUNK_OVERLAP | 100 | 文本分块重叠大小 |
| 检索数量 | TOP_K_RETRIEVAL | 5 | 默认检索的上下文数量 |

---

## 🎨 个性化演示

运行演示脚本查看 Noctua 的所有个性化功能：

```bash
python example_noctua.py
```

演示内容包括：
1. 启动问候（白天/夜晚不同）
2. API 调用前反应
3. 咕咕咕进度条
4. 等待动画
5. 错误消息（API 饥饿、空结果等）
6. 统计信息展示

---

## �️ 交互式演示

运行交互式演示脚本体验完整功能：

```bash
python demo.py
```

交互式菜单提供以下功能：
1. **处理论文** - 选择PDF文件并生成笔记和数据库
2. **问答** - 基于论文内容进行无幻觉问答
3. **列出论文** - 查看所有已处理的论文
4. **列出笔记** - 查看所有生成的笔记
5. **统计信息** - 查看数据库和论文统计

---

## 📁 目录结构说明

项目运行后会生成以下目录：

```
Noctua/
├── papers/          # 存放PDF论文文件（需手动放入）
├── notes/           # 自动生成的笔记文件（JSON/Markdown）
├── database/        # 向量数据库存储（ChromaDB）
└── base/            # 基础数据目录
```

> ⚠️ **注意**: `notes/`、`database/`、`base/` 目录会在首次运行时自动创建，无需手动创建。

---

## �� 依赖项

- PyMuPDF >= 1.23.0 - PDF解析
- pdfplumber >= 0.10.0 - PDF文本提取
- openai >= 1.0.0 - LLM API调用
- chromadb >= 0.4.0 - 向量数据库存储
- numpy >= 1.24.0 - 数据处理
- tqdm >= 4.65.0 - 进度条显示
- python-dotenv >= 1.0.0 - 环境变量管理

---

## 📝 License

MIT License

---

## 🙏 致谢

- 参考 [paper-qa](https://github.com/whitead/paper-qa) 的无幻觉问答策略
- 参考 [mad-professor](https://github.com/dheerajnbhat/mad-professor) 的论文解析方法

---

🦉 **咕咕咕~ 祝你阅读愉快！**
