"""
CVEhunter-新一代集成AI代码审计工具 主应用
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import re
from pathlib import Path
from datetime import datetime
from string import Template
from PIL import Image

# 项目内部模块导入，无需添加外部路径

from managers.model_manager import AIModelManager
from managers.chat_manager import ChatManager
from managers.settings_manager import SettingsManager
from ui.model_management_window import ModelManagementWindow
from ui.settings_window import SettingsWindow

# 导入CVEhunter核心组件
from core.file_browser import FileBrowser
from core.code_editor import CodeEditor
from core.ai_code_assistant import AICodeAssistant
from core.breakpoint_manager import BreakpointManager
from utils.code_output_manager import CodeOutputManager
from utils.notification_system import notification_manager, show_info, show_success, show_warning, show_error
from ui.model_management_window import ModelDialog


class AICodeEditorApp:
    """CVEhunter-新一代集成AI代码审计工具 应用"""
    
    def __init__(self):
        # 初始化设置管理器
        self.settings_manager = SettingsManager()
        
        # 应用主题设置
        self.apply_theme_settings()
        
        self.root = ctk.CTk()
        # 准备应用图标资源
        try:
            self.prepare_app_icon_assets()
        except Exception as _e:
            print(f"准备图标资源失败: {_e}")
        self.setup_window()
        
        # 初始化管理器
        data_dir = os.path.join(Path(__file__).parent, "data")
        self.model_manager = AIModelManager(data_dir=str(data_dir))
        self.chat_manager = ChatManager(data_dir=str(data_dir), model_manager=self.model_manager)
        self.breakpoint_manager = BreakpointManager()
        
        # 初始化模板目录与示例模板
        self.ensure_template_dirs_and_examples()
        
        # 当前状态
        self.current_project_path = None
        self.current_file_path = None
        self.current_model_id = None
        self.terminal_panel_expanded = False
        # 新增：模型名称到ID的映射
        self.model_name_to_id = {}
        
        # 创建界面
        self.create_widgets()
        self.load_models()
        
        # 初始化通知系统
        notification_manager.set_root_window(self.root)
        
        # 绑定事件
        self.bind_events()

        # 显示hosts文件配置提示（受设置控制）
        try:
            if self.settings_manager.get_setting("ui.show_hosts_reminder", True):
                self.show_hosts_config_reminder()
        except Exception:
            # 读取设置异常时，默认显示
            self.show_hosts_config_reminder()
    
    def apply_theme_settings(self):
        """应用主题设置（固定为深色主题，移除主题切换）"""
        try:
            ctk.set_appearance_mode("Dark")
            ctk.set_default_color_theme("blue")
        except Exception as e:
            print(f"主题设置失败: {e}")
            try:
                ctk.set_appearance_mode("Dark")
                ctk.set_default_color_theme("blue")
            except Exception:
                pass
    
    def setup_window(self):
        """设置主窗口 - Trae风格"""
        self.root.title("CVEhunter-新一代集成AI代码审计工具")
        self.root.geometry("1600x1000")
        self.root.minsize(1400, 800)
        
        # 设置窗口图标
        try:
            self.apply_window_icon()
        except Exception as _e:
            print(f"设置窗口图标失败: {_e}")
        
        # 居中显示
        self.center_window()

    def get_assets_dir(self) -> Path:
        return Path(__file__).parent / "assets"

    def prepare_app_icon_assets(self):
        """准备应用图标资源路径（优先使用 assets 下的 icon.ico/icon.png）"""
        assets = self.get_assets_dir()
        try:
            assets.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        png_path = assets / "icon.png"
        ico_path = assets / "icon.ico"

        if png_path.exists():
            self._app_icon_png_path = str(png_path)
        if ico_path.exists():
            self._app_icon_ico_path = str(ico_path)
        return

    def apply_window_icon(self):
        """设置窗口图标，优先使用 Windows 的 .ico，其次使用 PNG"""
        assets = self.get_assets_dir()
        ico_path = assets / "icon.ico"
        png_path = assets / "icon.png"
        try:
            if sys.platform.startswith("win") and ico_path.exists():
                self.root.iconbitmap(str(ico_path))
            elif png_path.exists():
                self._window_icon_photo = tk.PhotoImage(file=str(png_path))
                self.root.iconphoto(True, self._window_icon_photo)
            else:
                print("未找到图标资源，窗口图标保持默认")
        except Exception as e:
            print(f"应用窗口图标失败: {e}")
    
    def center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1600 // 2)
        y = (self.root.winfo_screenheight() // 2) - (1000 // 2)
        self.root.geometry(f"1600x1000+{x}+{y}")
    
    def create_widgets(self):
        """创建界面元素 - Trae风格布局"""
        # 主容器 - 使用更现代的布局
        main_container = ctk.CTkFrame(self.root, corner_radius=0)
        main_container.pack(fill="both", expand=True)
        
        # 顶部工具栏 - Trae风格
        self.create_top_toolbar(main_container)
        
        # 主内容区域
        content_container = ctk.CTkFrame(main_container, corner_radius=0)
        content_container.pack(fill="both", expand=True)
        
        # 主工作区（包含三栏布局）
        self.create_main_workspace(content_container)
        
        # 底部状态栏
        self.create_status_bar(main_container)
    
    def create_top_toolbar(self, parent):
        """创建顶部工具栏"""
        self.toolbar = ctk.CTkFrame(parent, height=50, corner_radius=0)
        self.toolbar.pack(fill="x", padx=0, pady=0)
        self.toolbar.pack_propagate(False)
        
        # 左侧：应用标题和项目信息
        left_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        left_frame.pack(side="left", fill="y", padx=20, pady=10)
        
        # 应用图标和标题
        title_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        title_frame.pack(side="left", fill="y")
        
        # 标题采用项目图标
        app_title_img = None
        try:
            icon_png = self.get_assets_dir() / "icon.png"
            if icon_png.exists():
                img = Image.open(icon_png)
                self.app_logo_image = ctk.CTkImage(light_image=img, dark_image=img, size=(22, 22))
                app_title_img = self.app_logo_image
        except Exception as _e:
            print(f"加载标题图标失败: {_e}")
        
        if app_title_img is not None:
            app_title = ctk.CTkLabel(title_frame, text="CVEhunter", image=app_title_img, compound="left", 
                                   font=ctk.CTkFont(size=16, weight="bold"))
        else:
            app_title = ctk.CTkLabel(title_frame, text="CVEhunter", 
                                   font=ctk.CTkFont(size=16, weight="bold"))
        app_title.pack(side="left", pady=5)
        
        # 打开项目按钮
        open_project_btn = ctk.CTkButton(left_frame, text="📁 打开项目", 
                                       command=self.open_project_folder,
                                       width=90, height=28,
                                       font=ctk.CTkFont(size=11))
        open_project_btn.pack(side="left", padx=(20, 10), pady=5)
        
        # 项目路径显示
        self.project_path_label = ctk.CTkLabel(left_frame, text="未打开项目", 
                                             font=ctk.CTkFont(size=11),
                                             text_color=("gray50", "gray50"))
        self.project_path_label.pack(side="left", padx=(0, 0), pady=5)
        
        # 中间：模型选择
        center_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        center_frame.pack(side="left", fill="y", padx=20, pady=10, expand=True)
        
        # 模型选择标签和下拉框
        model_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        model_frame.pack(side="right")
        
        model_label = ctk.CTkLabel(model_frame, text="🤖 AI模型:", 
                                 font=ctk.CTkFont(size=11, weight="bold"))
        model_label.pack(side="left", padx=(0, 5))
        
        self.model_var = ctk.StringVar()
        self.model_combobox = ctk.CTkComboBox(model_frame, variable=self.model_var,
                                            command=self.on_model_change, width=150, height=28)
        self.model_combobox.pack(side="left", padx=5)
        
        # 右侧：快速操作按钮 - 更大更显眼
        right_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        right_frame.pack(side="right", fill="y", padx=15, pady=8)
        
        # 设置按钮
        settings_btn = ctk.CTkButton(right_frame, text="⚙️ 设置", width=70, height=34,
                                   command=self.open_settings,
                                   fg_color=("#10b981", "#059669"), 
                                   hover_color=("#059669", "#047857"),
                                   font=ctk.CTkFont(size=11, weight="bold"))
        settings_btn.pack(side="right", padx=3)
        
        # 模型管理按钮
        model_mgmt_btn = ctk.CTkButton(right_frame, text="🔧 模型", width=70, height=34,
                                     command=self.manage_models,
                                     fg_color=("#8b5cf6", "#7c3aed"), 
                                     hover_color=("#7c3aed", "#6d28d9"),
                                     font=ctk.CTkFont(size=11, weight="bold"))
        model_mgmt_btn.pack(side="right", padx=3)
        
        # 终端切换按钮
        self.terminal_toggle_btn = ctk.CTkButton(right_frame, text="📊 终端", width=70, height=34,
                                               command=self.toggle_terminal_panel,
                                               fg_color=("#3b82f6", "#2563eb"), 
                                               hover_color=("#2563eb", "#1d4ed8"),
                                               font=ctk.CTkFont(size=11, weight="bold"))
        self.terminal_toggle_btn.pack(side="right", padx=3)
        
        # 分隔线
        separator = ctk.CTkFrame(right_frame, width=2, height=30, fg_color=("gray70", "gray30"))
        separator.pack(side="right", padx=8)
        
        # 已移动到编辑器上方工具栏：自动换行开关（在 create_center_panel_content 中创建）
        # self.wrap_var = ctk.BooleanVar(value=False)
        # self.wrap_switch = ctk.CTkSwitch(right_frame, text="自动换行", variable=self.wrap_var, command=self.on_wrap_toggle)
        # self.wrap_switch.pack(side="right", padx=3)
        
        # 编辑器操作按钮已移动到代码编辑框上方的工具栏
        # 这里不再创建运行和保存按钮，避免重复

    
    def create_main_workspace(self, parent):
        """创建主工作区 - Trae风格三栏布局"""
        self.main_workspace = ctk.CTkFrame(parent, corner_radius=0)
        self.main_workspace.pack(side="right", fill="both", expand=True)
        
        # 创建三栏布局：左侧文件浏览器，中间代码编辑器，右侧AI对话
        self.create_three_column_layout()
    
    def create_three_column_layout(self):
        """创建左中右三栏布局 - 支持可调整分割"""
        # 主内容容器
        content_container = ctk.CTkFrame(self.main_workspace, corner_radius=0)
        content_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 创建主分割窗口（左侧面板 vs 右侧内容）
        self.main_paned = tk.PanedWindow(content_container, orient=tk.HORIZONTAL, 
                                        sashwidth=8, sashrelief=tk.RAISED,
                                        bg="#2b2b2b", sashpad=2)
        self.main_paned.pack(fill="both", expand=True)
        
        # 左栏：文件浏览器
        self.left_panel = ctk.CTkFrame(self.main_paned, corner_radius=6)
        
        # 创建右侧分割窗口（中间编辑器 vs 右侧AI助手）
        self.right_paned = tk.PanedWindow(self.main_paned, orient=tk.HORIZONTAL,
                                         sashwidth=8, sashrelief=tk.RAISED,
                                         bg="#2b2b2b", sashpad=2)
        
        # 中栏：代码编辑器
        self.center_panel = ctk.CTkFrame(self.right_paned, corner_radius=6)
        
        # 右栏：AI对话助手
        self.right_panel = ctk.CTkFrame(self.right_paned, corner_radius=6)
        # 第四栏：报告生成（默认不加入分割面板，待点击小三角后显示）
        self.report_panel = ctk.CTkFrame(self.right_paned, corner_radius=6)
        self.report_panel_in_paned = False
        # SQLmap验证面板（默认不加入分割面板）
        self.sqlmap_panel = ctk.CTkFrame(self.right_paned, corner_radius=6)
        self.sqlmap_panel_in_paned = False
        
        # 添加面板到分割窗口
        self.main_paned.add(self.left_panel, minsize=200, width=300)
        self.main_paned.add(self.right_paned, minsize=600)
        
        self.right_paned.add(self.center_panel, minsize=400)
        self.right_paned.add(self.right_panel, minsize=300, width=400)
        # 报告面板初始不加入 right_paned，保持隐藏
        
        # 设置初始分割比例
        self.root.after(100, self.set_initial_panel_ratios)
        
        # 绑定分割窗口事件
        self.bind_paned_events()
        
        # 创建各栏内容
        self.create_left_panel_content()
        self.create_center_panel_content()
        self.create_right_panel_content()
        # 初始化报告面板内容（先构建内容，稍后通过按钮切换显示）
        self.create_report_panel_content()
        # 初始化SQLmap面板内容
        self.create_sqlmap_panel_content()
    
    def set_initial_panel_ratios(self):
        """设置初始面板比例"""
        try:
            # 从设置中加载保存的比例，如果没有则使用默认值（更均匀的分布）
            ratios = self.settings_manager.get_setting('panel_ratios', {}) or {}
            left_ratio = ratios.get('left', 0.25)
            right_ratio = ratios.get('right', 0.25)
            center_vertical_ratio = ratios.get('center_vertical', 0.70)
            
            # 获取窗口总宽度
            total_width = self.root.winfo_width()
            if total_width <= 1:  # 窗口还未完全初始化
                total_width = 1600  # 使用默认宽度
            
            # 计算各面板宽度
            left_width = int(total_width * left_ratio)
            right_width = int(total_width * right_ratio)
            center_width = total_width - left_width - right_width
            
            # 设置主分割窗口的分割位置
            self.main_paned.sash_place(0, left_width, 0)
            
            # 设置右侧分割窗口的分割位置
            right_total = center_width + right_width
            right_split_pos = center_width
            self.right_paned.sash_place(0, right_split_pos, 0)

            # 设置中心垂直分割位置（编辑器/终端）仅在终端已加入时尝试
            try:
                if getattr(self, 'terminal_in_paned', False) and hasattr(self, 'center_paned') and self.center_paned:
                    ch = self.center_paned.winfo_height()
                    if ch <= 1:
                        # 延迟设置，确保高度与sash已可用
                        self.root.after(200, lambda: self.center_paned.sash_place(0, 0, int(self.center_paned.winfo_height() * center_vertical_ratio)))
                    else:
                        self.center_paned.sash_place(0, 0, int(ch * center_vertical_ratio))
            except Exception:
                pass
            
        except Exception as e:
            print(f"设置初始面板比例失败: {e}")
            # 使用默认比例（更均匀的分布：25% + 50% + 25%）
            self.root.after(100, lambda: self.main_paned.sash_place(0, 400, 0))  # 25% of 1600px
            self.root.after(100, lambda: self.right_paned.sash_place(0, 800, 0))  # 50% of 1600px
    
    def bind_paned_events(self):
        """绑定分割窗口事件"""
        # 绑定分割窗口拖拽结束事件
        self.main_paned.bind('<ButtonRelease-1>', self.on_paned_drag_end)
        self.right_paned.bind('<ButtonRelease-1>', self.on_paned_drag_end)
        # 中心垂直分割（编辑器/终端）拖拽事件：容错绑定（创建顺序可能晚于本方法）
        try:
            if hasattr(self, 'center_paned') and self.center_paned:
                self.center_paned.bind('<ButtonRelease-1>', self.on_paned_drag_end)
            else:
                self.root.after(200, lambda: getattr(self, 'center_paned', None) and self.center_paned.bind('<ButtonRelease-1>', self.on_paned_drag_end))
        except Exception:
            pass
        
        # 绑定窗口大小改变事件
        self.root.bind('<Configure>', self.on_window_configure)
    
    def on_paned_drag_end(self, event=None):
        """分割窗口拖拽结束时保存比例"""
        self.root.after(50, self.save_panel_ratios)  # 延迟保存，确保拖拽完成
    
    def on_window_configure(self, event=None):
        """窗口大小改变时的处理"""
        if event and event.widget == self.root:
            # 窗口大小改变时，延迟保存当前比例
            self.root.after(100, self.save_panel_ratios)
    
    def save_panel_ratios(self):
        """保存当前面板比例"""
        try:
            # 获取窗口总宽度
            total_width = self.root.winfo_width()
            if total_width <= 1:
                return
            
            # 主分割（左/中+右）
            main_sash_pos = self.main_paned.sash_coord(0)[0] if self.main_paned.winfo_exists() else 300
            left_ratio = main_sash_pos / total_width
            
            # 右侧分割（中/右）
            try:
                right_paned_width = self.right_paned.winfo_width()
                if right_paned_width > 1:
                    right_sash_pos = self.right_paned.sash_coord(0)[0]
                    right_panel_width = right_paned_width - right_sash_pos
                    right_ratio = right_panel_width / total_width
                else:
                    right_ratio = 0.25
            except Exception:
                right_ratio = 0.25
            
            # 报告与SQLmap面板宽度（如果显示）
            report_ratio = 0.0
            sqlmap_ratio = 0.0
            try:
                if getattr(self, "report_panel_in_paned", False) and self.report_panel.winfo_exists():
                    report_ratio = max(0.0, min(0.8, (self.report_panel.winfo_width() or 0) / max(1, total_width)))
            except Exception:
                pass
            try:
                if getattr(self, "sqlmap_panel_in_paned", False) and self.sqlmap_panel.winfo_exists():
                    sqlmap_ratio = max(0.0, min(0.8, (self.sqlmap_panel.winfo_width() or 0) / max(1, total_width)))
            except Exception:
                pass
            
            # 中心垂直分割（编辑器/终端高度）
            center_vertical_ratio = 0.70
            try:
                ch = self.center_paned.winfo_height()
                if ch > 1:
                    center_vertical_ratio = max(0.25, min(0.90, (self.center_paned.sash_coord(0)[1]) / ch))
            except Exception:
                pass
            
            panel_ratios = {
                'left': max(0.15, min(0.4, left_ratio)),
                'right': max(0.15, min(0.4, right_ratio)),
                'report': max(0.08, min(0.40, report_ratio)) if report_ratio > 0 else self.settings_manager.get_setting('panel_ratios', {}).get('report', 0.20),
                'sqlmap': max(0.08, min(0.40, sqlmap_ratio)) if sqlmap_ratio > 0 else self.settings_manager.get_setting('panel_ratios', {}).get('sqlmap', 0.20),
                'center_vertical': center_vertical_ratio
            }
            
            current = self.settings_manager.get_setting('panel_ratios', {})
            if current != panel_ratios:
                self.settings_manager.set_setting('panel_ratios', panel_ratios)
        except Exception as e:
            print(f"保存面板比例失败: {e}")
    
    def create_left_panel_content(self):
        """创建左栏内容 - 增强的文件浏览器"""
        # 标题
        title_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        title_label = ctk.CTkLabel(title_frame, text="📁 项目文件", 
                                 font=ctk.CTkFont(size=14, weight="bold"))
        title_label.pack(side="left")
        
        # 新建按钮：点击显示下拉菜单（新建文件/文件夹）
        def show_add_menu():
            if not hasattr(self, 'file_browser') or self.file_browser is None:
                show_warning("警告", "请先打开项目文件夹")
                return
            menu = tk.Menu(title_frame, tearoff=0)
            menu.add_command(label="新建文件", command=self.file_browser.new_file)
            menu.add_command(label="新建文件夹", command=self.file_browser.new_folder)
            x = new_file_btn.winfo_rootx()
            y = new_file_btn.winfo_rooty() + new_file_btn.winfo_height()
            menu.post(x, y)
        
        new_file_btn = ctk.CTkButton(title_frame, text="+", width=25, height=25,
                                   command=show_add_menu,
                                   font=ctk.CTkFont(size=12, weight="bold"))
        new_file_btn.pack(side="right")
        
        # 文件浏览器容器
        browser_container = ctk.CTkFrame(self.left_panel, corner_radius=4)
        browser_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # 重新初始化文件浏览器
        self.file_browser = FileBrowser(browser_container, on_file_select=self.on_file_selected)
    
    def create_center_panel_content(self):
        """创建中栏内容 - 代码编辑器和终端面板"""
        # 创建可调整大小的分割面板
        self.center_paned = tk.PanedWindow(self.center_panel, orient="vertical", sashwidth=8, sashrelief=tk.RAISED, bg="#2b2b2b", sashpad=2)
        self.center_paned.pack(fill="both", expand=True, padx=2, pady=2)
        
        # 代码编辑器容器 - 确保没有红色边框
        self.editor_container = ctk.CTkFrame(self.center_paned, 
                                           corner_radius=4,
                                           border_width=0,
                                           fg_color="transparent")
        # 将编辑器容器作为上半部分加入可拖动面板
        self.center_paned.add(self.editor_container)
        
        # 在代码编辑框上方创建工具栏（保存、运行、自动换行）
        self.editor_toolbar = ctk.CTkFrame(self.editor_container, fg_color="transparent")
        self.editor_toolbar.pack(fill="x", padx=8, pady=(6, 0))
        
        # 保存按钮
        save_btn = ctk.CTkButton(self.editor_toolbar, text="💾 保存", width=70, height=30,
                               command=self.save_file,
                               fg_color=("#3b82f6", "#2563eb"), 
                               hover_color=("#2563eb", "#1d4ed8"),
                               font=ctk.CTkFont(size=11, weight="bold"))
        save_btn.pack(side="right", padx=3)
        
        # 运行按钮
        run_btn = ctk.CTkButton(self.editor_toolbar, text="▶️ 运行", width=70, height=30,
                              command=self.run_code,
                              fg_color=("#10b981", "#059669"), 
                              hover_color=("#059669", "#047857"),
                              font=ctk.CTkFont(size=11, weight="bold"))
        run_btn.pack(side="right", padx=3)
        
        # 自动换行开关
        self.wrap_var = ctk.BooleanVar(value=False)
        self.wrap_switch = ctk.CTkSwitch(self.editor_toolbar, text="自动换行", variable=self.wrap_var, command=self.on_wrap_toggle)
        self.wrap_switch.pack(side="right", padx=3)
        
        # 初始化代码编辑器
        self.code_editor = CodeEditor(self.editor_container, on_content_change=self.on_code_changed)
        
        # 创建终端面板内容（下半部分，可自由上下拖动）
        self.create_terminal_content(self.center_paned)
        # 终端初始状态：未加入分割面板
        self.terminal_in_paned = False
    
    def _apply_markdown_formatting(self, text_widget):
        """应用Markdown格式化"""
        import re
        
        # 兼容 CTkTextbox：获取底层 tk.Text 以支持标签操作
        tw = getattr(text_widget, "textbox", None) or getattr(text_widget, "_textbox", None) or text_widget
        
        # 配置标签样式
        tw.tag_configure("heading1", font=("Consolas", 16, "bold"), foreground="#0078d4")
        tw.tag_configure("heading2", font=("Consolas", 14, "bold"), foreground="#0078d4")
        tw.tag_configure("heading3", font=("Consolas", 12, "bold"), foreground="#0078d4")
        tw.tag_configure("code_block", font=("Consolas", 9), background="#2d2d2d", foreground="#f8f8f2")
        tw.tag_configure("inline_code", font=("Consolas", 9), background="#404040", foreground="#f8f8f2")
        tw.tag_configure("bold", font=("Consolas", 10, "bold"))
        tw.tag_configure("italic", font=("Consolas", 10, "italic"))
        tw.tag_configure("link", font=("Consolas", 10, "underline"), foreground="#0078d4")
        tw.tag_configure("list_item", font=("Consolas", 10), lmargin1=20, lmargin2=30)
        tw.tag_configure("sub_list_item", font=("Consolas", 10), lmargin1=40, lmargin2=50)
        tw.tag_configure("table", font=("Consolas", 10))
        tw.tag_configure("table_header", font=("Consolas", 10, "bold"), background="#404040")
        tw.tag_configure("quote", font=("Consolas", 10, "italic"), background="#404040", lmargin1=20, lmargin2=20)
        tw.tag_configure("strikethrough", font=("Consolas", 10), overstrike=True)
        
        # 先清理旧的格式标签，避免重复叠加
        try:
            for tag in (
                "heading1","heading2","heading3","code_block","inline_code","bold","italic",
                "link","list_item","sub_list_item","table","table_header","quote","strikethrough"
            ):
                tw.tag_remove(tag, "1.0", "end")
        except Exception:
            pass
        
        # 获取所有文本内容
        content = tw.get("1.0", "end-1c")
        
        # 应用格式化
        lines = content.split('\n')
        in_code_block = False
        code_block_start = None
        in_table = False
        table_header_row = None
        in_quote = False
        quote_start = None
        
        for line_num, line in enumerate(lines, 1):
            line_start = f"{line_num}.0"
            line_end = f"{line_num}.{len(line)}"
            
            # 代码块格式化
            if line.strip().startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    code_block_start = line_start
                else:
                    in_code_block = False
                    tw.tag_add("code_block", code_block_start, line_end)
                continue
            
            if in_code_block:
                continue
                
            # 引用块格式化
            if line.strip().startswith('>'):
                if not in_quote:
                    in_quote = True
                    quote_start = line_start
                tw.tag_add("quote", line_start, line_end)
                if line_num < len(lines) and not lines[line_num].strip().startswith('>'):
                    in_quote = False
                continue
            elif in_quote:
                in_quote = False
            
            # 表格格式化
            if re.match(r'^\|(.+\|)+$', line.strip()):
                if not in_table:
                    in_table = True
                    table_header_row = line_num
                tw.tag_add("table", line_start, line_end)
                if table_header_row == line_num:
                    tw.tag_add("table_header", line_start, line_end)
                continue
            elif re.match(r'^\|(\s*[-:]+\s*\|)+$', line.strip()):
                # 表格分隔行
                tw.tag_add("table", line_start, line_end)
                continue
            elif in_table and not line.strip().startswith('|'):
                in_table = False
                table_header_row = None
            
            # 标题格式化
            heading_match = re.match(r'^(#{1,6})\s+', line)
            if heading_match:
                heading_level = len(heading_match.group(1))
                if heading_level == 1:
                    tw.tag_add("heading1", line_start, line_end)
                elif heading_level == 2:
                    tw.tag_add("heading2", line_start, line_end)
                else:
                    tw.tag_add("heading3", line_start, line_end)
                continue
            
            # 列表项格式化
            if re.match(r'^\s*[-*+]\s+', line):
                indent = len(re.match(r'^\s*', line).group(0))
                if indent >= 2:
                    tw.tag_add("sub_list_item", line_start, line_end)
                else:
                    tw.tag_add("list_item", line_start, line_end)
                continue
            
            # 内联格式化
            # 粗体
            for match in re.finditer(r'\*\*(.+?)\*\*', line):
                start, end = match.span()
                tw.tag_add("bold", f"{line_num}.{start}", f"{line_num}.{end}")
            
            # 斜体
            for match in re.finditer(r'\*(.+?)\*', line):
                start, end = match.span()
                if not any(start >= m.start() and end <= m.end() for m in re.finditer(r'\*\*(.+?)\*\*', line)):
                    tw.tag_add("italic", f"{line_num}.{start}", f"{line_num}.{end}")
            
            # 内联代码
            for match in re.finditer(r'`(.+?)`', line):
                start, end = match.span()
                tw.tag_add("inline_code", f"{line_num}.{start}", f"{line_num}.{end}")
            
            # 链接
            for match in re.finditer(r'\[(.+?)\]\((.+?)\)', line):
                start, end = match.span()
                tw.tag_add("link", f"{line_num}.{start}", f"{line_num}.{end}")
                
            # 删除线
            for match in re.finditer(r'~~(.+?)~~', line):
                start, end = match.span()
                tw.tag_add("strikethrough", f"{line_num}.{start}", f"{line_num}.{end}")
    

    
    def add_message_to_display(self, text_widget, message, is_user=False):
        """添加消息到显示区域，支持Markdown渲染"""
        # 设置只读状态为False以允许编辑
        text_widget.config(state="normal")
        
        # 在文本末尾添加消息
        if text_widget.get("1.0", "end-1c"):
            text_widget.insert("end", "\n\n")
        
        # 添加消息前缀
        prefix = "🧑‍💻 用户: " if is_user else "🤖 AI: "
        text_widget.insert("end", prefix + "\n", "bold")
        
        # 添加消息内容
        text_widget.insert("end", message)
        
        # 应用Markdown格式化
        self._apply_markdown_formatting(text_widget)
        
        # 滚动到底部
        text_widget.see("end")
        
        # 恢复只读状态
        text_widget.config(state="disabled")
    
    def display_user_message(self, message):
        """显示用户消息"""
        self.add_message_to_display(self.chat_display, message, is_user=True)
    
    def process_ai_response(self, response):
        """处理AI响应"""
        self.add_message_to_display(self.chat_display, response, is_user=False)
    
    def create_right_panel_content(self):
        """创建右栏内容 - AI对话助手"""
        # AI助手标题
        ai_header = ctk.CTkFrame(self.right_panel, fg_color="transparent", height=35)
        ai_header.pack(fill="x", padx=8, pady=(8, 3))
        ai_header.pack_propagate(False)
        
        ai_title = ctk.CTkLabel(ai_header, text="🤖 AI代码助手", 
                              font=ctk.CTkFont(size=12, weight="bold"))
        ai_title.pack(side="left", pady=6)
        
        # 右侧：报告面板小三角切换按钮（默认▶，展开后◀）
        self.report_toggle_btn = ctk.CTkButton(
            ai_header, text="报告生成模块 ▶", width=26, height=26,
            command=self.toggle_report_panel,
            fg_color=("gray30", "gray25"), hover_color=("gray40", "gray35"),
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.report_toggle_btn.pack(side="right", padx=4, pady=6)
        
        # SQLmap面板切换按钮
        self.sqlmap_toggle_btn = ctk.CTkButton(
            ai_header, text="SQLmap验证 ▶", width=26, height=26,
            command=self.toggle_sqlmap_panel,
            fg_color=("gray30", "gray25"), hover_color=("gray40", "gray35"),
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.sqlmap_toggle_btn.pack(side="right", padx=4, pady=6)
        
        # AI助手容器
        ai_container = ctk.CTkFrame(self.right_panel, corner_radius=4)
        ai_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # 初始化AI助手
        self.ai_assistant = AICodeAssistant(ai_container, 
                                          model_manager=self.model_manager,
                                          chat_manager=self.chat_manager,
                                          settings_manager=self.settings_manager,
                                          breakpoint_manager=self.breakpoint_manager)
        self.ai_assistant.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 使用AICodeAssistant内置的高级文件选择对话框（树形结构、搜索、标签）
        try:
            # 不再引入旧的简化对话框，避免覆盖内置高级组件
            print("使用内置高级文件选择对话框")
        except Exception as e:
            print(f"初始化文件交互对话框时出现问题: {e}")
        
        # 设置文件浏览器的AI助手引用
        self.file_browser.set_ai_assistant(self.ai_assistant)
        
        # 将Toast锚定到左侧项目结构面板容器的左下角
        try:
            self.ai_assistant.set_toast_anchor(browser_container)
        except Exception:
            pass
        
        # 设置AI助手的回调函数
        self.ai_assistant.set_callbacks(
            on_file_open=self.open_file_from_ai,
            on_file_edit=self.edit_file_from_ai
        )

    def create_report_panel_content(self):
        """创建右侧报告生成面板内容（默认隐藏，点击小三角显示）"""
        # 标题栏
        header = ctk.CTkFrame(self.report_panel, fg_color="transparent", height=35)
        header.pack(fill="x", padx=8, pady=(8, 3))
        header.pack_propagate(False)
        title = ctk.CTkLabel(header, text="📄 报告生成", font=ctk.CTkFont(size=12, weight="bold"))
        title.pack(side="left", pady=6)
        
        # 内容容器
        container = ctk.CTkFrame(self.report_panel, corner_radius=4)
        container.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # 控制栏：生成与导出 + 弹出模板选择
        controls = ctk.CTkFrame(container, fg_color="transparent")
        controls.pack(fill="x", padx=6, pady=(8, 4))
        
        # 隐藏语言状态变量（默认中文），由弹窗内切换
        self.report_lang_var = tk.StringVar(value="zh")
        # 初始化选中模板状态
        if not hasattr(self, "selected_template_path"):
            self.selected_template_path = None
        
        # 左侧：选择模板（弹窗）
        self.select_tpl_btn = ctk.CTkButton(controls, text="选择模板", width=90, height=30, command=self.open_template_selector_dialog,
                                           fg_color=("gray30", "gray25"), hover_color=("gray40", "gray35"))
        self.select_tpl_btn.pack(side="left", padx=3)
        reset_tpl_btn = ctk.CTkButton(controls, text="重置模板", width=80, height=30, command=self.reset_current_template_to_editor,
                                     fg_color=("gray28","gray24"), hover_color=("gray36","gray32"))
        reset_tpl_btn.pack(side="left", padx=3)
        
        # 右侧：生成与导出按钮
        gen_btn = ctk.CTkButton(controls, text="⚙️ 生成", width=70, height=30, command=self.generate_audit_report,
                               fg_color=("#10b981", "#059669"), hover_color=("#059669", "#047857"),
                               font=ctk.CTkFont(size=11, weight="bold"))
        gen_btn.pack(side="right", padx=3)
        export_md_btn = ctk.CTkButton(controls, text="📝 导出MD", width=80, height=30, command=lambda: self.export_report("md"),
                                     fg_color=("#3b82f6", "#2563eb"), hover_color=("#2563eb", "#1d4ed8"),
                                     font=ctk.CTkFont(size=11, weight="bold"))
        export_md_btn.pack(side="right", padx=3)
        
        # 表单填写区域（Basic.txt定义）
        form_label = ctk.CTkLabel(container, text="填写信息（Basic.txt）", font=ctk.CTkFont(size=11, weight="bold"))
        form_label.pack(fill="x", padx=6, pady=(6, 0))
        self.basic_form_frame = ctk.CTkScrollableFrame(container, height=180)
        self.basic_form_frame.pack(fill="x", padx=6, pady=(2, 6))
        try:
            self.build_basic_fields_form(self.basic_form_frame)
        except Exception:
            ctk.CTkLabel(self.basic_form_frame, text="Basic.txt 解析失败或不存在").pack(padx=6, pady=8)
        
        # 报告编辑/预览区域
        self.report_textbox = ctk.CTkTextbox(container)
        self.report_textbox.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        initial_text = "# 这里将展示所选模板或生成的报告内容\n\n在上方填写信息，填写后下方实时回显（占位符：全角（数字））。"
        self.report_base_text = initial_text
        self.report_textbox.insert("end", initial_text)
        # 实时Markdown渲染：键盘释放事件绑定（轻微节流）
        def _schedule_md_format(event=None):
            try:
                if hasattr(self, "_md_format_after_id") and self._md_format_after_id:
                    self.root.after_cancel(self._md_format_after_id)
            except Exception:
                pass
            try:
                self._md_format_after_id = self.root.after(120, lambda: self._apply_markdown_formatting(self.report_textbox))
            except Exception:
                pass
        try:
            self.report_textbox.bind("<KeyRelease>", _schedule_md_format)
        except Exception:
            pass
        
    def create_sqlmap_panel_content(self):
        """创建右侧SQLmap验证面板内容（默认隐藏，点击小三角显示）"""
        try:
            header = ctk.CTkFrame(self.sqlmap_panel, fg_color="transparent", height=35)
            header.pack(fill="x", padx=8, pady=(8, 3))
            header.pack_propagate(False)
            title = ctk.CTkLabel(header, text="🧪 SQLmap验证", font=ctk.CTkFont(size=12, weight="bold"))
            title.pack(side="left", pady=6)
            
            container = ctk.CTkFrame(self.sqlmap_panel, corner_radius=4)
            container.pack(fill="both", expand=True, padx=8, pady=(0, 8))
            
            # 路径显示与设置入口
            path_row = ctk.CTkFrame(container, fg_color="transparent")
            path_row.pack(fill="x", padx=6, pady=(8, 4))
            sqlmap_path = self.settings_manager.get_setting("tools.sqlmap_path", "") or "未配置"
            self.sqlmap_path_label = ctk.CTkLabel(path_row, text=f"路径: {sqlmap_path}", anchor="w")
            self.sqlmap_path_label.pack(side="left", fill="x", expand=True)
            open_settings_btn = ctk.CTkButton(path_row, text="打开设置", width=90, height=28, command=self.open_settings)
            open_settings_btn.pack(side="right", padx=3)
            
            # 参数输入（提醒粘贴大模型给出的参数，而不是单独URL）
            params_row = ctk.CTkFrame(container, fg_color="透明" if hasattr(ctk, 'TRANSPARENT') else "transparent")
            params_row.pack(fill="x", padx=6, pady=(4, 0))
            ctk.CTkLabel(params_row, text="参数:").pack(side="left", padx=(0, 6))
            # 使用多行输入框，自动换行，便于阅读长参数
            self.sqlmap_params_box = ctk.CTkTextbox(params_row, height=72)
            self.sqlmap_params_box.pack(side="left", fill="x", expand=True)
            # 旁边添加“清空”按钮，便于快速清空参数
            clear_params_btn = ctk.CTkButton(
                params_row,
                text="清空",
                width=72,
                height=28,
                command=lambda: self.sqlmap_params_box.delete("1.0", "end")
            )
            clear_params_btn.pack(side="right", padx=(6, 0))
            try:
                # 设置自动按词换行
                (getattr(self.sqlmap_params_box, "textbox", None) or getattr(self.sqlmap_params_box, "_textbox", None)).configure(wrap="word")
            except Exception:
                pass
            # 提示放到下一行并显式换行，避免被截断
            hint_label = ctk.CTkLabel(container, text="粘贴大模型提供的命令参数，\n例如 -u <url> -p id ...", anchor="w", justify="left")
            hint_label.pack(fill="x", padx=12, pady=(2, 6))
            
            # 操作按钮
            controls = ctk.CTkFrame(container, fg_color="透明" if hasattr(ctk, 'TRANSPARENT') else "transparent")
            controls.pack(fill="x", padx=6, pady=(6, 6))
            run_btn = ctk.CTkButton(controls, text="开始验证", width=90, height=30, command=self.run_sqlmap_scan,
                                    fg_color=("#10b981", "#059669"), hover_color=("#059669", "#047857"))
            run_btn.pack(side="left", padx=3)
            stop_btn = ctk.CTkButton(controls, text="停止", width=90, height=30, command=self.stop_sqlmap_execution,
                                     fg_color=("#ef4444", "#dc2626"), hover_color=("#dc2626", "#b91c1c"))
            stop_btn.pack(side="left", padx=3)
            clear_btn = ctk.CTkButton(controls, text="清空输出", width=90, height=30, command=self.clear_sqlmap_output)
            clear_btn.pack(side="left", padx=3)
            # 自动滚动开关（默认关闭，避免阅读时跳到底部）
            self.sqlmap_autoscroll_var = tk.BooleanVar(value=False)
            auto_cb = ctk.CTkCheckBox(controls, text="自动滚动", variable=self.sqlmap_autoscroll_var,
                                      command=lambda: self.sqlmap_output_manager.set_auto_scroll(self.sqlmap_autoscroll_var.get()))
            auto_cb.pack(side="right", padx=3)
            
            # SQLmap专用终端（精简UI，支持右键复制/全选，并保留ANSI颜色）
            self.sqlmap_output_manager = CodeOutputManager(container, minimal_ui=True)
            # 默认关闭自动滚动，按需打开
            try:
                self.sqlmap_output_manager.set_auto_scroll(False)
            except Exception:
                pass
            self.sqlmap_output_manager.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        except Exception as e:
            print(f"创建SQLmap面板失败: {e}")

    def toggle_report_panel(self):
        """切换右侧报告面板显示/隐藏（默认隐藏；点击小三角展开/收起）"""
        try:
            if getattr(self, "report_panel_in_paned", False):
                # 当前在分割面板中 -> 移除
                removed = False
                try:
                    self.right_paned.remove(self.report_panel)
                    removed = True
                except Exception:
                    try:
                        self.right_paned.forget(self.report_panel)
                        removed = True
                    except Exception:
                        removed = False
                if removed:
                    self.report_panel_in_paned = False
                    if hasattr(self, "report_toggle_btn"):
                        try:
                            self.report_toggle_btn.configure(text="报告生成模块 ▶")
                        except Exception:
                            pass
            else:
                # 尚未加入 -> 加入并显示
                self.right_paned.add(self.report_panel)
                try:
                    self.right_paned.paneconfig(self.report_panel, minsize=240)
                except Exception:
                    pass
                self.report_panel_in_paned = True
                if hasattr(self, "report_toggle_btn"):
                    try:
                        self.report_toggle_btn.configure(text="报告生成模块 ◀")
                    except Exception:
                        pass
        except Exception:
            # 回退：使用 pack 控制显示（非常规，但作为兼容处理）
            if hasattr(self, "report_panel"):
                if self.report_panel.winfo_ismapped():
                    try:
                        self.report_panel.pack_forget()
                        self.report_panel_in_paned = False
                        if hasattr(self, "report_toggle_btn"):
                            self.report_toggle_btn.configure(text="报告生成模块 ▶")
                    except Exception:
                        pass
                else:
                    self.report_panel.pack(fill="both", expand=True)
                    self.report_panel_in_paned = True
                    if hasattr(self, "report_toggle_btn"):
                        self.report_toggle_btn.configure(text="报告生成模块 ◀")

    def toggle_sqlmap_panel(self):
        """切换右侧SQLmap验证面板显示/隐藏"""
        try:
            if getattr(self, "sqlmap_panel_in_paned", False):
                removed = False
                try:
                    self.right_paned.remove(self.sqlmap_panel)
                    removed = True
                except Exception:
                    try:
                        self.right_paned.forget(self.sqlmap_panel)
                        removed = True
                    except Exception:
                        removed = False
                if removed:
                    self.sqlmap_panel_in_paned = False
                    if hasattr(self, "sqlmap_toggle_btn"):
                        try:
                            self.sqlmap_toggle_btn.configure(text="SQLmap验证 ▶")
                        except Exception:
                            pass
            else:
                self.right_paned.add(self.sqlmap_panel)
                try:
                    self.right_paned.paneconfig(self.sqlmap_panel, minsize=240)
                except Exception:
                    pass
                self.sqlmap_panel_in_paned = True
                if hasattr(self, "sqlmap_toggle_btn"):
                    try:
                        self.sqlmap_toggle_btn.configure(text="SQLmap验证 ◀")
                    except Exception:
                        pass
        except Exception:
            if hasattr(self, "sqlmap_panel"):
                if self.sqlmap_panel.winfo_ismapped():
                    try:
                        self.sqlmap_panel.pack_forget()
                        self.sqlmap_panel_in_paned = False
                        if hasattr(self, "sqlmap_toggle_btn"):
                            self.sqlmap_toggle_btn.configure(text="SQLmap验证 ▶")
                    except Exception:
                        pass
                else:
                    self.sqlmap_panel.pack(fill="both", expand=True)
                    self.sqlmap_panel_in_paned = True
                    if hasattr(self, "sqlmap_toggle_btn"):
                        self.sqlmap_toggle_btn.configure(text="SQLmap验证 ◀")
    
    def run_sqlmap_scan(self):
        """读取设置中的SQLmap路径并执行验证，输出到SQLmap专用终端"""
        try:
            sqlmap_path = self.settings_manager.get_setting("tools.sqlmap_path", "").strip()
            params_str = ""
            try:
                params_text = (self.sqlmap_params_box.get("1.0", "end") or "")
                # 压缩空白，允许用户分行输入
                params_str = " ".join(params_text.split()).strip()
            except Exception:
                params_str = ""
            
            if not sqlmap_path:
                show_error("错误", "未配置SQLmap路径，请在设置中配置。")
                try:
                    self.open_settings()
                except Exception:
                    pass
                return
            if not os.path.exists(sqlmap_path):
                show_error("错误", f"SQLmap路径不存在:\n{sqlmap_path}")
                return
            if not params_str:
                show_warning("警告", "请粘贴大模型给出的参数（包含 -u 等）。")
                return
            
            # 在SQLmap面板输出开始信息
            try:
                ts = datetime.now().strftime("%H:%M:%S")
                self.sqlmap_output_manager.append_output("stdout", f"[{ts}] [SQLmap] 启动验证: {params_str}\n")
            except Exception:
                pass
            
            # 构造命令（不强加 --color / --batch，完全按用户参数执行）
            ext = os.path.splitext(sqlmap_path)[1].lower()
            if ext in (".py", ".pyw"):
                cmd = f'python "{sqlmap_path}" {params_str}'
            else:
                cmd = f'"{sqlmap_path}" {params_str}'
            
            # 执行并实时输出到SQLmap终端
            self.sqlmap_output_manager.execute_code(cmd)
        except Exception as e:
            try:
                ts = datetime.now().strftime("%H:%M:%S")
                self.sqlmap_output_manager.append_output("stderr", f"[{ts}] [SQLmap] 执行失败: {e}\n")
            except Exception:
                self.add_terminal_output("SQLmap", f"执行失败: {e}")
        
    def generate_audit_report(self):
        """生成审计报告（基于模板）"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            project = self.project_path_label.cget("text") if hasattr(self, "project_path_label") else "未打开项目"
            model = self.model_combobox.get() if hasattr(self, "model_combobox") else "未知模型"
            # 占位数据
            summary = "此处将展示审计助手生成的概述与总结。"
            risks_list = [
                "（示例）存在潜在的输入未校验问题",
                "（示例）使用过期依赖版本"
            ]
            risks = "\n".join([f"- {r}" for r in risks_list])
            details = "后续将接入具体检测与证据。"
            context = {
                "timestamp": timestamp,
                "project": project,
                "model": model,
                "summary": summary,
                "risks": risks,
                "details": details
            }
            # 选择模板
            tpl_path = getattr(self, "selected_template_path", None)
            if not tpl_path:
                lang = self.report_lang_var.get() if hasattr(self, "report_lang_var") else "zh"
                tpl_list = self.load_templates_for_lang(lang)
                tpl_path = tpl_list[0]["path"] if tpl_list else None
            if tpl_path and Path(tpl_path).exists():
                # 若下方编辑区当前展示模板，则优先使用用户编辑后的模板文本
                try:
                    edited_text = self.report_textbox.get("1.0", "end").strip()
                    tpl_text = edited_text if edited_text else Path(tpl_path).read_text(encoding="utf-8")
                except Exception:
                    tpl_text = Path(tpl_path).read_text(encoding="utf-8")
                # 先替换 Basic.txt 定义的编号占位符，再进行 ${} 渲染
                basic_values = self.get_basic_values()
                preprocessed = self.apply_basic_mappings_to_text(tpl_text, basic_values)
                content = self.render_template_with_context(preprocessed, context)
            else:
                content = (
                    f"# CVEhunter 审计报告\n\n"
                    f"生成时间: {timestamp}\n"
                    f"项目: {project}\n"
                    f"模型: {model}\n\n"
                    "## 概述\n" + summary + "\n\n" +
                    "## 风险摘要\n" + risks + "\n\n" +
                    "## 详细结果\n" + details + "\n"
                )
            self.report_textbox.delete("1.0", "end")
            self.report_textbox.insert("end", content)
            try:
                self._apply_markdown_formatting(self.report_textbox)
            except Exception:
                pass
            self.add_terminal_output("报告", "已根据模板生成审计报告")
        except Exception as e:
            try:
                show_error("错误", f"生成报告失败: {e}")
            except Exception:
                pass
        
    def export_report(self, fmt: str):
        """导出报告为 Markdown 或 HTML（占位实现）"""
        try:
            content = self.report_textbox.get("1.0", "end")
            if fmt == "md":
                default_ext = ".md"
                filetypes = [("Markdown", "*.md"), ("所有文件", "*.*")]
            else:
                default_ext = ".html"
                filetypes = [("HTML", "*.html"), ("所有文件", "*.*")]
            save_path = filedialog.asksaveasfilename(defaultextension=default_ext, filetypes=filetypes, title="导出报告")
            if not save_path:
                return
            if fmt == "md":
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                html = (
                    "<!doctype html><html><head><meta charset='utf-8'><title>审计报告</title>"
                    "<style>body{font-family:Consolas,monospace;background:#111;color:#eee;padding:20px;}"
                    "pre{white-space:pre-wrap;}</style></head><body><pre>" + content + "</pre></body></html>"
                )
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(html)
            show_success("成功", f"报告已导出: {save_path}")
            self.add_terminal_output("报告", f"已导出为 {fmt.upper()} -> {save_path}")
        except Exception as e:
            try:
                show_error("错误", f"导出失败: {e}")
            except Exception:
                pass

    def get_templates_dir(self):
        return Path(__file__).parent / "templates"

    def ensure_template_dirs_and_examples(self):
        try:
            base = self.get_templates_dir()
            (base / "zh").mkdir(parents=True, exist_ok=True)
            (base / "en").mkdir(parents=True, exist_ok=True)
            # 如果已检测到任何模板文件，直接跳过示例生成
            try:
                zh_has = any((base / "zh").glob("*.md"))
                en_has = any((base / "en").glob("*.md"))
            except Exception:
                zh_has = False
                en_has = False
            if zh_has or en_has:
                return
            # 未检测到模板时，才创建示例模板
            samples = [
                (base/"zh"/"默认模板.md", "# CVEhunter 审计报告\n\n生成时间: ${timestamp}\n项目: ${project}\n模型: ${model}\n\n## 概述\n${summary}\n\n## 风险摘要\n${risks}\n\n## 详细结果\n${details}\n"),
                (base/"zh"/"简版摘要.md", "# 审计摘要\n\n生成时间: ${timestamp}\n项目: ${project}\n\n## 关键风险\n${risks}\n\n## 建议\n- 加强输入校验\n- 升级过期依赖\n"),
                (base/"en"/"Default.md", "# CVEhunter Audit Report\n\nGenerated at: ${timestamp}\nProject: ${project}\nModel: ${model}\n\n## Overview\n${summary}\n\n## Risk Summary\n${risks}\n\n## Details\n${details}\n"),
                (base/"en"/"Summary.md", "# Audit Summary\n\nGenerated at: ${timestamp}\nProject: ${project}\n\n## Key Risks\n${risks}\n\n## Recommendations\n- Improve input validation\n- Upgrade outdated dependencies\n"),
            ]
            for path, content in samples:
                if not path.exists():
                    path.write_text(content, encoding="utf-8")
        except Exception as e:
            print(f"初始化模板目录失败: {e}")

    def load_templates_for_lang(self, lang: str):
        base = self.get_templates_dir() / lang
        templates = []
        try:
            if base.exists():
                for p in sorted(base.glob("*.md")):
                    templates.append({"name": p.stem, "path": str(p)})
        except Exception as e:
            print(f"加载模板失败: {e}")
        return templates

    def refresh_template_buttons(self):
        # 清空旧按钮
        try:
            for child in self.templates_list_frame.winfo_children():
                child.destroy()
        except Exception:
            pass
        lang = getattr(self, "report_lang_var", None).get() if hasattr(self, "report_lang_var") else "zh"
        tpl_list = self.load_templates_for_lang(lang)
        self._template_buttons = {}
        for tpl in tpl_list:
            btn = ctk.CTkButton(self.templates_list_frame, text=tpl["name"], width=120, height=28,
                                command=lambda p=tpl["path"]: self.select_template(p),
                                fg_color=("gray30","gray25"), hover_color=("gray40","gray35"))
            btn.pack(side="left", padx=4, pady=6)
            self._template_buttons[tpl["path"]] = btn
        # 如果没有模板，显示提示
        if not tpl_list:
            ctk.CTkLabel(self.templates_list_frame, text="当前语言暂无模板").pack(padx=6, pady=8)

    def on_report_language_change(self, value: str):
        lang = "zh" if value == "中文" else "en"
        if hasattr(self, "report_lang_var"):
            self.report_lang_var.set(lang)
        self.refresh_template_buttons()

    def select_template(self, path: str):
        self.selected_template_path = path
        # 高亮选中按钮
        try:
            for p, b in getattr(self, "_template_buttons", {}).items():
                if p == path:
                    b.configure(fg_color=("#3b82f6","#2563eb"))
                else:
                    b.configure(fg_color=("gray30","gray25"))
        except Exception:
            pass
        # 预览模板结构（并建立实时映射基底）
        try:
            tpl_text = Path(path).read_text(encoding="utf-8")
            self.report_base_text = tpl_text
            self.refresh_report_preview()
            # 根据模板中出现的【数字】，重建 Basic 表单
            try:
                self.rebuild_basic_form_for_current_template()
            except Exception:
                pass
        except Exception:
            pass

    def open_template_selector_dialog(self):
        try:
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("选择模板")
            dialog.geometry("520x420")
            dialog.resizable(False, False)
            dialog.transient(self.root)
            dialog.grab_set()
            # 同步窗口图标
            try:
                assets = self.get_assets_dir()
                ico_path = assets / "icon.ico"
                png_path = assets / "icon.png"
                icon_applied = False
                if sys.platform.startswith("win") and ico_path.exists():
                    try:
                        dialog.iconbitmap(str(ico_path))
                        icon_applied = True
                        print("[hosts-dialog] icon set from ICO")
                    except Exception as _e:
                        print(f"[hosts-dialog] ICO set failed: {_e}")
                if not icon_applied and png_path.exists():
                    try:
                        _img = tk.PhotoImage(file=str(png_path))
                        dialog.iconphoto(False, _img)
                        setattr(dialog, "_icon_img_ref", _img)
                        icon_applied = True
                        print("[hosts-dialog] icon set from PNG")
                    except Exception as _e:
                        print(f"[hosts-dialog] PNG set failed: {_e}")
            except Exception:
                pass
            # 居中显示
            try:
                x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 260
                y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 210
                dialog.geometry(f"520x420+{x}+{y}")
            except Exception:
                pass

            main = ctk.CTkFrame(dialog)
            main.pack(fill="both", expand=True, padx=12, pady=12)

            title = ctk.CTkLabel(main, text="选择报告模板", font=ctk.CTkFont(size=14, weight="bold"))
            title.pack(pady=(4,8))

            # 顶部：语言切换
            topbar = ctk.CTkFrame(main, fg_color="transparent")
            topbar.pack(fill="x")
            lang_seg = ctk.CTkSegmentedButton(topbar, values=["中文", "English"]) 
            try:
                if getattr(self, "report_lang_var", None) and self.report_lang_var.get() == "en":
                    lang_seg.set("English")
                else:
                    lang_seg.set("中文")
            except Exception:
                pass
            lang_seg.pack(side="left", padx=4, pady=(2,6))

            # 模板列表
            list_frame = ctk.CTkScrollableFrame(main)
            list_frame.pack(fill="both", expand=True, pady=(6, 8))

            def populate():
                # 清空
                for child in list_frame.winfo_children():
                    try:
                        child.destroy()
                    except Exception:
                        pass
                current_value = lang_seg.get()
                lang = "zh" if current_value == "中文" else "en"
                if hasattr(self, "report_lang_var"):
                    self.report_lang_var.set(lang)
                tpl_list = self.load_templates_for_lang(lang)
                if not tpl_list:
                    ctk.CTkLabel(list_frame, text="当前语言暂无模板").pack(padx=6, pady=8)
                    return
                for tpl in tpl_list:
                    name = tpl["name"]
                    path = tpl["path"]
                    btn = ctk.CTkButton(list_frame, text=name, height=32,
                                        command=lambda p=path: choose_and_close(p),
                                        fg_color=("gray30","gray25"), hover_color=("gray40","gray35"))
                    btn.pack(fill="x", padx=6, pady=4)

            def choose_and_close(path):
                self.selected_template_path = path
                # 预览模板内容（不替换变量）
                try:
                    self.select_template(path)
                except Exception:
                    pass
                # 更新主面板按钮文本
                try:
                    if hasattr(self, "select_tpl_btn"):
                        self.select_tpl_btn.configure(text=f"模板：{Path(path).stem}")
                except Exception:
                    pass
                try:
                    dialog.destroy()
                except Exception:
                    pass
                try:
                    show_success("模板", f"已选择模板：{Path(path).stem}")
                except Exception:
                    pass

            def on_lang_change(value):
                populate()
            try:
                lang_seg.configure(command=on_lang_change)
            except Exception:
                pass

            populate()

            # 底部：关闭按钮
            bottom = ctk.CTkFrame(main, fg_color="transparent")
            bottom.pack(fill="x", pady=(6,0))
            close_btn = ctk.CTkButton(bottom, text="关闭", width=70, command=lambda: dialog.destroy())
            close_btn.pack(side="right", padx=4)
        except Exception as e:
            try:
                show_error("错误", f"打开模板选择失败: {e}")
            except Exception:
                pass

    def render_template_with_context(self, template_text: str, context: dict) -> str:
        try:
            t = Template(template_text)
            return t.safe_substitute(**context)
        except Exception as e:
            print(f"模板渲染失败: {e}")
            return template_text

    # ===== 基础字段（Basic.txt）解析与表单构建 =====
    def get_basic_definitions_path(self) -> Path:
        return Path(__file__).parent / "templates" / "Basic.txt"

    def parse_basic_definitions(self) -> dict:
        fields = {}
        path = self.get_basic_definitions_path()
        if not path.exists():
            return fields
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s:
                    continue
                # 格式：num-字段;默认值:选项1\选项2\选项3
                # 默认值或选项均可省略
                try:
                    num_part, rest = s.split('-', 1)
                    num = int(num_part.strip())
                    label = rest
                    default = ""
                    options = []
                    # 解析选项
                    if ':' in rest:
                        label_part, options_part = rest.split(':', 1)
                        label = label_part.strip()
                        options = [opt.strip() for opt in options_part.split('\\') if opt.strip()]
                    # 解析默认值（在label后通过 ; 指定）
                    if ';' in label:
                        label_text, default_part = label.split(';', 1)
                        label = label_text.strip()
                        default = default_part.strip()
                    fields[num] = {
                        'label': label,
                        'default': default,
                        'options': options
                    }
                except Exception:
                    # 容错：无法解析则跳过
                    continue
        except Exception:
            pass
        return fields

    def build_basic_fields_form(self, parent, include_numbers=None):
        self.basic_defs = self.parse_basic_definitions()
        self.basic_field_widgets = {}
        if not self.basic_defs:
            ctk.CTkLabel(parent, text="未发现 Basic.txt 或无内容").pack(pady=8)
            return
        # 依据模板中出现的【数字】过滤展示字段
        if include_numbers is not None:
            nums = [n for n in sorted(set(include_numbers)) if n in self.basic_defs]
            if not nums:
                ctk.CTkLabel(parent, text="当前模板未包含可用的【数字】占位符").pack(pady=8)
                return
        else:
            nums = sorted(self.basic_defs.keys())
        # 构建字段（竖排）
        for num in nums:
            meta = self.basic_defs[num]
            group = ctk.CTkFrame(parent)
            group.pack(fill="x", padx=6, pady=6)
            title = ctk.CTkLabel(group, text=f"【{num}】{meta['label']}", font=ctk.CTkFont(size=11, weight="bold"))
            title.pack(anchor='w')
            # 文本输入
            entry = ctk.CTkEntry(group, width=600)
            entry.pack(fill="x", pady=(4,2))
            if meta['default']:
                try:
                    entry.insert(0, meta['default'])
                except Exception:
                    pass
            # 输入变更 -> 预览刷新（轻节流）
            try:
                entry.bind("<KeyRelease>", lambda e: self._schedule_basic_preview())
            except Exception:
                pass
            widgets = {'entry': entry, 'options_vars': [], 'options_labels': meta['options']}
            # 选项（多选）
            if meta['options']:
                opts_frame = ctk.CTkFrame(group)
                opts_frame.pack(fill="x", pady=(2,4))
                for opt in meta['options']:
                    var = tk.BooleanVar(value=False)
                    cb = ctk.CTkCheckBox(opts_frame, text=opt, variable=var)
                    # 纵向从上到下排列，左对齐，避免一行显示不全
                    cb.pack(fill='x', anchor='w', padx=4, pady=2)
                    # 选项变更 -> 预览刷新
                    try:
                        cb.configure(command=self._schedule_basic_preview)
                    except Exception:
                        pass
                    widgets['options_vars'].append(var)
            self.basic_field_widgets[num] = widgets

    def extract_template_placeholder_numbers(self, text: str = None):
        """从当前模板文本中提取【数字】占位符编号列表（去重、排序）"""
        try:
            if text is None:
                text = getattr(self, 'report_base_text', '') or ''
            pattern = r'【\s*(\d{1,3})\s*】'
            nums = {int(m.group(1)) for m in re.finditer(pattern, text)}
            return sorted(nums)
        except Exception:
            return []

    def rebuild_basic_form_for_current_template(self):
        """根据当前模板中的【数字】占位符，重建 Basic 表单，只展示所需字段"""
        try:
            frame = getattr(self, 'basic_form_frame', None)
            if not frame:
                return
            # 清空旧表单
            for child in frame.winfo_children():
                try:
                    child.destroy()
                except Exception:
                    pass
            used_nums = self.extract_template_placeholder_numbers()
            self.build_basic_fields_form(frame, include_numbers=used_nums)
            # 构建后立刻刷新预览，确保界面一致
            try:
                self._schedule_basic_preview(0)
            except Exception:
                pass
        except Exception:
            pass

    def get_basic_values(self) -> dict:
        values = {}
        for num, w in getattr(self, 'basic_field_widgets', {}).items():
            text_val = ""
            try:
                text_val = w['entry'].get().strip()
            except Exception:
                pass
            selected_opts = []
            try:
                for var, opt in zip(w.get('options_vars', []), w.get('options_labels', [])):
                    if var.get():
                        selected_opts.append(opt)
            except Exception:
                pass
            render_val = text_val
            if selected_opts:
                # 选中项以“ / ”拼接，适配标题等位置
                opts_str = " / ".join(selected_opts)
                render_val = opts_str if not text_val else f"{text_val}\n{opts_str}"
            values[num] = {
                'text': text_val,
                'options': selected_opts,
                'render': render_val
            }
        return values

    def apply_basic_mappings_to_text(self, template_text: str, values_map: dict) -> str:
        # 占位符替换：支持【数字】（全角方括号），同时兼容（数字）与(数字)
        # 示例：【1】、【 14 】、（3）、(7)
        pattern = r'(?:[【\[]\s*(\d{1,3})\s*[】\]]|[（(]\s*(\d{1,3})\s*[)）])'
        def repl(m):
            try:
                num_str = m.group(1) or m.group(2)
                num = int(num_str)
                if num in values_map:
                    # 即使值为空也替换为空字符串，避免残留占位符
                    return values_map.get(num, {}).get('render', '')
                return m.group(0)
            except Exception:
                return m.group(0)
        return re.sub(pattern, repl, template_text)

    # 实时刷新下方报告预览（从基底模板+当前 Basic 值生成）
    def refresh_report_preview(self):
        try:
            base = getattr(self, 'report_base_text', '') or self.report_textbox.get("1.0", "end-1c")
            values_map = self.get_basic_values()
            rendered = self.apply_basic_mappings_to_text(base, values_map)
            self.report_textbox.delete("1.0", "end")
            self.report_textbox.insert("end", rendered)
            self._apply_markdown_formatting(self.report_textbox)
        except Exception:
            pass

    # 轻节流调度：避免频繁刷新
    def _schedule_basic_preview(self, delay_ms: int = 120):
        try:
            if hasattr(self, "_basic_preview_after_id") and self._basic_preview_after_id:
                self.root.after_cancel(self._basic_preview_after_id)
        except Exception:
            pass
        try:
            self._basic_preview_after_id = self.root.after(delay_ms, self.refresh_report_preview)
        except Exception:
            pass

    def reset_current_template_to_editor(self):
        """将当前选择的模板文本重新载入到编辑区，便于修改"""
        try:
            tpl_path = getattr(self, "selected_template_path", None)
            if tpl_path and Path(tpl_path).exists():
                tpl_text = Path(tpl_path).read_text(encoding="utf-8")
                self.report_base_text = tpl_text
                self.refresh_report_preview()
                # 重建 Basic 表单，仅展示模板中的【数字】字段
                try:
                    self.rebuild_basic_form_for_current_template()
                except Exception:
                    pass
                try:
                    show_success("模板", "已重置为当前选择的模板内容")
                except Exception:
                    pass
            else:
                show_warning("模板", "尚未选择模板或模板不存在")
        except Exception as e:
            try:
                show_error("错误", f"重置模板失败: {e}")
            except Exception:
                pass


    def create_terminal_content(self, parent):
        """创建底部终端/输出区域（支持上下拖动，精简UI）"""
        # 终端容器（透明背景）
        self.terminal_container = ctk.CTkFrame(parent, fg_color="transparent")
        
        # 精简的 CodeOutputManager（仅输出，无多余按钮/标签页，支持彩色ANSI）
        from utils.code_output_manager import CodeOutputManager
        self.code_output_manager = CodeOutputManager(self.terminal_container, minimal_ui=True)
        self.code_output_manager.pack(fill="both", expand=True)
        
        # 兼容旧引用名称
        self.output_manager = self.code_output_manager
        
        # 接管全局stdout/stderr到终端输出（保留原输出）
        try:
            class _StdRedirector:
                def __init__(self, app, source, orig_stream):
                    self.app = app
                    self.source = source
                    self.orig_stream = orig_stream
                def write(self, data):
                    if not data:
                        return
                    # 追加到终端（去掉多余换行避免双换行）
                    try:
                        msg = data if isinstance(data, str) else str(data)
                        if msg.strip():
                            self.app.add_terminal_output(self.source, msg.rstrip("\n"))
                    except Exception:
                        pass
                    # 同步到原始流
                    try:
                        self.orig_stream.write(data)
                    except Exception:
                        pass
                def flush(self):
                    try:
                        self.orig_stream.flush()
                    except Exception:
                        pass
            # 保存原始流并替换
            if not hasattr(self, "_orig_stdout"):
                self._orig_stdout = sys.stdout
            if not hasattr(self, "_orig_stderr"):
                self._orig_stderr = sys.stderr
            sys.stdout = _StdRedirector(self, "STDOUT", self._orig_stdout)
            sys.stderr = _StdRedirector(self, "STDERR", self._orig_stderr)
        except Exception as e:
            print(f"终端输出接管失败: {e}")
        
        # 默认不加入分割面板，保持隐藏，待运行或用户手动切换时再加入
        return self.terminal_container
    
    def bind_terminal_resize_events(self, resize_handle):
        """绑定终端面板调整大小事件"""
        def start_resize(event):
            self.resize_start_y = event.y_root
            self.resize_start_height = self.terminal_container.winfo_height()
        
        def do_resize(event):
            if hasattr(self, 'resize_start_y'):
                delta_y = event.y_root - self.resize_start_y
                new_height = max(100, min(400, self.resize_start_height - delta_y))
                self.terminal_container.configure(height=new_height)
        
        def end_resize(event):
            if hasattr(self, 'resize_start_y'):
                delattr(self, 'resize_start_y')
        
        resize_handle.bind("<Button-1>", start_resize)
        resize_handle.bind("<B1-Motion>", do_resize)
        resize_handle.bind("<ButtonRelease-1>", end_resize)
        
        # 改变鼠标样式
        resize_handle.bind("<Enter>", lambda e: resize_handle.configure(cursor="sb_v_double_arrow"))
        resize_handle.bind("<Leave>", lambda e: resize_handle.configure(cursor=""))
    
    def create_status_bar(self, parent):
        """创建底部状态栏 - Trae风格"""
        self.status_bar = ctk.CTkFrame(parent, height=30, corner_radius=0)
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)
        
        # 状态信息
        self.status_label = ctk.CTkLabel(self.status_bar, text="就绪", 
                                       font=ctk.CTkFont(size=11))
        self.status_label.pack(side="left", padx=15, pady=5)
        
        # 右侧信息
        status_right = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        status_right.pack(side="right", padx=15, pady=5)
        
        # 当前模型显示
        self.current_model_label = ctk.CTkLabel(status_right, text="未选择模型", 
                                              font=ctk.CTkFont(size=10),
                                              text_color=("gray50", "gray50"))
        self.current_model_label.pack(side="right")

    def load_models(self):
        """加载模型列表"""
        models = self.model_manager.get_enabled_models()
        model_names = [f"{model['name']}" for model in models]
        # 新增：建立名称到ID的映射
        self.model_name_to_id = {model['name']: model['id'] for model in models}
        
        self.model_combobox.configure(values=model_names)
        
        if models:
            first_name = model_names[0]
            self.model_combobox.set(first_name)
            self.current_model_id = self.model_name_to_id.get(first_name)
            # 同步当前模型ID到 ChatManager
            if hasattr(self, 'chat_manager') and hasattr(self.chat_manager, 'set_current_model_id'):
                self.chat_manager.set_current_model_id(self.current_model_id)
            self.current_model_label.configure(text=f"模型: {first_name}")
        else:
            self.model_combobox.set("无可用模型")
            self.current_model_id = None
            if hasattr(self, 'chat_manager') and hasattr(self.chat_manager, 'set_current_model_id'):
                self.chat_manager.set_current_model_id(None)
            self.current_model_label.configure(text="无可用模型")
    
    def bind_events(self):
        """绑定事件"""
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        
        # 快捷键绑定
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-o>", lambda e: self.open_project_folder())
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<F5>", lambda e: self.run_code())
    
    # 事件处理方法
    def open_project_folder(self):
        """打开项目文件夹"""
        folder_path = filedialog.askdirectory(title="选择项目文件夹")
        if folder_path:
            self.current_project_path = folder_path
            project_name = os.path.basename(folder_path)
            self.project_path_label.configure(text=f"项目: {project_name}")
            self.file_browser.load_project(folder_path)
            
            # 通知AI助手项目路径变化
            if hasattr(self, 'ai_assistant'):
                self.ai_assistant.set_project_path(folder_path)
            
            self.update_status(f"已打开项目: {folder_path}")
            self.add_terminal_output("项目", f"已打开项目: {project_name}")
    
    def on_file_selected(self, file_path):
        """文件选择事件处理"""
        if file_path and os.path.isfile(file_path):
            self.current_file_path = file_path
            file_name = os.path.basename(file_path)
            
            # 读取文件内容到代码编辑器
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.code_editor.set_content(content)
                
                # 通知AI助手当前文件变化
                if hasattr(self, 'ai_assistant'):
                    self.ai_assistant.set_current_file(file_path)
                
                self.update_status(f"已打开文件: {file_name}")
                self.add_terminal_output("文件", f"已打开: {file_name}")
            except Exception as e:
                show_error("错误", f"无法打开文件: {e}")
                self.add_terminal_output("错误", f"无法打开文件: {e}")
    
    def on_model_change(self, model_name):
        """模型选择变化事件"""
        # 使用名称→ID映射查找并设置当前模型
        new_model_id = self.model_name_to_id.get(model_name)
        if new_model_id:
            self.current_model_id = new_model_id
            # 同步到 ChatManager
            if hasattr(self, 'chat_manager') and hasattr(self.chat_manager, 'set_current_model_id'):
                self.chat_manager.set_current_model_id(self.current_model_id)
            self.current_model_label.configure(text=f"模型: {model_name}")
            self.update_status(f"已选择模型: {model_name}")
            self.add_terminal_output("模型", f"已选择: {model_name}")
        else:
            # 未找到匹配的模型，提示用户
            show_warning("警告", f"未找到模型: {model_name}")
            self.add_terminal_output("模型", f"选择失败: {model_name}")
    
    def on_code_changed(self):
        """代码内容变化事件"""
        # 可以在这里添加自动保存等功能
        pass
    
    def new_file(self):
        """新建文件"""
        if not self.current_project_path:
            show_warning("警告", "请先打开项目文件夹")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="新建文件",
            initialdir=self.current_project_path,
            filetypes=[("Python文件", "*.py"), ("JavaScript文件", "*.js"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("")
                self.on_file_selected(file_path)
                self.file_browser.refresh_tree()
                self.add_terminal_output("文件", f"已创建: {os.path.basename(file_path)}")
            except Exception as e:
                show_error("错误", f"无法创建文件: {e}")
                self.add_terminal_output("错误", f"无法创建文件: {e}")
    
    def save_file(self):
        """保存文件"""
        if not self.current_file_path:
            show_warning("警告", "没有打开的文件")
            return
        
        try:
            content = self.code_editor.get_content()
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            file_name = os.path.basename(self.current_file_path)
            self.update_status(f"已保存: {file_name}")
            self.add_terminal_output("文件", f"已保存: {file_name}")
            show_success("成功", "文件保存成功")
        except Exception as e:
            show_error("错误", f"无法保存文件: {e}")
            self.add_terminal_output("错误", f"无法保存文件: {e}")
    
    def run_code(self):
        """运行代码"""
        if not self.current_file_path:
            show_warning("警告", "没有打开的文件")
            return
        
        # 先保存文件
        self.save_file()
        
        # 运行前确保终端显示（若未显示则加入分割面板）
        try:
            pane_names = self.center_paned.panes()
            if str(self.terminal_container) not in pane_names:
                self.center_paned.add(self.terminal_container)
                self.center_paned.paneconfig(self.terminal_container, minsize=120)
                # 标记：终端已加入分割面板
                self.terminal_in_paned = True
            else:
                # 已存在时也标记为可见状态
                self.terminal_in_paned = True
        except Exception:
            # 如果无法操作 PanedWindow，则使用 pack 作为回退
            if hasattr(self, 'terminal_container') and not self.terminal_container.winfo_ismapped():
                self.terminal_container.pack(fill="both", expand=True)
                self.terminal_in_paned = True
        
        # 执行代码（输出会显示在终端中）；将工作目录设置为当前文件所在目录，避免脚本把输出写到应用根目录
        self.output_manager.execute_file(self.current_file_path, working_directory=os.path.dirname(self.current_file_path))
        self.add_terminal_output("执行", f"正在运行: {os.path.basename(self.current_file_path)}")
    
    
    def add_model(self):
        """添加模型"""
        from ui.model_management_window import ModelDialog
        dialog = ModelDialog(self.root, self.model_manager)
        self.root.wait_window(dialog)
        
        if hasattr(dialog, 'result') and dialog.result:
            self.model_manager.add_model(dialog.result)
            self.load_models()
            self.add_terminal_output("模型", "模型添加成功")
    
    def manage_models(self):
        """管理模型"""
        # 打开模型管理窗口，并在关闭后刷新模型列表
        window = ModelManagementWindow(self.root, self.model_manager, self.settings_manager)
        try:
            self.root.wait_window(window)
        except Exception:
            pass
        # 关闭后刷新模型列表
        self.load_models()
    
    def open_settings(self):
        """打开设置窗口"""
        SettingsWindow(self.root, self.settings_manager, self.on_settings_changed)
    
    def on_settings_changed(self):
        """设置更改回调"""
        # 重新应用主题设置
        self.apply_theme_settings()
        
        # 更新文件浏览器主题
        if hasattr(self, 'file_browser'):
            self.file_browser.update_theme()
        
        # 同步代码编辑器主题
        if hasattr(self, 'code_editor'):
            try:
                self.code_editor.update_theme()
            except Exception:
                pass
        
        # 刷新AI助手的字体大小
        if hasattr(self, 'ai_assistant'):
            self.ai_assistant.refresh_font_sizes()
        
        # 刷新SQLmap路径显示
        try:
            if hasattr(self, 'sqlmap_path_label'):
                sqlmap_path = self.settings_manager.get_setting("tools.sqlmap_path", "") or "未配置"
                self.sqlmap_path_label.configure(text=f"路径: {sqlmap_path}")
        except Exception:
            pass
        
        self.add_terminal_output("设置", "设置已更新")
    
    def toggle_terminal_panel(self):
        """切换终端显示/隐藏（默认隐藏；若未加入分割面板则先加入）"""
        try:
            # 优先使用我们维护的状态标记，避免 panes() 字符串比较不一致导致无法隐藏
            if getattr(self, 'terminal_in_paned', False):
                # 终端当前在分割面板中 -> 移除
                removed = False
                try:
                    # Tkinter PanedWindow 正确的移除 Pane 的方法
                    self.center_paned.remove(self.terminal_container)
                    removed = True
                except Exception:
                    # 某些版本或实现也支持 forget，作为兼容备选
                    try:
                        self.center_paned.forget(self.terminal_container)
                        removed = True
                    except Exception:
                        removed = False
                if removed:
                    self.terminal_in_paned = False
                else:
                    # 如果移除失败，尝试回退隐藏
                    if self.terminal_container.winfo_ismapped():
                        try:
                            self.terminal_container.pack_forget()
                            self.terminal_in_paned = False
                        except Exception:
                            pass
            else:
                # 终端尚未加入 -> 加入并显示
                self.center_paned.add(self.terminal_container)
                self.center_paned.paneconfig(self.terminal_container, minsize=120)
                self.terminal_in_paned = True
                # 尝试应用保存的编辑器/终端高度比例
                try:
                    ratios = self.settings_manager.get_setting('panel_ratios', {}) or {}
                    center_vertical_ratio = ratios.get('center_vertical', 0.70)
                    ch = self.center_paned.winfo_height()
                    if ch <= 1:
                        # 延迟以等待高度与sash创建
                        self.root.after(120, lambda: self.center_paned.sash_place(0, 0, int(self.center_paned.winfo_height() * center_vertical_ratio)))
                    else:
                        self.center_paned.sash_place(0, 0, int(ch * center_vertical_ratio))
                except Exception:
                    pass
        except Exception:
            # 回退：使用 pack 控制显示
            if hasattr(self, 'terminal_container'):
                if self.terminal_container.winfo_ismapped():
                    try:
                        self.terminal_container.pack_forget()
                        self.terminal_in_paned = False
                    except Exception:
                        pass
                else:
                    self.terminal_container.pack(fill="both", expand=True)
                    self.terminal_in_paned = True
    
    def add_terminal_output(self, source: str, message: str):
        """添加终端输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        output_line = f"[{timestamp}] [{source}] {message}\n"
        
        # 如果有输出管理器，写入其标准/错误输出；否则跳回旧的文本框（兼容）
        if hasattr(self, 'output_manager') and self.output_manager:
            try:
                output_type = "stderr" if str(source).upper().startswith("STDERR") else "stdout"
                self.output_manager.append_output(output_type, output_line)
            except Exception:
                pass
        elif hasattr(self, 'terminal_text') and self.terminal_text:
            self.terminal_text.insert("end", output_line)
            self.terminal_text.see("end")
        
        # 旧的行数限制逻辑不再适用 CodeOutputManager，保留兼容处理
        if hasattr(self, 'terminal_text') and self.terminal_text:
            lines = self.terminal_text.get("1.0", "end").split('\n')
            if len(lines) > 500:
                lines_to_delete = len(lines) - 500
                self.terminal_text.delete("1.0", f"{lines_to_delete}.0")
    
    def clear_terminal_output(self):
        """清空终端输出"""
        if hasattr(self, 'output_manager') and self.output_manager:
            try:
                self.output_manager.clear_output()
            except Exception:
                pass
        elif hasattr(self, 'terminal_text') and self.terminal_text:
            self.terminal_text.delete("1.0", "end")
        self.add_terminal_output("系统", "终端输出已清空")

    def clear_sqlmap_output(self):
        """清空SQLmap面板输出"""
        try:
            if hasattr(self, 'sqlmap_output_manager') and self.sqlmap_output_manager:
                self.sqlmap_output_manager.clear_output()
            show_success("成功", "SQLmap输出已清空")
        except Exception:
            pass

    def copy_sqlmap_output(self):
        """复制SQLmap面板全部输出到剪贴板（已移除按钮，但保留方法以兼容）"""
        try:
            text = self.sqlmap_output_manager.output_text.get("1.0", "end") if hasattr(self, 'sqlmap_output_manager') else ""
            if text:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                show_success("成功", "已复制SQLmap输出到剪贴板")
        except Exception:
            show_warning("提示", "复制失败，请尝试手动选择后 Ctrl+C 复制")

    def stop_sqlmap_execution(self):
        """停止SQLmap执行并提示"""
        try:
            if hasattr(self, 'sqlmap_output_manager') and self.sqlmap_output_manager:
                self.sqlmap_output_manager.stop_execution()
                try:
                    ts = datetime.now().strftime("%H:%M:%S")
                    self.sqlmap_output_manager.append_output("stderr", f"[{ts}] [SQLmap] 执行已停止\n")
                except Exception:
                    pass
                show_info("已停止", "已终止SQLmap执行")
        except Exception as e:
            show_warning("提示", f"停止失败: {e}")
    
    def update_status(self, message):
        """更新状态"""
        self.status_label.configure(text=message)
    
    def open_file_from_ai(self, file_path: str):
        """从审计助手打开文件"""
        try:
            if os.path.exists(file_path):
                self.code_editor.open_file(file_path)
                self.update_status(f"已打开文件: {os.path.basename(file_path)}")
            else:
                self.add_terminal_output("AI助手", f"文件不存在: {file_path}")
        except Exception as e:
            self.add_terminal_output("AI助手", f"打开文件失败: {e}")
    
    def edit_file_from_ai(self, file_path: str, content: str):
        """从审计助手编辑文件"""
        try:
            # 如果文件已经在编辑器中打开，直接设置内容
            if self.code_editor.current_file == file_path:
                self.code_editor.set_content(content)
                self.update_status(f"已更新文件: {os.path.basename(file_path)}")
            else:
                # 先打开文件，再设置内容
                self.code_editor.open_file(file_path)
                self.code_editor.set_content(content)
                self.update_status(f"已打开并更新文件: {os.path.basename(file_path)}")
        except Exception as e:
            self.add_terminal_output("AI助手", f"编辑文件失败: {e}")
    
    def on_wrap_toggle(self):
        """切换编辑器的可视自动换行，不影响文件真实内容"""
        try:
            enabled = bool(self.wrap_var.get())
            if hasattr(self, 'code_editor') and self.code_editor:
                self.code_editor.set_wrap(enabled)
            # 更新状态栏提示
            self.update_status(f"自动换行已{'开启' if enabled else '关闭'}")
        except Exception:
            pass
    
    def show_hosts_config_reminder(self):
        """显示hosts文件配置提示弹窗"""
        try:
            # 使用after方法延迟显示，确保主窗口已完全加载
            self.root.after(1000, self._show_hosts_dialog)
        except Exception as e:
            print(f"显示hosts配置提示失败: {e}")
    
    def _show_hosts_dialog(self):
        """显示hosts配置对话框"""
        try:
            # 二次防护：若设置为不显示，则直接返回
            try:
                if not self.settings_manager.get_setting("ui.show_hosts_reminder", True):
                    return
            except Exception:
                pass
            # 创建自定义对话框
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("CVEhunter - 环境配置提示")
            dialog.geometry("600x500")
            dialog.resizable(False, False)
            
            # 居中显示
            dialog.transient(self.root)
            dialog.grab_set()
            # 同步窗口图标
            try:
                assets = self.get_assets_dir()
                ico_path = assets / "icon.ico"
                png_path = assets / "icon.png"
                icon_applied = False
                if sys.platform.startswith("win") and ico_path.exists():
                    try:
                        dialog.iconbitmap(str(ico_path))
                        icon_applied = True
                        print("[hosts-dialog] icon set from ICO")
                    except Exception as _e:
                        print(f"[hosts-dialog] ICO set failed: {_e}")
                if not icon_applied and png_path.exists():
                    try:
                        _img = tk.PhotoImage(file=str(png_path))
                        dialog.iconphoto(False, _img)
                        setattr(dialog, "_icon_img_ref", _img)
                        icon_applied = True
                        print("[hosts-dialog] icon set from PNG")
                    except Exception as _e:
                        print(f"[hosts-dialog] PNG set failed: {_e}")
            except Exception:
                pass
            
            # 计算居中位置
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 300
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 200
            dialog.geometry(f"600x500+{x}+{y}")
            
            # 主容器
            main_frame = ctk.CTkFrame(dialog)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # 标题
            title_label = ctk.CTkLabel(main_frame, 
                                     text="🔧 CVEhunter 环境配置", 
                                     font=ctk.CTkFont(size=24, weight="bold"))
            title_label.pack(pady=(20, 30))
            
            # 提示内容
            content_text = """为了正常使用CVEhunter代码审计工具，请按以下步骤配置hosts文件：

1. 以管理员权限运行记事本
   • 右键点击"记事本" → 选择"以管理员身份运行"

2. 打开hosts文件
   • 在记事本中，点击"文件" → "打开"
   • 导航到：%SystemRoot%\\System32\\drivers\\etc\\
   • 选择文件类型为"所有文件(*.*)"
   • 打开"hosts"文件

3. 添加配置
   • 在文件末尾添加以下行：
   127.0.0.1 cvehunter.test

4. 保存文件
   • 按Ctrl+S保存文件

配置完成后，您就可以通过 http://cvehunter.test/项目文件夹名 访问本地系统了。"""
            
            # 正文使用可滚动区域，防止被裁剪导致下方复选框不可见
            content_frame = ctk.CTkScrollableFrame(main_frame, width=560, height=260)
            content_frame.pack(fill="both", expand=False, padx=20, pady=(0, 20))
            content_label = ctk.CTkLabel(content_frame, 
                                       text=content_text,
                                       font=ctk.CTkFont(size=14),
                                       justify="left",
                                       wraplength=520)
            content_label.pack(anchor="w")

            # “不再显示”复选框变量
            # 使用 tkinter.BooleanVar，确保 .get() 返回布尔值
            dont_show_var = tk.BooleanVar(value=False)

            # 复选框放在正文下方，更容易注意到
            dont_show_checkbox = ctk.CTkCheckBox(
                main_frame,
                text="不再显示此提醒",
                variable=dont_show_var
            )
            dont_show_checkbox.pack(pady=(0, 10), padx=20, anchor="w")
            
            # 按钮容器
            button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            button_frame.pack(fill="x", padx=20, pady=(0, 20))

            # 按钮行左侧不再重复放置复选框
            
            # 确定按钮（带持久化逻辑）
            def on_ok():
                try:
                    print(f"[hosts-reminder] checkbox={dont_show_var.get()} action=ok")
                    if bool(dont_show_var.get()):
                        self.settings_manager.set_setting("ui.show_hosts_reminder", False)
                        print("[hosts-reminder] saved ui.show_hosts_reminder=False")
                except Exception:
                    pass
                dialog.destroy()

            ok_button = ctk.CTkButton(button_frame, 
                                    text="我知道了",
                                    width=120,
                                    command=on_ok)
            ok_button.pack(side="right", padx=(10, 0))
            
            # 打开文件夹按钮也应用复选框持久化
            def on_open_folder():
                try:
                    print(f"[hosts-reminder] checkbox={dont_show_var.get()} action=open_folder")
                    if bool(dont_show_var.get()):
                        self.settings_manager.set_setting("ui.show_hosts_reminder", False)
                        print("[hosts-reminder] saved ui.show_hosts_reminder=False")
                except Exception:
                    pass
                self._open_hosts_folder(dialog)

            # 打开hosts文件夹按钮
            open_folder_button = ctk.CTkButton(button_frame, 
                                             text="打开hosts文件夹",
                                             width=140,
                                             command=on_open_folder)
            open_folder_button.pack(side="right")

            # 关闭窗口时也应用复选框持久化
            def on_close_dialog():
                try:
                    print(f"[hosts-reminder] checkbox={dont_show_var.get()} action=close")
                    if bool(dont_show_var.get()):
                        self.settings_manager.set_setting("ui.show_hosts_reminder", False)
                        print("[hosts-reminder] saved ui.show_hosts_reminder=False")
                except Exception:
                    pass
                dialog.destroy()
            try:
                dialog.protocol("WM_DELETE_WINDOW", on_close_dialog)
            except Exception:
                pass
            
        except Exception as e:
            print(f"创建hosts配置对话框失败: {e}")
    
    def _open_hosts_folder(self, dialog):
        """打开hosts文件所在文件夹"""
        try:
            import subprocess
            system_root = os.environ.get("SystemRoot") or os.environ.get("WINDIR") or ""
            hosts_path = os.path.join(system_root, "System32", "drivers", "etc")
            subprocess.run(f'explorer "{hosts_path}"', shell=True)
            dialog.destroy()
        except Exception as e:
            print(f"打开hosts文件夹失败: {e}")
    
    def quit_app(self):
        """退出应用程序"""
        # 保存当前分割比例（安全尝试）
        try:
            self.save_panel_ratios()
        except Exception:
            pass
        
        # 停止任何正在执行的命令
        try:
            if hasattr(self, 'output_manager') and self.output_manager:
                self.output_manager.stop_execution()
        except Exception:
            pass
        
        # 还原stdout/stderr（避免对外部环境造成影响）
        try:
            if hasattr(self, '_orig_stdout'):
                sys.stdout = self._orig_stdout
            if hasattr(self, '_orig_stderr'):
                sys.stderr = self._orig_stderr
        except Exception:
            pass
        
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """运行应用程序"""
        self.root.mainloop()


def main():
    """主函数"""
    app = AICodeEditorApp()
    app.run()


if __name__ == "__main__":
    main()
