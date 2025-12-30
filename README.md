# CVEhunter：集成式 AI 代码审计与漏洞验证工具（Windows）

![Build](https://img.shields.io/badge/build-ready-brightgreen) ![Platform](https://img.shields.io/badge/platform-Windows-blue) ![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![Focus](https://img.shields.io/badge/focus-security-critical)

[中文](#cvehunter集成式-ai-代码审计与漏洞验证工具windows) | [English](#cvehunter-integrated-ai-assisted-code-auditing-toolkit-windows)

**CVEhunter** 面向本地测试环境：把“看代码 → 找疑点 → 生成 PoC → 复现验证 → 归档报告”串成一条高效率工作流。

只能说可堪一用的工具，主要针对phpstudy可部署的项目。可以看《操作手册.pdf》快速了解使用方法。小Bug就见笑了。

2.0将会从基本架构开始进行重大的升级。

---

## 亮点功能

### 1）项目级工作流
* **文件浏览与编辑**：快速定位、检索、重命名与管理项目文件。
* **上下文分析**：支持读取项目结构、批量加载关键文件，降低上下文丢失。

### 2）审计助手（提示词驱动）
* **结构化输出**：按统一模板输出结论，字段完整、格式稳定，便于归档与复核。
* **可直接运行的 PoC**：输出可运行的验证脚本片段，降低复现成本。

### 3）报告与验证
* **模板化报告**：内置中英文模板，按字段填充并生成审计报告。
* **SQLmap 集成**：在工具内配置并执行，统一收集与保存输出结果。

---

## 环境要求
* Windows 10/11
* Python 3.8+
* 安装依赖：

```bash
pip install -r requirements.txt
```

---

## 快速开始

```bash
python run_app.py
```

* 备用入口：`python main_app.py`
* 打开项目：使用左侧文件浏览器选择目标项目根目录。

### SQLmap（可选）
* 在“设置”中填写路径：
  * `<sqlmap_path>\sqlmap.py` 或 `<sqlmap_path>\sqlmap.bat`
* 留空时会尝试自动探测应用根目录下的 `sqlmap/`（若存在）。

---

## 目录结构

```text
CVEhunter/
├── core/        # 核心逻辑（AI 交互、文件浏览、编辑器）
├── ui/          # 窗口与组件
├── managers/    # 模型 / 对话 / 设置管理
├── utils/       # 输出与通知
├── prompts/     # 提示词模板
├── templates/   # 报告模板（zh/en）
├── assets/      # icon.ico / icon.png
├── data/        # 本地 JSON 配置（models/settings）
├── run_app.py   # 推荐入口
└── main_app.py  # 主界面实现
```

---

## 打包发行

```bash
python scripts/build_release.py
```

* 发行说明与校验值见：`发布说明.md`

---

## 合规提示
* 仅用于授权范围内的安全测试与本地验证场景。

---

# CVEhunter: Integrated AI-Assisted Code Auditing Toolkit (Windows)

**CVEhunter** is designed for local test environments, streamlining the workflow from “code review → findings → PoC generation → verification → reporting”.

---

## Key Features

### 1) Project-Centric Workflow
* **File Browser & Editor**: quickly locate, search, rename, and manage project files.
* **Context-Aware Analysis**: load project structure and key files to reduce context loss.

### 2) Audit Assistant (Prompt-Driven)
* **Structured Output**: stable, template-aligned results for easy review and archiving.
* **Runnable PoC Snippets**: produces runnable verification scripts to reduce reproduction cost.

### 3) Reporting & Verification
* **Template-Based Reports**: built-in zh/en templates for consistent report generation.
* **SQLmap Integration**: configure and execute in-app, with unified output collection.

---

## Requirements
* Windows 10/11
* Python 3.8+

```bash
pip install -r requirements.txt
```

---

## Quick Start

```bash
python run_app.py
```

* Alternative entry: `python main_app.py`

### SQLmap (Optional)
* Set path in “设置”:
  * `<sqlmap_path>\sqlmap.py` or `<sqlmap_path>\sqlmap.bat`
* If empty, CVEhunter tries to auto-detect `sqlmap/` under the application root (if present).

---

## Project Structure

```text
CVEhunter/
├── core/        # Core logic (AI interaction, file browsing, editor)
├── ui/          # Windows & widgets
├── managers/    # Models / chats / settings managers
├── utils/       # Output & notifications
├── prompts/     # Prompt templates
├── templates/   # Report templates (zh/en)
├── assets/      # icon.ico / icon.png
├── data/        # Local JSON configs (models/settings)
├── run_app.py   # Recommended entry
└── main_app.py  # Main GUI implementation
```

---

## Release Packaging

```bash
python scripts/build_release.py
```

* Release notes and checksums: see `发布说明.md`.

---

## Compliance Notice
* Only use CVEhunter for authorized testing and local verification environments.
