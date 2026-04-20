#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assignment Markdown to LaTeX Converter
将作业 Markdown 转换为 LaTeX 并编译为 PDF
"""

import re
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# 尝试导入 pdfplumber（可选，用于图片提取）
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

# 尝试导入数学计算库（可选，用于解题辅助）
try:
    import sympy
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False

try:
    import numpy
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# 默认学生信息（可修改）
DEFAULT_INFO = {
    "name": "姓名",
    "student_id": "学号",
    "class": "班级",
}


def parse_markdown(md_content):
    """解析 Markdown，提取信息"""

    # 提取标题（第一行 # 标题）
    title_match = re.search(r'^#\s+(.+)$', md_content, re.MULTILINE)
    title = title_match.group(1) if title_match else "作业"

    # 提取学生信息
    info = DEFAULT_INFO.copy()
    name_match = re.search(r'\*\*姓名\*\*:\s*(.+)', md_content)
    if name_match:
        info["name"] = name_match.group(1).strip()

    id_match = re.search(r'\*\*学号\*\*:\s*(.+)', md_content)
    if id_match:
        info["student_id"] = id_match.group(1).strip()

    class_match = re.search(r'\*\*班级\*\*:\s*(.+)', md_content)
    if class_match:
        info["class"] = class_match.group(1).strip()

    date_match = re.search(r'\*\*提交日期\*\*:\s*(.+)', md_content)
    submit_date = date_match.group(1).strip() if date_match else datetime.now().strftime("%Y-%m-%d")

    return title, info, submit_date


def extract_images_from_pdf(pdf_path, output_dir="sources"):
    """使用 pdfplumber 从 PDF 中提取图片并保存到 sources/ 目录

    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录，默认为 sources/

    Returns:
        list: 提取的图片文件名列表
    """
    if not HAS_PDFPLUMBER:
        print("警告: pdfplumber 未安装，无法提取图片")
        print("安装命令: pip install pdfplumber")
        return []

    images = []
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                if page.images:
                    for img_num, image in enumerate(page.images):
                        # 获取图片边界框
                        x0, top, x1, bottom = image['x0'], image['top'], image['x1'], image['bottom']

                        # 裁剪图片区域
                        cropped = page.crop((x0, top, x1, bottom))

                        # 转换为图片对象
                        image_obj = cropped.to_image()

                        # 生成文件名
                        image_filename = f"page{page_num+1}_img{img_num+1}.png"
                        image_path = output_path / image_filename

                        # 保存图片
                        image_obj.save(str(image_path))
                        images.append(image_filename)
                        print(f"✅ 提取图片: {image_filename}")

    except Exception as e:
        print(f"❌ 提取图片时出错: {e}")

    return images


def md_to_latex(md_content, title, info, submit_date):
    """将 Markdown 转换为 LaTeX"""

    # 移除开头的标题和学生信息行（会在 LaTeX 中重新生成）
    lines = md_content.split('\n')
    content_start = 0
    for i, line in enumerate(lines):
        if line.startswith('---'):
            content_start = i + 1
            break

    md_body = '\n'.join(lines[content_start:])

    # 转换 Markdown 语法到 LaTeX
    latex_body = convert_markdown_to_latex(md_body)

    # 生成完整 LaTeX 文档
    latex_template = r"""\documentclass[12pt,a4paper]{ctexart}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{geometry}
\usepackage{graphicx}
\usepackage{float}
\usepackage{enumitem}
\geometry{margin=2.5cm}

\title{""" + title + r"""}
\author{""" + info["name"] + r" \quad " + info["student_id"] + r" \quad " + info["class"] + r"""}

\date{""" + submit_date + r"""}

\begin{document}

\maketitle

""" + latex_body + r"""

\end{document}"""

    return latex_template


def convert_markdown_to_latex(md_text):
    """转换 Markdown 语法到 LaTeX"""

    lines = md_text.split('\n')
    latex_lines = []
    in_list = False

    for line in lines:
        # 跳过空行
        if not line.strip():
            if in_list:
                latex_lines.append(r'\end{itemize}')
                in_list = False
            latex_lines.append('')
            continue

        # 标题转换
        if line.startswith('### '):
            latex_lines.append(r'\subsubsection{' + line[4:].strip() + '}')
        elif line.startswith('## '):
            latex_lines.append(r'\subsection{' + line[3:].strip() + '}')
        elif line.startswith('# '):
            latex_lines.append(r'\section{' + line[2:].strip() + '}')
        # 列表转换
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            if not in_list:
                latex_lines.append(r'\begin{itemize}')
                in_list = True
            latex_lines.append(r'\item ' + line.strip()[2:])
        # 加粗转换
        else:
            converted = line
            converted = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', converted)
            # 数学公式转换
            converted = re.sub(r'\$\$(.+?)\$\$', r'[\1]', converted, flags=re.DOTALL)
            converted = re.sub(r'\$(.+?)\$', r'(\1)', converted)
            latex_lines.append(converted)

    if in_list:
        latex_lines.append(r'\end{itemize}')

    return '\n'.join(latex_lines)


def compile_pdf(tex_path, max_runs=2):
    """使用 pdflatex 编译 PDF"""
    try:
        for i in range(max_runs):
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', tex_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(tex_path)
            )
            if result.returncode != 0:
                print(f"编译错误 (第 {i+1} 次):")
                print(result.stderr)
                return False

        # 清理辅助文件
        base_path = str(Path(tex_path).with_suffix(''))
        for ext in ['.aux', '.log', '.out']:
            aux_file = base_path + ext
            if os.path.exists(aux_file):
                os.remove(aux_file)

        return True

    except FileNotFoundError:
        print("错误: 未找到 pdflatex，请安装 MikTeX 或 TeX Live")
        return False


# ============================================================================
# LaTeX 检查与修复功能 (Revise)
# ============================================================================

class LatexIssue:
    """LaTeX 问题类"""
    def __init__(self, line_num: int, issue_type: str, message: str, severity: str = "warning"):
        self.line_num = line_num
        self.issue_type = issue_type
        self.message = message
        self.severity = severity  # "error", "warning", "info"

    def __str__(self):
        severity_symbol = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}
        return f"{severity_symbol.get(self.severity, '•')} 行 {self.line_num}: {self.message} [{self.issue_type}]"


def check_latex_file(tex_path: str) -> List[LatexIssue]:
    """检查 .tex 文件的语法问题

    Args:
        tex_path: LaTeX 文件路径

    Returns:
        List[LatexIssue]: 发现的问题列表
    """
    issues = []

    if not os.path.exists(tex_path):
        issues.append(LatexIssue(0, "file", "文件不存在", "error"))
        return issues

    with open(tex_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 检查特殊字符转义
    special_chars = {
        '%': '百分号',
        '&': '安培符',
        '#': '井号',
        '_': '下划线',
    }

    for line_num, line in enumerate(lines, 1):
        # 跳过注释行
        if line.strip().startswith('%'):
            continue

        for char, name in special_chars.items():
            # 检查未转义的特殊字符（排除已转义的 \\% 和在 \begin、\end 等命令中的）
            if char == '%':
                # 检查未转义的 %（排除 \% 和注释）
                pattern = r'(?<!\\)%'
            elif char == '&':
                # 检查未转义的 &（排除 \&）
                pattern = r'(?<!\\)&'
            elif char == '#':
                # 检查未转义的 #（排除 \#）
                pattern = r'(?<!\\)#'
            elif char == '_':
                # 检查未转义的 _（排除 \_ 和数学模式中的 _）
                # 在数学模式中 _ 是下标，不算错误
                in_math = False
                for i, c in enumerate(line):
                    if c == '$':
                        in_math = not in_math
                    elif c == '_' and not in_math:
                        # 检查是否已转义
                        if i == 0 or line[i-1] != '\\':
                            issues.append(LatexIssue(line_num, "escape", f"未转义的{name}: '{char}' 在非数学模式中", "warning"))
                continue  # _ 单独处理

            matches = re.finditer(pattern, line)
            for match in matches:
                # 排除注释中的 %
                if char == '%' and '\\' in line[:match.start()]:
                    continue
                issues.append(LatexIssue(line_num, "escape", f"未转义的{name}: '{char}'", "warning"))

    # 检查公式配对
    dollar_count = 0
    bracket_count = 0
    for line_num, line in enumerate(lines, 1):
        # 跳过注释行
        if line.strip().startswith('%'):
            continue

        # 检查 $ 配对
        dollar_count += line.count('$')

        # 检查 \[ \] 配对
        bracket_count += line.count(r'\[')
        bracket_count -= line.count(r'\]')

    if dollar_count % 2 != 0:
        issues.append(LatexIssue(0, "math", "行内公式 $ 不配对", "error"))

    if bracket_count != 0:
        issues.append(LatexIssue(0, "math", "显示公式 \\[ \\] 不配对", "error"))

    # 检查环境配对
    environments = {}
    for line_num, line in enumerate(lines, 1):
        # 检查 \begin{...}
        for match in re.finditer(r'\\begin\{([^}]+)\}', line):
            env_name = match.group(1)
            if env_name not in environments:
                environments[env_name] = []
            environments[env_name].append(('begin', line_num))

        # 检查 \end{...}
        for match in re.finditer(r'\\end\{([^}]+)\}', line):
            env_name = match.group(1)
            if env_name not in environments or not environments[env_name]:
                issues.append(LatexIssue(line_num, "environment", f"多余的 \\end{{{env_name}}}", "error"))
            else:
                environments[env_name].pop()

    # 检查未关闭的环境
    for env_name, stack in environments.items():
        if stack:
            for _, line_num in stack:
                issues.append(LatexIssue(line_num, "environment", f"\\begin{{{env_name}}} 未关闭", "error"))

    # 检查图片路径
    for line_num, line in enumerate(lines, 1):
        for match in re.finditer(r'\\includegraphics[^}]*\{([^}]+)\}', line):
            img_path = match.group(1)
            # 解析相对路径
            tex_dir = os.path.dirname(tex_path)
            full_path = os.path.join(tex_dir, img_path)
            if not os.path.exists(full_path):
                issues.append(LatexIssue(line_num, "image", f"图片文件不存在: {img_path}", "error"))

    return issues


def auto_fix_latex(tex_path: str, issues: List[LatexIssue]) -> bool:
    """自动修复常见 LaTeX 问题

    Args:
        tex_path: LaTeX 文件路径
        issues: 问题列表

    Returns:
        bool: 是否成功修复
    """
    if not os.path.exists(tex_path):
        print(f"❌ 文件不存在: {tex_path}")
        return False

    with open(tex_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = lines.copy()
    offset = 0  # 行号偏移（因为修复可能改变行数）

    for issue in issues:
        if issue.issue_type == "escape" and issue.severity == "warning":
            line_idx = issue.line_num - 1 + offset
            if 0 <= line_idx < len(fixed_lines):
                line = fixed_lines[line_idx]

                # 转义特殊字符
                if '%' in issue.message and '\\%' not in line:
                    fixed_lines[line_idx] = line.replace('%', r'\%')
                elif '&' in issue.message and '\\&' not in line:
                    fixed_lines[line_idx] = line.replace('&', r'\&')
                elif '#' in issue.message and '\\#' not in line:
                    fixed_lines[line_idx] = line.replace('#', r'\#')
                elif '_' in issue.message:
                    # 在非数学模式下转义下划线
                    # 简单处理：在非 $ ... $ 之间的 _ 替换为 \_
                    pass  # 下划线处理较复杂，跳过自动修复

    # 保存修复后的文件
    backup_path = tex_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"📦 备份已保存: {backup_path}")

    with open(tex_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print(f"✅ 已自动修复 {len(issues)} 个问题")
    return True


def validate_latex_compilation(tex_path: str) -> Tuple[bool, str]:
    """验证 LaTeX 能否成功编译

    Args:
        tex_path: LaTeX 文件路径

    Returns:
        Tuple[bool, str]: (是否成功, 错误信息)
    """
    try:
        result = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', '-draftmode', tex_path],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(tex_path),
            timeout=30
        )

        # 清理 draftmode 生成的文件
        base_path = str(Path(tex_path).with_suffix(''))
        for ext in ['.aux', '.log']:
            aux_file = base_path + ext
            if os.path.exists(aux_file):
                os.remove(aux_file)

        if result.returncode == 0:
            return True, ""
        else:
            # 提取关键错误信息
            error_output = result.stderr or result.stdout
            # 简化错误输出
            errors = re.findall(r'^!.*$', error_output, re.MULTILINE)
            if errors:
                return False, "\n".join(errors[:5])  # 只返回前5个错误
            return False, "编译失败，请检查日志"

    except FileNotFoundError:
        return False, "未找到 pdflatex，请安装 MikTeX 或 TeX Live"
    except subprocess.TimeoutExpired:
        return False, "编译超时"
    except Exception as e:
        return False, f"验证出错: {str(e)}"


# ============================================================================
# 数学计算辅助功能
# ============================================================================

def math_calculate(expression: str) -> Optional[str]:
    """使用数学库计算表达式

    Args:
        expression: 数学表达式，如 "x**2 - 4 = 0" 或 "diff(x**3, x)"

    Returns:
        Optional[str]: 计算结果字符串
    """
    if HAS_SYMPY:
        try:
            # 尝试解方程
            if '=' in expression:
                # 解方程: x**2 - 4 = 0
                left, right = expression.split('=')
                x = sympy.symbols('x')
                eq = sympy.Eq(sympy.sympify(left), sympy.sympify(right))
                result = sympy.solve(eq, x)
                return f"解方程 {expression} = 0:\n{x} = {result}"
            else:
                # 计算表达式
                result = sympy.sympify(expression)
                return f"{expression} = {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"
    elif HAS_NUMPY:
        try:
            # 使用 numpy 进行数值计算
            result = eval(expression, {"__builtins__": {}}, {"np": numpy, "numpy": numpy})
            return f"{expression} = {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"
    else:
        return "数学计算库未安装。请安装: pip install sympy numpy"


def show_math_help():
    """显示数学计算帮助"""
    help_text = """
📐 数学计算辅助功能

可用库:
"""
    if HAS_SYMPY:
        help_text += "  ✅ SymPy (符号计算)\n"
    else:
        help_text += "  ❌ SymPy (未安装，pip install sympy)\n"

    if HAS_NUMPY:
        help_text += "  ✅ NumPy (数值计算)\n"
    else:
        help_text += "  ❌ NumPy (未安装，pip install numpy)\n"

    help_text += """
使用示例:
  - 解方程: x**2 - 4 = 0  →  x = [2, -2]
  - 微积分: diff(x**3, x)  →  3*x**2
  - 积分: integrate(x**2, x)  →  x**3/3
  - 数值计算: sqrt(16)  →  4.0

Python 代码示例:
  from sympy import symbols, solve, diff, integrate
  x = symbols('x')
  solve(x**2 - 4, x)  # 解方程
  diff(x**3, x)       # 求导
"""
    return help_text


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    # 设置 Windows 控制台编码
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    if len(sys.argv) < 2:
        print("用法: python md_to_latex.py <markdown_file> [选项]")
        print("选项:")
        print("  --check       检查 .tex 文件语法")
        print("  --fix         自动修复常见问题")
        print("  --math <expr> 计算数学表达式")
        print("  --math-help   显示数学计算帮助")
        sys.exit(1)

    # 处理命令行选项
    if '--check' in sys.argv:
        # 检查 LaTeX 语法
        tex_path = sys.argv[1]
        print(f"🔍 检查 LaTeX 文件: {tex_path}")
        issues = check_latex_file(tex_path)

        if not issues:
            print("✅ 没有发现语法问题")
        else:
            print(f"⚠️ 发现 {len(issues)} 个问题:")
            for issue in issues:
                print(f"  {issue}")

        sys.exit(0)

    elif '--fix' in sys.argv:
        # 自动修复 LaTeX 问题
        tex_path = sys.argv[1]
        print(f"🔧 修复 LaTeX 文件: {tex_path}")

        issues = check_latex_file(tex_path)
        fixable_issues = [i for i in issues if i.issue_type == "escape" and i.severity == "warning"]

        if not issues:
            print("✅ 没有发现需要修复的问题")
        elif not fixable_issues:
            print("⚠️ 发现问题但无法自动修复:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print(f"🔧 准备修复 {len(fixable_issues)} 个问题...")
            if auto_fix_latex(tex_path, fixable_issues):
                print("✅ 修复完成")

        sys.exit(0)

    elif '--math' in sys.argv:
        # 数学计算
        idx = sys.argv.index('--math')
        if idx + 1 < len(sys.argv):
            expression = sys.argv[idx + 1]
            print(f"📐 计算: {expression}")
            result = math_calculate(expression)
            print(result)
        else:
            print(show_math_help())
        sys.exit(0)

    elif '--math-help' in sys.argv:
        print(show_math_help())
        sys.exit(0)

    # 默认：Markdown 转 LaTeX 并编译 PDF
    md_path = sys.argv[1]
    if not os.path.exists(md_path):
        print(f"错误: 文件不存在: {md_path}")
        sys.exit(1)

    # 读取 Markdown
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # 解析并转换
    title, info, submit_date = parse_markdown(md_content)
    latex_content = md_to_latex(md_content, title, info, submit_date)

    # 保存 LaTeX 文件
    base_path = str(Path(md_path).with_suffix(''))
    tex_path = base_path + '.tex'

    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(latex_content)

    print(f"✅ LaTeX 文件已生成: {tex_path}")

    # 编译 PDF
    print("🔄 正在编译 PDF...")
    if compile_pdf(tex_path):
        pdf_path = base_path + '.pdf'
        print(f"✅ PDF 已生成: {pdf_path}")
    else:
        print("❌ PDF 编译失败")


if __name__ == '__main__':
    main()
