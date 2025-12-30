"""
代码编辑器组件
支持语法高亮、代码折叠、多标签页等功能
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import re
from pathlib import Path
from typing import Callable, Optional, Dict, List
import threading
from utils.notification_system import show_info, show_success, show_warning, show_error, show_confirm
import tkinter.font as tkfont


class CodeTab:
    """代码标签页类"""
    
    def __init__(self, file_path: Optional[str] = None, content: str = ""):
        self.file_path = file_path
        self.content = content
        self.is_modified = False
        self.cursor_position = "1.0"
        self.scroll_position = 0.0
        
    @property
    def title(self) -> str:
        """获取标签页标题"""
        if self.file_path:
            name = os.path.basename(self.file_path)
            return f"*{name}" if self.is_modified else name
        else:
            return "*新文件" if self.is_modified else "新文件"
    
    @property
    def file_extension(self) -> str:
        """获取文件扩展名"""
        if self.file_path:
            return Path(self.file_path).suffix.lower()
        return ""


class SyntaxHighlighter:
    """语法高亮器"""
    
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.setup_tags()
        
        # 语法规则
        self.syntax_rules = {
            '.py': self.python_rules(),
            '.js': self.javascript_rules(),
            '.ts': self.javascript_rules(),
            '.html': self.html_rules(),
            '.css': self.css_rules(),
            '.json': self.json_rules(),
            '.md': self.markdown_rules(),
        }
    
    def setup_tags(self):
        """设置文本标签样式（更丰富的高亮配色）"""
        # 初始根据当前外观模式应用配色
        try:
            mode = ctk.get_appearance_mode()
        except Exception:
            mode = "Dark"
        self.apply_theme(mode)

    def apply_theme(self, mode: str):
        """根据主题模式更新语法高亮前景色"""
        if mode == "Dark":
            palette = {
                "keyword": "#7aa2f7",
                "string": "#9ece6a",
                "comment": "#565f89",
                "number": "#ff9e64",
                "function": "#bb9af7",
                "class": "#9ece6a",
                "builtin": "#7dcfff",
                "operator": "#c0caf5",
                "html_tag": "#7aa2f7",
                "html_attr": "#7dcfff",
                "css_property": "#7dcfff",
                "css_value": "#9ece6a",
                "json_key": "#7dcfff",
                "json_value": "#9ece6a",
            }
        else:
            palette = {
                "keyword": "#1d4ed8",
                "string": "#059669",
                "comment": "#6b7280",
                "number": "#b45309",
                "function": "#7c3aed",
                "class": "#10b981",
                "builtin": "#0ea5e9",
                "operator": "#374151",
                "html_tag": "#1d4ed8",
                "html_attr": "#0ea5e9",
                "css_property": "#0ea5e9",
                "css_value": "#059669",
                "json_key": "#0ea5e9",
                "json_value": "#059669",
            }
        for tag, color in palette.items():
            try:
                self.text_widget.tag_configure(tag, foreground=color)
            except Exception:
                pass
    
    def python_rules(self):
        """Python语法规则"""
        return [
            # 关键字
            (r'\b(def|class|if|elif|else|for|while|try|except|finally|with|as|import|from|return|yield|break|continue|pass|lambda|and|or|not|in|is|True|False|None)\b', "keyword"),
            # 字符串
            (r'""".*?"""', "string"),
            (r"'''.*?'''", "string"),
            (r'".*?"', "string"),
            (r"'.*?'", "string"),
            # 注释
            (r'#.*$', "comment"),
            # 数字
            (r'\b\d+\.?\d*\b', "number"),
            # 函数定义
            (r'\bdef\s+(\w+)', "function"),
            # 类定义
            (r'\bclass\s+(\w+)', "class"),
            # 内置函数
            (r'\b(print|len|range|enumerate|zip|map|filter|sorted|sum|max|min|abs|round|int|float|str|list|dict|set|tuple)\b', "builtin"),
        ]
    
    def javascript_rules(self):
        """JavaScript语法规则"""
        return [
            # 关键字
            (r'\b(function|var|let|const|if|else|for|while|do|switch|case|default|break|continue|return|try|catch|finally|throw|new|this|typeof|instanceof|in|of|class|extends|super|import|export|from|as|async|await|yield|true|false|null|undefined)\b', "keyword"),
            # 字符串
            (r'`.*?`', "string"),
            (r'".*?"', "string"),
            (r"'.*?'", "string"),
            # 注释
            (r'//.*$', "comment"),
            (r'/\*.*?\*/', "comment"),
            # 数字
            (r'\b\d+\.?\d*\b', "number"),
            # 函数
            (r'\bfunction\s+(\w+)', "function"),
            (r'(\w+)\s*\(', "function"),
        ]
    
    def html_rules(self):
        """HTML语法规则"""
        return [
            # HTML标签
            (r'</?[^>]+>', "html_tag"),
            # 属性
            (r'\w+="[^"]*"', "html_attr"),
            # 注释
            (r'<!--.*?-->', "comment"),
        ]
    
    def css_rules(self):
        """CSS语法规则"""
        return [
            # 属性
            (r'[\w-]+\s*:', "css_property"),
            # 值
            (r':\s*[^;]+', "css_value"),
            # 注释
            (r'/\*.*?\*/', "comment"),
            # 字符串
            (r'".*?"', "string"),
            (r"'.*?'", "string"),
        ]
    
    def json_rules(self):
        """JSON语法规则"""
        return [
            # 键
            (r'"[^"]*"\s*:', "json_key"),
            # 字符串值
            (r':\s*"[^"]*"', "json_value"),
            # 数字
            (r'\b\d+\.?\d*\b', "number"),
            # 布尔值和null
            (r'\b(true|false|null)\b', "keyword"),
        ]
    
    def markdown_rules(self):
        """Markdown语法规则"""
        return [
            # 标题
            (r'^#{1,6}.*$', "keyword"),
            # 代码块
            (r'```.*?```', "string"),
            (r'`.*?`', "string"),
            # 链接
            (r'\[.*?\]\(.*?\)', "builtin"),
            # 粗体
            (r'\*\*.*?\*\*', "function"),
            # 斜体
            (r'\*.*?\*', "comment"),
        ]
    
    def highlight_syntax(self, file_extension: str):
        """应用语法高亮"""
        # 清除现有标签
        for tag in ["keyword", "string", "comment", "number", "function", "class", "builtin", "operator", "html_tag", "html_attr", "css_property", "css_value", "json_key", "json_value"]:
            self.text_widget.tag_remove(tag, "1.0", "end")
        
        # 获取对应的语法规则
        rules = self.syntax_rules.get(file_extension, [])
        if not rules:
            return
        
        # 获取文本内容
        content = self.text_widget.get("1.0", "end-1c")
        
        # 应用语法规则
        for pattern, tag in rules:
            for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                start_line = content[:match.start()].count('\n') + 1
                start_col = match.start() - content.rfind('\n', 0, match.start()) - 1
                end_line = content[:match.end()].count('\n') + 1
                end_col = match.end() - content.rfind('\n', 0, match.end()) - 1
                
                start_pos = f"{start_line}.{start_col}"
                end_pos = f"{end_line}.{end_col}"
                
                self.text_widget.tag_add(tag, start_pos, end_pos)


class FindReplaceDialog:
    """查找替换对话框"""
    
    def __init__(self, parent, text_widget):
        self.parent = parent
        self.text_widget = text_widget
        self.dialog = None
        self.find_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.case_sensitive = tk.BooleanVar()
        self.whole_word = tk.BooleanVar()
        
    def show_find_dialog(self):
        """显示查找对话框"""
        if self.dialog:
            self.dialog.destroy()
        
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("查找")
        self.dialog.geometry("400x150")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        # 同步窗口图标
        self._apply_window_icon(self.dialog)
        
        # 查找输入框
        find_frame = ctk.CTkFrame(self.dialog)
        find_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(find_frame, text="查找:").pack(side="left", padx=5)
        find_entry = ctk.CTkEntry(find_frame, textvariable=self.find_var, width=250)
        find_entry.pack(side="left", padx=5, fill="x", expand=True)
        find_entry.focus()
        
        # 选项
        options_frame = ctk.CTkFrame(self.dialog)
        options_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkCheckBox(options_frame, text="区分大小写", variable=self.case_sensitive).pack(side="left", padx=5)
        ctk.CTkCheckBox(options_frame, text="全词匹配", variable=self.whole_word).pack(side="left", padx=5)
        
        # 按钮
        button_frame = ctk.CTkFrame(self.dialog)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(button_frame, text="查找下一个", command=self.find_next).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="查找上一个", command=self.find_previous).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="关闭", command=self.dialog.destroy).pack(side="right", padx=5)
        
        # 绑定回车键
        find_entry.bind("<Return>", lambda e: self.find_next())

    def _apply_window_icon(self, window):
        try:
            icon_path = Path(__file__).parent.parent / 'assets' / 'icon.ico'
            if icon_path.exists():
                window.iconbitmap(default=str(icon_path))
            else:
                png_path = Path(__file__).parent.parent / 'assets' / 'icon.png'
                if png_path.exists():
                    img = tk.PhotoImage(file=str(png_path))
                    window.iconphoto(False, img)
                    setattr(window, "_icon_img_ref", img)
        except Exception:
            pass
    
    def show_replace_dialog(self):
        """显示替换对话框"""
        if self.dialog:
            self.dialog.destroy()
        
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("替换")
        self.dialog.geometry("400x200")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        # 同步窗口图标
        self._apply_window_icon(self.dialog)
        
        # 查找输入框
        find_frame = ctk.CTkFrame(self.dialog)
        find_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(find_frame, text="查找:").pack(side="left", padx=5)
        find_entry = ctk.CTkEntry(find_frame, textvariable=self.find_var, width=250)
        find_entry.pack(side="left", padx=5, fill="x", expand=True)
        find_entry.focus()
        
        # 替换输入框
        replace_frame = ctk.CTkFrame(self.dialog)
        replace_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(replace_frame, text="替换:").pack(side="left", padx=5)
        replace_entry = ctk.CTkEntry(replace_frame, textvariable=self.replace_var, width=250)
        replace_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # 选项
        options_frame = ctk.CTkFrame(self.dialog)
        options_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkCheckBox(options_frame, text="区分大小写", variable=self.case_sensitive).pack(side="left", padx=5)
        ctk.CTkCheckBox(options_frame, text="全词匹配", variable=self.whole_word).pack(side="left", padx=5)
        
        # 按钮
        button_frame = ctk.CTkFrame(self.dialog)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(button_frame, text="查找下一个", command=self.find_next).pack(side="left", padx=2)
        ctk.CTkButton(button_frame, text="替换", command=self.replace_current).pack(side="left", padx=2)
        ctk.CTkButton(button_frame, text="全部替换", command=self.replace_all).pack(side="left", padx=2)
        ctk.CTkButton(button_frame, text="关闭", command=self.dialog.destroy).pack(side="right", padx=5)
    
    def find_next(self):
        """查找下一个"""
        search_text = self.find_var.get()
        if not search_text:
            return
        
        # 从当前光标位置开始搜索
        start_pos = self.text_widget.index(tk.INSERT)
        
        # 构建搜索选项
        search_options = []
        if not self.case_sensitive.get():
            search_options.append("-nocase")
        if self.whole_word.get():
            search_options.append("-regexp")
            search_text = r'\b' + re.escape(search_text) + r'\b'
        
        # 搜索
        pos = self.text_widget.search(search_text, start_pos, "end", *search_options)
        if pos:
            # 选中找到的文本
            end_pos = f"{pos}+{len(self.find_var.get())}c"
            self.text_widget.tag_remove("sel", "1.0", "end")
            self.text_widget.tag_add("sel", pos, end_pos)
            self.text_widget.mark_set(tk.INSERT, end_pos)
            self.text_widget.see(pos)
        else:
            # 从头开始搜索
            pos = self.text_widget.search(search_text, "1.0", start_pos, *search_options)
            if pos:
                end_pos = f"{pos}+{len(self.find_var.get())}c"
                self.text_widget.tag_remove("sel", "1.0", "end")
                self.text_widget.tag_add("sel", pos, end_pos)
                self.text_widget.mark_set(tk.INSERT, end_pos)
                self.text_widget.see(pos)
            else:
                show_info("查找", "未找到指定文本")
    
    def find_previous(self):
        """查找上一个"""
        search_text = self.find_var.get()
        if not search_text:
            return
        
        # 从当前光标位置向前搜索
        start_pos = self.text_widget.index(tk.INSERT)
        
        # 构建搜索选项
        search_options = ["-backwards"]
        if not self.case_sensitive.get():
            search_options.append("-nocase")
        if self.whole_word.get():
            search_options.append("-regexp")
            search_text = r'\b' + re.escape(search_text) + r'\b'
        
        # 搜索
        pos = self.text_widget.search(search_text, start_pos, "1.0", *search_options)
        if pos:
            # 选中找到的文本
            end_pos = f"{pos}+{len(self.find_var.get())}c"
            self.text_widget.tag_remove("sel", "1.0", "end")
            self.text_widget.tag_add("sel", pos, end_pos)
            self.text_widget.mark_set(tk.INSERT, pos)
            self.text_widget.see(pos)
        else:
            show_info("查找", "未找到指定文本")
    
    def replace_current(self):
        """替换当前选中的文本"""
        try:
            if self.text_widget.tag_ranges("sel"):
                self.text_widget.delete("sel.first", "sel.last")
                self.text_widget.insert(tk.INSERT, self.replace_var.get())
                self.find_next()
        except tk.TclError:
            pass
    
    def replace_all(self):
        """替换所有匹配的文本"""
        search_text = self.find_var.get()
        replace_text = self.replace_var.get()
        
        if not search_text:
            return
        
        content = self.text_widget.get("1.0", "end-1c")
        
        # 构建替换选项
        flags = 0
        if not self.case_sensitive.get():
            flags |= re.IGNORECASE
        
        if self.whole_word.get():
            pattern = r'\b' + re.escape(search_text) + r'\b'
        else:
            pattern = re.escape(search_text)
        
        # 执行替换
        new_content, count = re.subn(pattern, replace_text, content, flags=flags)
        
        if count > 0:
            self.text_widget.delete("1.0", "end")
            self.text_widget.insert("1.0", new_content)
            show_success("替换", f"已替换 {count} 处")
        else:
            show_info("替换", "未找到要替换的文本")


class CodeEditor:
    """代码编辑器组件"""
    
    def __init__(self, parent, on_content_change: Optional[Callable] = None):
        self.parent = parent
        self.on_content_change = on_content_change
        
        # 标签页管理
        self.tabs: List[CodeTab] = []
        self.current_tab_index = -1
        
        # 创建UI
        self.create_ui()
        
        # 语法高亮器
        self.syntax_highlighter = SyntaxHighlighter(self.text_widget)
        
        # 查找替换对话框
        self.find_replace_dialog = FindReplaceDialog(self.parent, self.text_widget)
        
        # 自动保存定时器
        self.auto_save_timer = None
        
        # 创建默认标签页
        self.new_file()
    
    def create_ui(self):
        """创建用户界面"""
        # 标签页容器 - 隐藏不显示
        self.tab_frame = ctk.CTkFrame(self.parent, 
                                    fg_color="transparent", 
                                    border_width=0,
                                    corner_radius=0,
                                    height=0)
        # 不pack标签页容器，直接隐藏
        
        # 标签页按钮容器 - 隐藏不显示
        self.tab_button_frame = ctk.CTkFrame(self.tab_frame, 
                                           fg_color="transparent", 
                                           border_width=0,
                                           corner_radius=0)
        # 不pack标签页按钮容器
        
        # 编辑器容器 - 确保没有红色边框
        self.editor_frame = ctk.CTkFrame(self.parent, 
                                       border_width=0,
                                       corner_radius=4,
                                       fg_color="transparent")
        self.editor_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # 创建文本编辑器
        self.create_text_editor()
        
        # 状态信息
        self.info_frame = ctk.CTkFrame(self.parent)
        self.info_frame.pack(fill="x", padx=0, pady=0)
        
        self.line_col_label = ctk.CTkLabel(self.info_frame, text="行: 1, 列: 1")
        self.line_col_label.pack(side="left", padx=10, pady=2)
        
        self.encoding_label = ctk.CTkLabel(self.info_frame, text="UTF-8")
        self.encoding_label.pack(side="right", padx=10, pady=2)
    
    def create_text_editor(self):
        """创建文本编辑器"""
        # 文本框容器 - 现代化外观
        self.text_container = ctk.CTkFrame(self.editor_frame, 
                                    fg_color=("#2b2b2b", "#2b2b2b"),
                                    corner_radius=8,
                                    border_width=1,
                                    border_color=("#3b3b3b", "#3b3b3b"))
        self.text_container.pack(fill="both", expand=True, padx=0, pady=0)
        
        # 选择更美观的等宽字体（优先 Fira Code，其次 JetBrains Mono/Cascadia Code/Consolas）
        try:
            available_fonts = set(tkfont.families())
        except Exception:
            available_fonts = set()
        preferred = ["Fira Code", "JetBrains Mono", "Cascadia Code", "Consolas"]
        family = next((f for f in preferred if f in available_fonts), "Consolas")
        editor_font = (family, 14, "normal")
        
        # 行号显示 - 更佳的对比度与字体
        self.line_numbers = tk.Text(
            self.text_container,
            width=5,
            padx=8,
            takefocus=0,
            border=0,
            state='disabled',
            wrap='none',
            background='#2b2b2b',
            foreground='#64748b',
            font=editor_font,
            relief='flat',
            borderwidth=0
        )
        self.line_numbers.pack(side="left", fill="y")
        # 行号当前行高亮样式
        self.line_numbers.tag_configure("current_line_number", background="#1f2937", foreground="#e5e7eb")
        
        # 主文本编辑器 - 更丰富的深色配色与更美观字体
        self.text_widget = tk.Text(
            self.text_container,
            wrap="none",
            undo=True,
            maxundo=50,
            font=editor_font,
            background='#2b2b2b',
            foreground='#e5e7eb',
            insertbackground='#93c5fd',
            selectbackground='#3b3b3b',
            selectforeground='#ffffff',
            tabs=('2c', '4c', '6c', '8c', '10c', '12c', '14c', '16c'),
            relief='flat',
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=5
        )
        self.text_widget.pack(side="left", fill="both", expand=True)
        # 当前行高亮样式
        self.text_widget.tag_configure("current_line", background="#1f2937")
        
        # 滚动条
        v_scrollbar = tk.Scrollbar(self.text_container, orient="vertical", command=self.on_scroll)
        v_scrollbar.pack(side="right", fill="y")
        # 水平滚动条
        self.h_scrollbar = tk.Scrollbar(self.text_container, orient="horizontal", command=self.text_widget.xview)
        self.h_scrollbar.pack(side="bottom", fill="x")
        
        # 绑定滚动
        self.text_widget.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        self.line_numbers.configure(yscrollcommand=v_scrollbar.set)
        
        # 绑定事件
        self.text_widget.bind("<KeyRelease>", self.on_text_change)
        self.text_widget.bind("<Button-1>", self.on_text_change)
        self.text_widget.bind("<MouseWheel>", self.on_mouse_wheel)
        self.text_widget.bind("<Shift-MouseWheel>", self.on_shift_mouse_wheel)
        self.text_widget.bind("<Control-s>", lambda e: self.save_file())
        self.text_widget.bind("<Control-f>", lambda e: self.show_find_dialog())
        self.text_widget.bind("<Control-h>", lambda e: self.show_replace_dialog())
        
        # 初始化行号
        self.update_line_numbers()
        # 根据当前主题应用编辑器配色
        try:
            self.update_theme()
        except Exception:
            pass
    
    def on_scroll(self, *args):
        """滚动事件处理"""
        self.text_widget.yview(*args)
        self.line_numbers.yview(*args)
    
    def on_mouse_wheel(self, event):
        """鼠标滚轮事件处理"""
        # 计算滚动量
        delta = -1 * (event.delta / 120)
        self.text_widget.yview_scroll(int(delta), "units")
        self.line_numbers.yview_scroll(int(delta), "units")
        return "break"
    
    def on_shift_mouse_wheel(self, event):
        """按住 Shift 使用鼠标滚轮进行水平滚动"""
        try:
            # Windows 下 event.delta > 0 表示向上滚，按住 Shift 约定为向左；反之向右
            direction = -1 if event.delta > 0 else 1
            self.text_widget.xview_scroll(direction * 3, "units")
            return "break"
        except Exception:
            pass
    
    def on_text_change(self, event=None):
        """文本内容改变事件"""
        self.update_line_numbers()
        self.update_cursor_info()
        # 高亮当前行
        self.highlight_current_line()
        
        # 标记当前标签页为已修改
        if self.current_tab_index >= 0:
            self.tabs[self.current_tab_index].is_modified = True
            self.tabs[self.current_tab_index].content = self.text_widget.get("1.0", "end-1c")
            self.update_tab_title()
        
        # 应用语法高亮
        if self.current_tab_index >= 0:
            file_ext = self.tabs[self.current_tab_index].file_extension
            if file_ext:
                # 延迟执行语法高亮以提高性能
                self.parent.after_idle(lambda: self.syntax_highlighter.highlight_syntax(file_ext))
        
        # 触发内容改变回调
        if self.on_content_change:
            self.on_content_change()
        
        # 重置自动保存定时器
        self.reset_auto_save_timer()
    
    def update_line_numbers(self):
        """更新行号显示"""
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', 'end')
        
        # 获取文本行数
        line_count = int(self.text_widget.index('end-1c').split('.')[0])
        
        # 生成行号
        line_numbers_text = '\n'.join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert('1.0', line_numbers_text)
        
        # 高亮当前行号
        try:
            cursor_line = int(self.text_widget.index(tk.INSERT).split('.')[0])
            self.line_numbers.tag_remove('current_line_number', '1.0', 'end')
            self.line_numbers.tag_add('current_line_number', f"{cursor_line}.0", f"{cursor_line}.end")
        except Exception:
            pass
        
        self.line_numbers.config(state='disabled')
    
    def update_cursor_info(self):
        """更新光标位置信息"""
        cursor_pos = self.text_widget.index(tk.INSERT)
        line, col = cursor_pos.split('.')
        self.line_col_label.configure(text=f"行: {line}, 列: {int(col) + 1}")
    
    def update_tab_title(self):
        """更新标签页标题"""
        if self.current_tab_index >= 0:
            tab = self.tabs[self.current_tab_index]
            # 这里需要更新标签页按钮的文本
            # 实际实现中需要维护标签页按钮的引用
            pass
    
    def reset_auto_save_timer(self):
        """重置自动保存定时器"""
        if self.auto_save_timer:
            self.parent.after_cancel(self.auto_save_timer)
        
        # 5秒后自动保存
        self.auto_save_timer = self.parent.after(5000, self.auto_save)
    
    def auto_save(self):
        """自动保存"""
        if self.current_tab_index >= 0:
            tab = self.tabs[self.current_tab_index]
            if tab.is_modified and tab.file_path:
                try:
                    with open(tab.file_path, 'w', encoding='utf-8') as f:
                        f.write(tab.content)
                    tab.is_modified = False
                    self.update_tab_title()
                except Exception as e:
                    print(f"自动保存失败: {e}")
    
    # 文件操作方法
    def new_file(self):
        """新建文件"""
        tab = CodeTab()
        self.tabs.append(tab)
        self.switch_to_tab(len(self.tabs) - 1)
        self.text_widget.delete("1.0", "end")
        self.update_line_numbers()
    
    def open_file(self, file_path: str):
        """打开文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否已经打开
            for i, tab in enumerate(self.tabs):
                if tab.file_path == file_path:
                    self.switch_to_tab(i)
                    return
            
            # 创建新标签页
            tab = CodeTab(file_path, content)
            self.tabs.append(tab)
            self.switch_to_tab(len(self.tabs) - 1)
            
            # 加载内容
            self.text_widget.delete("1.0", "end")
            self.text_widget.insert("1.0", content)
            self.update_line_numbers()
            
            # 应用语法高亮
            self.syntax_highlighter.highlight_syntax(tab.file_extension)
            
        except Exception as e:
            show_error("错误", f"无法打开文件: {e}")
    
    def save_file(self):
        """保存文件"""
        if self.current_tab_index < 0:
            return
        
        tab = self.tabs[self.current_tab_index]
        
        if not tab.file_path:
            self.save_as_file()
            return
        
        try:
            content = self.text_widget.get("1.0", "end-1c")
            with open(tab.file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            tab.content = content
            tab.is_modified = False
            self.update_tab_title()
            
        except Exception as e:
            show_error("错误", f"保存文件失败: {e}")
    
    def save_as_file(self):
        """另存为文件"""
        if self.current_tab_index < 0:
            return
        
        file_path = filedialog.asksaveasfilename(
            title="另存为",
            filetypes=[
                ("Python文件", "*.py"),
                ("JavaScript文件", "*.js"),
                ("HTML文件", "*.html"),
                ("CSS文件", "*.css"),
                ("JSON文件", "*.json"),
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            tab = self.tabs[self.current_tab_index]
            tab.file_path = file_path
            self.save_file()
    
    def switch_to_tab(self, index: int):
        """切换到指定标签页"""
        if 0 <= index < len(self.tabs):
            # 保存当前标签页状态
            if self.current_tab_index >= 0:
                current_tab = self.tabs[self.current_tab_index]
                current_tab.content = self.text_widget.get("1.0", "end-1c")
                current_tab.cursor_position = self.text_widget.index(tk.INSERT)
                current_tab.scroll_position = self.text_widget.yview()[0]
            
            # 切换到新标签页
            self.current_tab_index = index
            tab = self.tabs[index]
            
            # 加载标签页内容
            self.text_widget.delete("1.0", "end")
            self.text_widget.insert("1.0", tab.content)
            self.text_widget.mark_set(tk.INSERT, tab.cursor_position)
            self.text_widget.yview_moveto(tab.scroll_position)
            
            # 更新UI
            self.update_line_numbers()
            self.update_cursor_info()
            
            # 应用语法高亮
            if tab.file_extension:
                self.syntax_highlighter.highlight_syntax(tab.file_extension)
    
    def close_tab(self, index: int):
        """关闭标签页"""
        if 0 <= index < len(self.tabs):
            tab = self.tabs[index]
            
            if tab.is_modified:
                result = show_confirm(
                    "关闭标签页",
                    f"文件 '{tab.title}' 有未保存的更改，是否保存？"
                )
                if result is True:
                    if index == self.current_tab_index:
                        self.save_file()
                    else:
                        # 保存其他标签页
                        if tab.file_path:
                            try:
                                with open(tab.file_path, 'w', encoding='utf-8') as f:
                                    f.write(tab.content)
                            except Exception as e:
                                show_error("错误", f"保存文件失败: {e}")
                                return
                elif result is None:
                    return  # 取消关闭
            
            # 删除标签页
            del self.tabs[index]
            
            # 调整当前标签页索引
            if index < self.current_tab_index:
                self.current_tab_index -= 1
            elif index == self.current_tab_index:
                if self.tabs:
                    new_index = min(index, len(self.tabs) - 1)
                    self.switch_to_tab(new_index)
                else:
                    self.current_tab_index = -1
                    self.text_widget.delete("1.0", "end")
                    self.update_line_numbers()
    
    # 编辑操作方法
    def undo(self):
        """撤销"""
        try:
            self.text_widget.edit_undo()
        except tk.TclError:
            pass
    
    def redo(self):
        """重做"""
        try:
            self.text_widget.edit_redo()
        except tk.TclError:
            pass
    
    def show_find_dialog(self):
        """显示查找对话框"""
        self.find_replace_dialog.show_find_dialog()
    
    def show_replace_dialog(self):
        """显示替换对话框"""
        self.find_replace_dialog.show_replace_dialog()
    
    # 获取信息的方法
    def get_current_file(self) -> Optional[str]:
        """获取当前文件路径"""
        if self.current_tab_index >= 0:
            return self.tabs[self.current_tab_index].file_path
        return None
    
    def get_open_files(self):
        """获取所有已打开的文件路径列表"""
        open_files = []
        for tab_id, tab_info in self.tabs.items():
            file_path = tab_info.get('file_path')
            if file_path and os.path.exists(file_path):
                open_files.append(file_path)
        return open_files
    
    def get_content(self) -> str:
        """获取当前内容"""
        return self.text_widget.get("1.0", "end-1c")
    
    def set_content(self, content: str):
        """设置文本内容"""
        self.text_widget.delete("1.0", "end")
        self.text_widget.insert("1.0", content)
        self.update_line_numbers()
        # 应用语法高亮
        if self.current_tab_index >= 0:
            file_ext = self.tabs[self.current_tab_index].file_extension
            if file_ext:
                self.syntax_highlighter.highlight_syntax(file_ext)
    
    def get_cursor_position(self) -> str:
        """获取光标位置"""
        return self.text_widget.index(tk.INSERT)
    
    def has_unsaved_changes(self) -> bool:
        """检查是否有未保存的更改"""
        return any(tab.is_modified for tab in self.tabs)


    def highlight_current_line(self):
        """高亮当前行背景"""
        try:
            # 先移除旧的高亮
            self.text_widget.tag_remove('current_line', '1.0', 'end')
            # 添加新的高亮到光标所在行
            line = self.text_widget.index(tk.INSERT).split('.')[0]
            self.text_widget.tag_add('current_line', f"{line}.0", f"{line}.end+1c")
        except Exception:
            pass

    def update_theme(self):
        """根据当前外观模式更新编辑器与语法高亮配色"""
        try:
            mode = ctk.get_appearance_mode()
        except Exception:
            mode = "Dark"
        if mode == "Dark":
            container_bg = "#2b2b2b"
            border_color = "#3b3b3b"
            text_bg = "#2b2b2b"
            text_fg = "#e5e7eb"
            insert = "#93c5fd"
            select_bg = "#3b3b3b"
            select_fg = "#ffffff"
            line_bg = "#2b2b2b"
            line_fg = "#64748b"
            current_line_bg = "#1f2937"
            current_line_num_bg = "#1f2937"
            current_line_num_fg = "#e5e7eb"
        else:
            container_bg = "#ffffff"
            border_color = "#d0d7de"
            text_bg = "#ffffff"
            text_fg = "#1f2937"
            insert = "#2563eb"
            select_bg = "#cfe3ff"
            select_fg = "#000000"
            line_bg = "#f7f9fb"
            line_fg = "#6b7280"
            current_line_bg = "#eef2ff"
            current_line_num_bg = "#e5e9f2"
            current_line_num_fg = "#1f2937"
        try:
            if hasattr(self, 'text_container') and self.text_container:
                self.text_container.configure(fg_color=container_bg, border_color=border_color)
        except Exception:
            pass
        self.text_widget.configure(background=text_bg, foreground=text_fg,
                                   insertbackground=insert,
                                   selectbackground=select_bg,
                                   selectforeground=select_fg)
        self.line_numbers.configure(background=line_bg, foreground=line_fg)
        self.text_widget.tag_configure('current_line', background=current_line_bg)
        self.line_numbers.tag_configure('current_line_number',
                                        background=current_line_num_bg,
                                        foreground=current_line_num_fg)
        # 同步语法高亮主题
        try:
            if hasattr(self, 'syntax_highlighter') and self.syntax_highlighter:
                self.syntax_highlighter.apply_theme(mode)
        except Exception:
            pass

    def set_wrap(self, enabled: bool):
        """设置编辑器可视自动换行（不改变文件真实内容）"""
        try:
            wrap_mode = "word" if enabled else "none"
            self.text_widget.configure(wrap=wrap_mode)
            # 自动换行开启时隐藏水平滚动条，关闭时显示
            if enabled:
                try:
                    self.h_scrollbar.pack_forget()
                except Exception:
                    pass
            else:
                try:
                    self.h_scrollbar.pack(side="bottom", fill="x")
                except Exception:
                    pass
        except Exception:
            pass