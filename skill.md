---
name: assignment
description: 大学作业管理系统 - 读取作业文档转为MD，用 `/assignment complete` 自动完成解答，用 `/assignment done` 编译PDF。
---

# Assignment Skill - 大学作业管理系统

自动化大学作业处理：读取作业文档 → 转换为 Markdown → 自动完成解答 → 编译为 PDF。

## Overview

这个 skill 帮助你：
1. **创建作业文件夹** - 按格式 `姓名_学号_班级_课程_作业序号` 自动命名
2. **读取作业文档** - 支持 PDF、DOCX 格式
3. **转换为 Markdown** - 提取文字、公式、图片到 .md
4. **自动完成解答** - 使用 `/assignment complete` 逐题完成，遇到疑问时询问
5. **编译 PDF** - 使用 `/assignment done` 触发 MikTeX 编译

## Workflow

### Step 1: 收集作业信息

询问用户以下信息：
| 字段 | 说明 | 示例 |
|------|------|------|
| 姓名 | 学生姓名 | 张三 |
| 学号 | 10位学号 | 2023010001 |
| 班级 | 班级名称 | 机械01 |
| 课程 | 课程名称 | 材料加工1 |
| 作业序号 | 作业编号 | 作业8 |

### Step 2: 询问作业文档

**重要**：询问用户作业文档的路径
```
"请提供作业文档的路径（支持 PDF 或 DOCX）"
```

支持的格式：
- `.pdf` - PDF 文档
- `.docx` - Word 文档
- `.md` - Markdown 文件（已有内容）

### Step 3: 创建文件夹结构

在课程目录下创建：
```
课程名/作业/姓名_学号_班级_课程_作业序号/
├── 姓名_学号_班级_课程_作业序号.md    # Markdown源文件
├── 姓名_学号_班级_课程_作业序号.tex   # LaTeX文件（done时生成）
├── 姓名_学号_班级_课程_作业序号.pdf   # PDF输出（done时编译）
└── sources/                          # 图片目录（提取的图片）
```

### Step 4: 读取并转换文档

根据文档类型进行处理：

#### A. PDF 文档
- 使用 Read 工具读取 PDF 内容
- 提取文字内容
- 提取图片（如果有）
- 保存到 .md 文件

**图片处理工作流程**：
1. 使用 `pdfplumber` 从 PDF 中提取图片
2. 保存图片到 `sources/` 目录
3. 在 .md 中添加图片引用：`![描述](sources/pageN_imgM.png)`
4. 在 .tex 中添加 LaTeX 图片代码：`\includegraphics[width=0.8\textwidth]{sources/pageN_imgM.png}`

**图片提取命令**（Python）：
```python
from md_to_latex import extract_images_from_pdf
images = extract_images_from_pdf("作业.pdf", output_dir="sources")
```

#### B. DOCX 文档
- 提示用户先转换为 PDF 或 MD
- 或者使用 lab-report skill 的转换功能

#### C. 已有 MD 文件
- 直接读取并显示内容
- 准备编辑

### Step 5: 生成 Markdown 模板

```markdown
# [课程名称] - [作业序号]

**姓名**: [姓名] \quad **学号**: [学号] \quad **班级**: [班级]

**提交日期**: [YYYY-MM-DD]

---

[从文档提取的内容...]

---
```

### Step 6: 用户编辑内容

用户在 .md 文件中：
- 添加解答内容
- 修改公式（使用 $$公式$$）
- 添加图片引用

**此时不编译 PDF，节省 token**

### Step 7: 完成并编译（用户触发）

用户输入 `/assignment done` 时：
1. 读取当前 .md 文件
2. 转换为 LaTeX 格式
3. 使用 MikTeX/pdflatex 编译 PDF
4. 输出完成报告

## LaTeX 转换规则

| Markdown | LaTeX |
|----------|-------|
| `# 标题` | `\section{标题}` |
| `## 标题` | `\subsection{标题}` |
| `### 标题` | `\subsubsection{标题}` |
| `$$公式$$` | `\[公式\]` |
| `$公式$` | `\(...$$` |
| `**加粗**` | `\textbf{加粗}` |
| `- 列表` | `\item 列表` |

## LaTeX 模板

```latex
\documentclass[12pt,a4paper]{ctexart}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{geometry}
\usepackage{graphicx}
\usepackage{float}
\usepackage{enumitem}
\geometry{margin=2.5cm}

\title{[课程名称] - [作业序号]}
\author{[姓名] \quad [学号] \quad [班级]}

\date{[提交日期]}

\begin{document}

\maketitle

% 内容从MD转换而来

\end{document}
```

## Usage Examples

```
# 开始新作业
/assignment 材料加工1 作业8

# 系统询问：请提供作业文档路径
# 用户：作业/2026年第3章 作业-3.pdf

# 系统读取文档并转换为 MD
# 用户编辑 MD 文件...

# 完成后编译 PDF
/assignment done
```

## /assignment done 触发器

当用户输入 `/assignment done` 时：
1. 检测当前目录的 .md 文件
2. 转换为 .tex
3. 编译 .pdf
4. 清理临时文件（.aux, .log）

---

## /assignment complete 触发器

当用户输入 `/assignment complete` 时：
**自动完成作业内容** - 逐题分析并解答，遇到疑问时询问用户

### 工作流程

#### Step 1: 读取作业题目
- 从 PDF 或 MD 文件中提取所有题目
- 识别题目类型（计算题、简答题、论述题、证明题等）
- 统计题目数量

#### Step 2: 逐题完成
对每道题目：

**A. 计算题**
- 识别已知条件和求解目标
- 应用相关公式和定理
- 分步骤计算
- 使用 `$$公式$$` 格式书写数学表达式

**B. 简答题/论述题**
- 分析题目核心问题
- 组织知识点和要点
- 分层次作答
- 提供实例或公式支持

**C. 遇到疑问时询问**
当题目信息不完整或不确定时：
- 暂停当前题目
- 向用户询问具体问题
- 等待用户回答后继续

**常见的询问场景**：
```
- 题目中的图表/图片内容不清晰
- 参数值缺失或模糊
- 需要特定的解答格式要求
- 需要使用特定的方法或公式
- 需要知道课程的特定要求
```

#### Step 3: 生成解答
- 将所有解答整理为 Markdown 格式
- 保持与题目相同的编号
- 添加"解答"小节标记
- 使用合适的标题层级（### 或 ####）

#### Step 4: 写入文件
- 更新 .md 文件
- 保留原有题目
- 在每道题后添加解答内容

### 解答格式示例

```markdown
## 题目一

[题目内容...]

### 解答

**分析**：[简要分析题目]

**Step 1：[步骤名称]**

[计算过程或分析...]

$$公式 = 结果$$

**Step 2：[步骤名称]**

[继续计算...]

**答案**：

$$\boxed{最终结果}$$
```

### 题目类型识别规则

| 关键词 | 题目类型 | 解答策略 |
|--------|----------|----------|
| 计算、求解、求、估算 | 计算题 | 分步计算，公式推导 |
| 简述、说明、解释 | 简答题 | 要点列举，简洁明了 |
| 分析、讨论、比较 | 论述题 | 层次分明，深入分析 |
| 证明、推导 | 证明题 | 逻辑严密，步骤完整 |
| 画图、示意图 | 作图题 | 描述图形特征 |

### 中途询问示例

```
# 系统处理题目二时发现疑问
"题目二中提到'如图所示'，但我无法看到图片内容。
请问图中显示的是什么工艺/结构？"

# 用户回答
"是正向挤压工艺，挤压筒直径100mm，挤压杆直径30mm"

# 系统继续完成解答
"明白了，我继续完成题目二的解答..."
```

### Usage Examples

```
# 自动完成作业
/assignment complete

# 系统逐题完成
"正在读取题目... 共发现 4 道题"
"开始完成题目一（计算题）..."
"题目一已完成 ✅"
"开始完成题目二（简答题）..."
"遇到疑问：题目中提到的'如图所示'无法识别"
"请问图中显示的是什么？"
[用户回答后继续]
"题目二已完成 ✅"
...
"所有题目已完成，正在写入文件..."
"✅ 作业内容已保存到 .md 文件"
```

## 编译命令

```bash
pdflatex 姓名_学号_班级_课程_作业序号.tex
pdflatex 姓名_学号_班级_课程_作业序号.tex  # 第二次生成目录
```

## Dependencies

- **MikTeX** 或 **TeX Live** - LaTeX发行版
- **pdflatex** - PDF编译器
- **ctex** - 中文支持
- **Python 3.x** - 转换脚本（可选）
- **pdfplumber** - PDF图片提取（可选，安装：`pip install pdfplumber`）

## 快速命令

```bash
# 创建作业（会询问文档路径）
/assignment [课程] [作业号]

# 自动完成作业内容（遇到疑问会询问）
/assignment complete

# 完成并编译 PDF
/assignment done
```

---

## 命令对比

| 命令 | 功能 | 是否询问 |
|------|------|----------|
| `/assignment 课程 作业号` | 创建作业文件夹，读取题目 | ✅ 询问文档路径 |
| `/assignment complete` | 自动完成所有题目解答 | ⚠️ 遇到疑问时询问 |
| `/assignment done` | 编译 MD 为 PDF | ❌ 不询问 |
| `/assignment revise` | 检查并修复 LaTeX 格式问题 | ⚠️ 发现问题时询问是否修复 |

---

## /assignment revise 触发器

当用户输入 `/assignment revise` 时：

### 功能 1：LaTeX 格式检查与修正

**检查内容**：
- ❌ 特殊字符未转义（`%`, `&`, `#`, `_`）
- ❌ 数学公式配对问题（`$...$`, `\[...\]`）
- ❌ LaTeX 环境配对问题（`\begin...\end`）
- ❌ 图片文件路径存在性

**工作流程**：
1. 检测当前目录的 .tex 文件
2. 运行 LaTeX 语法检查
3. 报告发现的问题（按严重程度分类）
4. 提供自动修复选项
5. 重新编译 PDF 验证修复结果

### 功能 2：数学计算辅助

当遇到计算题时，可以使用以下 Python 库进行数学计算：

| 库 | 功能 | 安装命令 |
|------|------|----------|
| `sympy` | 符号计算（解方程、微积分） | `pip install sympy` |
| `numpy` | 数值计算（矩阵、函数） | `pip install numpy` |
| `scipy` | 科学计算（优化、积分） | `pip install scipy` |

**使用示例**：

```python
# 解方程 x^2 - 4 = 0
from sympy import symbols, solve, Eq
x = symbols('x')
result = solve(Eq(x**2 - 4, 0), x)  # x = [2, -2]

# 微积分：求导
from sympy import diff
diff(x**3, x)  # 3*x^2

# 微积分：积分
from sympy import integrate
integrate(x**2, x)  # x^3/3

# 数值计算
import numpy as np
np.sqrt(16)  # 4.0
```

**在作业解答中的应用**：

```markdown
### 解答

**Step 1：建立方程**

根据题意，设未知量为 x，得到方程：

$$x^2 - 4 = 0$$

**Step 2：求解方程**

使用 SymPy 解方程：

```python
from sympy import symbols, solve, Eq
x = symbols('x')
solve(Eq(x**2 - 4, 0), x)
```

解得：

$$x = \pm 2$$

**答案**：

$$\boxed{x = 2 \text{ 或 } x = -2}$$
```

### 命令行用法

```bash
# 检查 LaTeX 语法
python md_to_latex.py file.tex --check

# 自动修复问题
python md_to_latex.py file.tex --fix

# 数学计算
python md_to_latex.py --math "x**2 - 4 = 0"

# 查看数学计算帮助
python md_to_latex.py --math-help
```

### 常见问题与修复

| 问题类型 | 示例 | 修复方法 |
|----------|------|----------|
| 未转义百分号 | `完成度 50%` | `完成度 50\%` |
| 未转义安培符 | `A & B` | `A \& B` |
| 未转义下划线 | `file_name` | `file\_name` |
| 公式不配对 | `$x^2 + y^2` | `$x^2 + y^2$` |
| 环境未关闭 | `\begin{itemize}` | 添加 `\end{itemize}` |

### 执行示例

```
# 用户输入
/assignment revise

# 系统响应
🔍 检查 LaTeX 文件: 姓名_学号_班级_课程_作业序号.tex

⚠️ 发现 3 个问题:
  ❌ 行 15: 未转义的百分号: '%' [escape]
  ⚠️ 行 23: 未转义的安培符: '&' [escape]
  ❌ 行 0: \begin{itemize} 未关闭 [environment]

📦 发现 2 个可自动修复的问题
是否自动修复？(y/n)

# 用户选择 y
🔧 准备修复 2 个问题...
📦 备份已保存: 姓名_学号_班级_课程_作业序号.tex.backup
✅ 已自动修复 2 个问题

⚠️ 仍有 1 个问题需要手动处理:
  ❌ 行 0: \begin{itemize} 未关闭 [environment]

请手动修复后重新编译
```
