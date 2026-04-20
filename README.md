# GapSight - 跨学科知识盲区探测工具

利用文献共现网络与结构洞算法，自动探测并可视化跨学科知识盲区，辅助科研人员精准定位创新开题方向的智能科研辅助工具。

## 功能特性

### 📚 文献检索与分析
- **Semantic Scholar API 集成**: 无需API Key即可使用公共接口（支持自定义API Key获取更高速率限制）
- **智能关键词搜索**: 支持1-2个关键词进行跨学科探索
- **时间范围筛选**: 可配置回溯年数（默认5年）
- **批量论文获取**: 最多支持100篇高相关度论文分析

### 🔬 学术实体提取
- **scispaCy 模型**: 基于生物医学/科学文本训练的NLP模型
- **核心概念识别**: 自动从论文标题和摘要中提取学术实体
- **智能过滤**: 自动过滤停用词、数字、无意义词汇
- **词形还原**: 统一学术术语的不同形态

### 🕸️ 共现网络构建
- **NetworkX 图网络**: 构建学术概念共现关系网络
- **权重计算**: 基于共现次数计算边权重
- **社区检测**: Louvain算法自动识别研究社区
- **动态可视化**: 支持3D和2D力导向图两种展示模式

### 💡 结构洞算法探测
- **中介中心性 (Betweenness Centrality)**: 识别连接不同社区的"桥梁"节点
- **约束系数 (Constraint)**: 衡量节点受邻居约束的程度
- **有效大小 (Effective Size)**: 计算节点ego网络的非冗余部分
- **知识盲区检测**: 自动识别跨社区间缺失的潜在创新连接

### 🎨 交互式可视化
- **3D 力导向图**: 基于 Three.js 的沉浸式3D体验
- **2D 力导向图**: 基于 D3.js 的经典2D布局
- **自动旋转**: 3D模式下支持自动旋转浏览
- **节点详情**: 点击节点查看结构洞指标
- **知识盲区高亮**: 橙色虚线标识潜在创新连接
- **一键复制提示词**: 点击盲区连接线生成研究建议

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                         前端 (Frontend)                        │
├─────────────────────────────────────────────────────────────┤
│  HTML5 / CSS3 / JavaScript                                   │
│  ├── 3D-Force-Graph (Three.js)  - 3D力导向图可视化          │
│  ├── D3.js                        - 2D力导向图可视化          │
│  └── Vanilla JS                   - 交互逻辑与API调用         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ REST API
┌─────────────────────────────────────────────────────────────┐
│                        后端 (Backend)                          │
├─────────────────────────────────────────────────────────────┤
│  FastAPI - Web框架                                             │
│  ├── 路由层 - API端点定义                                       │
│  ├── 服务层 - 业务逻辑实现                                      │
│  │   ├── SemanticScholarService  - 学术文献检索               │
│  │   ├── EntityExtractor         - 学术实体提取 (scispaCy)    │
│  │   └── NetworkAnalyzer         - 网络分析 (NetworkX)        │
│  └── 模型层 - Pydantic数据模型                                  │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求

- Python 3.8+
- pip (Python包管理器)

### 安装步骤

1. **克隆项目**
```bash
cd GapSight
```

2. **创建虚拟环境 (推荐)**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. **安装后端依赖**
```bash
pip install -r backend/requirements.txt
```

4. **下载 spaCy 模型**
```bash
# 下载轻量级英文模型 (推荐，速度快)
python -m spacy download en_core_web_sm

# 或下载 scispaCy 学术文本模型 (需要先安装 scispacy)
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz
```

5. **配置 API Key (可选)**

创建 `backend/.env` 文件：
```env
SEMANTIC_SCHOLAR_API_KEY=your_api_key_here
```

或者在前端界面的"设置"中输入API Key（实时生效，无需重启服务器）。

> **获取免费API Key**: 访问 https://www.semanticscholar.org/product/api 申请

### 启动服务

```bash
cd /home/ubuntu/GapSight
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

或者直接运行：
```bash
python backend/main.py
```

服务启动后，访问 http://localhost:8000 即可使用。

### API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 使用指南

### 基本流程

1. **输入关键词**: 在左侧面板输入1-2个研究领域关键词（如 "machine learning"）

2. **配置参数 (可选)**:
   - 点击"高级选项"展开更多设置
   - **论文数量**: 10-100篇（默认50篇）
   - **回溯年数**: 1-10年（默认5年）
   - **可视化模式**: 3D或2D力导向图

3. **开始分析**: 点击"开始分析"按钮，系统将：
   - 从 Semantic Scholar 检索相关论文
   - 使用 scispaCy 提取学术实体
   - 构建共现网络并计算结构洞指标
   - 检测潜在知识盲区

4. **探索结果**:
   - **网络可视化**: 查看学术概念的关联关系
   - **节点详情**: 点击节点查看结构洞指标
   - **知识盲区**: 橙色虚线标识潜在创新连接
   - **研究建议**: 点击盲区连接线查看详细分析报告

### 界面功能

#### 左侧面板
- **关键词输入**: 输入1-2个研究领域
- **高级选项**: 配置论文数量、时间范围、可视化模式
- **统计信息**: 显示分析结果的关键指标
- **知识盲区列表**: Top 10潜在创新连接（按评分排序）
- **使用说明**: 快速功能指引

#### 可视化区域
- **3D模式**:
  - 鼠标拖拽: 旋转视角
  - 滚轮: 缩放
  - 点击节点: 查看详情
  - 点击橙色边: 查看研究建议
  - 工具栏: 缩放控制、重置视图、自动旋转开关

- **2D模式**:
  - 鼠标拖拽节点: 调整布局
  - 滚轮: 缩放
  - 点击节点: 查看详情

#### 设置面板
- **Semantic Scholar API Key**: 输入自定义API Key以获得更高请求速率
- 配置自动保存到浏览器 localStorage

## 算法说明

### 结构洞理论

结构洞 (Structural Holes) 由社会学家 Ronald Burt 提出，指两个群体之间缺乏直接连接的"空隙"。在学术网络中，结构洞代表潜在的跨学科创新机会。

### 核心指标

1. **中介中心性 (Betweenness Centrality)**
   - 衡量节点在网络中作为"桥梁"的重要程度
   - 高中介中心性节点连接不同的研究社区
   - 计算公式: 经过该节点的最短路径数量占总最短路径的比例

2. **约束系数 (Constraint)**
   - 衡量节点受其邻居约束的程度
   - 低约束系数表示节点有更多"自由"连接
   - 计算公式: 基于节点与邻居的连接强度

3. **有效大小 (Effective Size)**
   - 衡量节点ego网络的非冗余部分
   - 高效大小表示节点连接多样化的邻居
   - 计算公式: 网络大小减去平均邻居连接度

### 知识盲区检测

系统通过以下规则识别潜在创新连接：

1. **跨社区对**: 不同社区的概念之间没有共现连接
2. **高中介节点对**: 两个高中介中心性节点之间没有连接
3. **低约束对**: 低约束系数节点之间的潜在连接

检测到的盲区按以下评分排序：
```
总分 = 中介中心性 * 0.4 + (1 - 约束系数) * 0.3 + 节点度 * 0.3
```

## 项目结构

```
GapSight/
├── backend/                    # 后端代码
│   ├── main.py                # FastAPI 应用入口
│   ├── config.py              # 配置管理
│   ├── requirements.txt       # Python依赖
│   ├── .env                   # 环境变量 (可选)
│   ├── __init__.py
│   ├── models/                # 数据模型
│   │   ├── __init__.py
│   │   └── schemas.py         # Pydantic模型定义
│   └── services/              # 业务逻辑
│       ├── __init__.py
│       ├── semantic_scholar.py  # Semantic Scholar API服务
│       ├── entity_extractor.py   # 实体提取服务 (scispaCy)
│       └── network_analyzer.py   # 网络分析服务 (NetworkX)
│
├── frontend/                   # 前端代码
│   ├── index.html             # 主页面
│   ├── css/
│   │   └── style.css          # 样式文件
│   └── js/
│       └── app.js             # 应用逻辑
│
└── README.md                  # 本文件
```

## API 参考

### POST /api/search

执行完整的文献搜索与分析流程。

**请求体:**
```json
{
  "keywords": ["machine learning", "drug discovery"],
  "max_papers": 50,
  "years_back": 5,
  "api_key": "optional_api_key",
  "visualization_mode": "3d"
}
```

**响应:**
```json
{
  "nodes": [...],
  "edges": [...],
  "gap_pairs": [...],
  "papers": [...],
  "total_papers": 50,
  "total_entities": 120
}
```

### POST /api/gap-prompt

生成指定知识盲区的研究建议提示词。

**请求体:**
```json
{
  "concept1": "neural network",
  "concept2": "molecular docking",
  "keywords": ["machine learning", "drug discovery"],
  "papers": [...]
}
```

### GET /api/config

获取当前系统配置。

**响应:**
```json
{
  "has_api_key": true,
  "max_papers_limit": 100,
  "default_years_back": 5,
  "scispacy_model": "en_core_sci_sm"
}
```

### GET /api/health

健康检查端点。

## 常见问题

### Q: 为什么需要 Semantic Scholar API Key?

**A:** Semantic Scholar API 支持两种使用方式：
- **无API Key**: 使用公共速率限制（1000请求/秒，所有用户共享）
- **有API Key**: 获取专属速率限制（1请求/秒起步，可申请更高）

对于轻度使用，无需API Key即可正常工作。如果遇到 429 (Too Many Requests) 错误，建议申请免费API Key。

### Q: scispaCy 和普通 spaCy 模型有什么区别?

**A:**
- **scispaCy**: 专门针对生物医学和科学文本训练，对学术术语识别更准确
- **普通 spaCy**: 针对通用文本训练，速度快但学术术语识别略逊

系统会优先尝试加载 scispaCy 模型，如果未安装则回退到普通英文模型。

### Q: 分析一次需要多长时间?

**A:** 典型耗时：
- 论文检索: 1-3秒
- 实体提取: 5-15秒（取决于论文数量）
- 网络分析: 1-3秒

总计约 7-20 秒。

### Q: 如何选择合适的关键词?

**A:** 建议：
- 使用领域核心术语（如 "deep learning" 而非 "AI"）
- 组合两个相关但不完全重叠的领域（如 "transformer" + "protein structure"）
- 避免过于宽泛的术语（如 "science"、"research"）

## 许可证

MIT License

## 致谢

- [Semantic Scholar](https://www.semanticscholar.org/) - 提供免费学术文献API
- [scispaCy](https://allenai.github.io/scispacy/) - 提供科学文本NLP模型
- [NetworkX](https://networkx.org/) - 提供图网络分析库
- [3d-force-graph](https://github.com/vasturiano/3d-force-graph) - 提供3D可视化组件
- [D3.js](https://d3js.org/) - 提供2D可视化组件

## 贡献

欢迎提交 Issue 和 Pull Request！

---

**GapSight** - 让知识盲区成为创新起点 ✨
