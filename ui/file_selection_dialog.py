import customtkinter as ctk
import tkinter as tk
import os
from pathlib import Path
from typing import List, Callable, Optional


class FileSelectionDialog:
    """改进的文件选择对话框"""
    
    def __init__(self, parent, project_path: str, on_confirm: Callable[[List[str]], None]):
        self.parent = parent
        self.project_path = project_path
        self.on_confirm = on_confirm
        self.dialog = None
        self.file_vars = {}
        self.search_var = ctk.StringVar()
        self.filter_var = ctk.StringVar(value="所有文件")
        self.selected_count_var = ctk.StringVar(value="已选择: 0 个文件")
        
        # 支持的文件扩展名
        self.supported_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss', '.sass',
            '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php', '.rb', '.go',
            '.rs', '.swift', '.kt', '.scala', '.clj', '.hs', '.ml', '.fs',
            '.sql', '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg',
            '.md', '.txt', '.rst', '.tex', '.log', '.sh', '.bat', '.ps1',
            '.dockerfile', '.gitignore', '.gitattributes', '.editorconfig',
            '.vue', '.svelte', '.elm', '.dart', '.r', '.m', '.pl', '.lua'
        }
        
        # 文件类型过滤器
        self.file_filters = {
            "所有文件": lambda ext: ext in self.supported_extensions,
            "Python": lambda ext: ext in {'.py'},
            "JavaScript/TypeScript": lambda ext: ext in {'.js', '.ts', '.jsx', '.tsx'},
            "Web前端": lambda ext: ext in {'.html', '.css', '.scss', '.sass', '.js', '.ts', '.jsx', '.tsx', '.vue'},
            "配置文件": lambda ext: ext in {'.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg'},
            "文档": lambda ext: ext in {'.md', '.txt', '.rst', '.tex'},
            "脚本": lambda ext: ext in {'.sh', '.bat', '.ps1', '.py'}
        }
        
        self.create_dialog()
    
    def create_dialog(self):
        """创建对话框"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("📁 文件交互 - 选择文件")
        self.dialog.geometry("900x700")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        # 同步窗口图标
        try:
            icon_path = Path(__file__).parent.parent / 'assets' / 'icon.ico'
            if icon_path.exists():
                self.dialog.iconbitmap(default=str(icon_path))
            else:
                png_path = Path(__file__).parent.parent / 'assets' / 'icon.png'
                if png_path.exists():
                    img = tk.PhotoImage(file=str(png_path))
                    self.dialog.iconphoto(False, img)
                    self._icon_img_ref = img
        except Exception:
            pass
        
        # 设置对话框样式
        self.dialog.configure(fg_color=("#f0f0f0", "#2b2b2b"))
        
        # 先设置初始位置，稍后在show方法中重新居中
        self.dialog.geometry("900x700+100+100")
        
        # 主框架
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 标题区域
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 20))
        
        # 主标题
        title_label = ctk.CTkLabel(
            title_frame,
            text="📁 文件交互模式",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("#2b2b2b", "#ffffff")
        )
        title_label.pack()
        
        # 副标题
        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="选择要上传到AI模型的项目文件",
            font=ctk.CTkFont(size=14),
            text_color=("#666666", "#cccccc")
        )
        subtitle_label.pack(pady=(5, 0))
        
        # 控制面板
        self.create_control_panel(main_frame)
        
        # 文件列表区域
        self.create_file_list_area(main_frame)
        
        # 底部按钮
        self.create_bottom_buttons(main_frame)
        
        # 加载文件列表
        self.load_files()
        
        # 绑定搜索事件
        self.search_var.trace("w", self.on_search_changed)
        self.filter_var.trace("w", self.on_filter_changed)
    
    def switch_view_mode(self):
        """切换视图模式"""
        # 隐藏当前视图
        self.scrollable_frame.pack_forget()
        
        # 切换到新视图
        if self.view_mode.get() == "tree":
            self.scrollable_frame = self.tree_scrollable_frame
        else:
            self.scrollable_frame = self.list_scrollable_frame
        
        # 显示新视图
        self.scrollable_frame.pack(fill="both", expand=True)
        
        # 重新显示文件
        self.display_files()
    
    def build_file_tree(self):
        """构建文件树结构"""
        tree = {}
        filtered_files = self.get_filtered_files()
        
        for file_info in filtered_files:
            path_parts = file_info['rel_path'].split(os.sep)
            current = tree
            
            # 构建目录结构
            for i, part in enumerate(path_parts[:-1]):
                if part not in current:
                    current[part] = {'type': 'folder', 'children': {}, 'files': []}
                current = current[part]['children']
            
            # 添加文件
            folder_name = os.path.dirname(file_info['rel_path']) if os.path.dirname(file_info['rel_path']) else '.'
            if folder_name == '.':
                if '.' not in tree:
                    tree['.'] = {'type': 'folder', 'children': {}, 'files': []}
                tree['.']['files'].append(file_info)
            else:
                # 找到文件所在的文件夹
                current = tree
                for part in path_parts[:-1]:
                    current = current[part]['children']
                parent_folder = tree
                for part in path_parts[:-1]:
                    if part not in parent_folder:
                        parent_folder[part] = {'type': 'folder', 'children': {}, 'files': []}
                    if part == path_parts[-2]:  # 最后一个文件夹
                        parent_folder[part]['files'].append(file_info)
                    parent_folder = parent_folder[part]['children']
        
        return tree
    
    def display_tree_node(self, parent_widget, name, node, level=0):
        """递归显示树节点"""
        indent = "  " * level
        
        if node['type'] == 'folder':
            # 创建文件夹节点
            folder_frame = ctk.CTkFrame(parent_widget, fg_color="transparent")
            folder_frame.pack(fill="x", pady=1)
            
            # 文件夹标签
            folder_label = ctk.CTkLabel(
                folder_frame,
                text=f"{indent}📁 {name}",
                font=ctk.CTkFont(size=11, weight="bold"),
                anchor="w"
            )
            folder_label.pack(anchor="w", padx=10, pady=2)
            
            # 显示文件夹中的文件
            for file_info in node.get('files', []):
                self.create_tree_file_item(parent_widget, file_info, level + 1)
            
            # 递归显示子文件夹
            for child_name, child_node in node.get('children', {}).items():
                self.display_tree_node(parent_widget, child_name, child_node, level + 1)
    
    def create_tree_file_item(self, parent_widget, file_info, level=0):
        """在树形视图中创建文件项"""
        indent = "  " * level
        
        # 文件项框架
        item_frame = ctk.CTkFrame(parent_widget, height=35)
        item_frame.pack(fill="x", pady=1, padx=(level*15, 5))
        item_frame.pack_propagate(False)
        
        # 复选框变量
        if file_info['full_path'] not in self.file_vars:
            self.file_vars[file_info['full_path']] = ctk.BooleanVar()
            self.file_vars[file_info['full_path']].trace("w", lambda *args: self.update_selection_count())
        
        var = self.file_vars[file_info['full_path']]
        
        # 复选框
        checkbox = ctk.CTkCheckBox(
            item_frame,
            text="",
            variable=var,
            width=20
        )
        checkbox.pack(side="left", padx=(5, 5), pady=5)
        
        # 文件信息
        file_text = f"📄 {file_info['name']} ({file_info['size_str']})"
        file_label = ctk.CTkLabel(
            item_frame,
            text=file_text,
            font=ctk.CTkFont(size=10),
            anchor="w"
        )
        file_label.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # 文件类型标签
        ext_label = ctk.CTkLabel(
            item_frame,
            text=file_info['ext'],
            font=ctk.CTkFont(size=9, weight="bold"),
            width=35,
            corner_radius=8,
            fg_color=self.get_ext_color(file_info['ext'])
        )
        ext_label.pack(side="right", padx=(5, 5), pady=5)
    
    def create_control_panel(self, parent):
        """创建控制面板"""
        control_frame = ctk.CTkFrame(parent, fg_color="transparent")
        control_frame.pack(fill="x", pady=(0, 15))
        
        # 第一行：搜索和过滤
        top_row = ctk.CTkFrame(control_frame, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 10))
        
        # 搜索框
        search_label = ctk.CTkLabel(top_row, text="🔍 搜索:")
        search_label.pack(side="left", padx=(0, 5))
        
        search_entry = ctk.CTkEntry(
            top_row,
            textvariable=self.search_var,
            placeholder_text="输入文件名或路径...",
            width=250
        )
        search_entry.pack(side="left", padx=(0, 20))
        
        # 文件类型过滤
        filter_label = ctk.CTkLabel(top_row, text="📋 类型:")
        filter_label.pack(side="left", padx=(0, 5))
        
        filter_combo = ctk.CTkComboBox(
            top_row,
            variable=self.filter_var,
            values=list(self.file_filters.keys()),
            width=150,
            state="readonly"
        )
        filter_combo.pack(side="left")
        
        # 第二行：选择操作和统计
        bottom_row = ctk.CTkFrame(control_frame, fg_color="transparent")
        bottom_row.pack(fill="x")
        
        # 选择操作按钮
        select_all_btn = ctk.CTkButton(
            bottom_row,
            text="全选",
            command=self.select_all,
            width=80,
            height=28
        )
        select_all_btn.pack(side="left", padx=(0, 10))
        
        deselect_all_btn = ctk.CTkButton(
            bottom_row,
            text="取消全选",
            command=self.deselect_all,
            width=80,
            height=28
        )
        deselect_all_btn.pack(side="left", padx=(0, 10))
        
        select_filtered_btn = ctk.CTkButton(
            bottom_row,
            text="选择当前显示",
            command=self.select_filtered,
            width=100,
            height=28
        )
        select_filtered_btn.pack(side="left", padx=(0, 20))
        
        # 选择统计
        count_label = ctk.CTkLabel(
            bottom_row,
            textvariable=self.selected_count_var,
            font=ctk.CTkFont(weight="bold")
        )
        count_label.pack(side="right")
    
    def create_file_list_area(self, parent):
        """创建文件列表区域"""
        # 文件列表框架
        list_frame = ctk.CTkFrame(parent)
        list_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # 创建视图切换按钮
        view_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        view_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        view_label = ctk.CTkLabel(view_frame, text="视图模式:", font=ctk.CTkFont(size=12))
        view_label.pack(side="left", padx=(0, 10))
        
        self.view_mode = ctk.StringVar(value="tree")
        
        tree_btn = ctk.CTkRadioButton(
            view_frame, 
            text="🌳 树形视图", 
            variable=self.view_mode, 
            value="tree",
            command=self.switch_view_mode
        )
        tree_btn.pack(side="left", padx=(0, 10))
        
        list_btn = ctk.CTkRadioButton(
            view_frame, 
            text="📋 列表视图", 
            variable=self.view_mode, 
            value="list",
            command=self.switch_view_mode
        )
        list_btn.pack(side="left")
        
        # 滚动区域容器
        self.scroll_container = ctk.CTkFrame(list_frame)
        self.scroll_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # 树形视图滚动区域
        self.tree_scrollable_frame = ctk.CTkScrollableFrame(
            self.scroll_container,
            label_text="项目文件树",
            label_font=ctk.CTkFont(size=14, weight="bold")
        )
        
        # 列表视图滚动区域
        self.list_scrollable_frame = ctk.CTkScrollableFrame(
            self.scroll_container,
            label_text="项目文件列表",
            label_font=ctk.CTkFont(size=14, weight="bold")
        )
        
        # 默认显示树形视图
        self.scrollable_frame = self.tree_scrollable_frame
        self.scrollable_frame.pack(fill="both", expand=True)
    
    def create_bottom_buttons(self, parent):
        """创建底部按钮"""
        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.pack(fill="x")
        
        # 取消按钮
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="取消",
            command=self.dialog.destroy,
            width=100,
            height=35
        )
        cancel_btn.pack(side="left")
        
        # 确认按钮
        confirm_btn = ctk.CTkButton(
            button_frame,
            text="🚀 开始分析",
            command=self.confirm_selection,
            width=120,
            height=35,
            font=ctk.CTkFont(weight="bold")
        )
        confirm_btn.pack(side="right")
        
        # 项目路径显示
        path_label = ctk.CTkLabel(
            button_frame,
            text=f"项目路径: {self.project_path}",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        path_label.pack(side="bottom", pady=(5, 0))
    
    def load_files(self):
        """加载项目文件"""
        if not os.path.exists(self.project_path):
            return
        
        # 排除的目录
        exclude_dirs = {
            '__pycache__', '.git', '.svn', '.hg', 'node_modules', '.vscode',
            '.idea', 'build', 'dist', 'target', 'bin', 'obj', '.pytest_cache',
            '.mypy_cache', '.tox', 'venv', '.venv', 'env', '.env'
        }
        
        # 扫描项目文件
        self.project_files = []
        for root, dirs, files in os.walk(self.project_path):
            # 过滤目录
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file)
                
                if ext.lower() in self.supported_extensions:
                    # 计算相对路径
                    rel_path = os.path.relpath(file_path, self.project_path)
                    file_size = os.path.getsize(file_path)
                    self.project_files.append({
                        'rel_path': rel_path,
                        'full_path': file_path,
                        'name': file,
                        'ext': ext.lower(),
                        'size': file_size,
                        'size_str': self.format_file_size(file_size)
                    })
        
        # 按文件名排序
        self.project_files.sort(key=lambda x: x['rel_path'])
        
        # 显示文件列表
        self.display_files()
    
    def format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def display_files(self):
        """显示文件列表"""
        # 清空现有内容
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # 获取过滤后的文件
        filtered_files = self.get_filtered_files()
        
        if not filtered_files:
            no_files_label = ctk.CTkLabel(
                self.scrollable_frame,
                text="没有找到匹配的文件",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_files_label.pack(pady=20)
            return
        
        # 根据视图模式显示文件
        if self.view_mode.get() == "tree":
            self.display_tree_view()
        else:
            self.display_list_view(filtered_files)
        
        # 更新选择计数
        self.update_selection_count()
    
    def display_tree_view(self):
        """显示树形视图"""
        tree = self.build_file_tree()
        
        # 显示根目录文件
        if '.' in tree:
            root_node = tree['.']
            if root_node.get('files'):
                root_label = ctk.CTkLabel(
                    self.scrollable_frame,
                    text="📁 根目录",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    anchor="w"
                )
                root_label.pack(anchor="w", padx=10, pady=(5, 2))
                
                for file_info in root_node['files']:
                    self.create_tree_file_item(self.scrollable_frame, file_info, 1)
        
        # 显示其他文件夹
        for folder_name, folder_node in tree.items():
            if folder_name != '.':
                self.display_tree_node(self.scrollable_frame, folder_name, folder_node, 0)
    
    def display_list_view(self, filtered_files):
        """显示列表视图"""
        for file_info in filtered_files:
            self.create_file_item(file_info)
    
    def create_file_item(self, file_info):
        """创建文件项"""
        # 文件项框架
        item_frame = ctk.CTkFrame(self.scrollable_frame, height=50)
        item_frame.pack(fill="x", pady=2, padx=5)
        item_frame.pack_propagate(False)
        
        # 复选框变量
        if file_info['full_path'] not in self.file_vars:
            self.file_vars[file_info['full_path']] = ctk.BooleanVar()
            self.file_vars[file_info['full_path']].trace("w", lambda *args: self.update_selection_count())
        
        var = self.file_vars[file_info['full_path']]
        
        # 复选框
        checkbox = ctk.CTkCheckBox(
            item_frame,
            text="",
            variable=var,
            width=20
        )
        checkbox.pack(side="left", padx=(10, 5), pady=10)
        
        # 文件信息框架
        info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=(5, 10))
        
        # 文件名和路径
        name_label = ctk.CTkLabel(
            info_frame,
            text=file_info['name'],
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        name_label.pack(anchor="w", pady=(5, 0))
        
        # 路径和大小
        details_text = f"{file_info['rel_path']} • {file_info['size_str']}"
        details_label = ctk.CTkLabel(
            info_frame,
            text=details_text,
            font=ctk.CTkFont(size=10),
            text_color="gray",
            anchor="w"
        )
        details_label.pack(anchor="w", pady=(0, 5))
        
        # 文件类型标签
        ext_label = ctk.CTkLabel(
            item_frame,
            text=file_info['ext'],
            font=ctk.CTkFont(size=10, weight="bold"),
            width=40,
            corner_radius=10,
            fg_color=self.get_ext_color(file_info['ext'])
        )
        ext_label.pack(side="right", padx=(5, 10), pady=10)
    
    def get_ext_color(self, ext):
        """根据文件扩展名获取颜色"""
        color_map = {
            '.py': "#3776ab",
            '.js': "#f7df1e",
            '.ts': "#3178c6",
            '.html': "#e34f26",
            '.css': "#1572b6",
            '.json': "#000000",
            '.md': "#083fa1",
            '.txt': "#808080"
        }
        return color_map.get(ext, "#666666")
    
    def get_filtered_files(self):
        """获取过滤后的文件列表"""
        search_text = self.search_var.get().lower()
        filter_type = self.filter_var.get()
        filter_func = self.file_filters[filter_type]
        
        filtered = []
        for file_info in self.project_files:
            # 应用类型过滤
            if not filter_func(file_info['ext']):
                continue
            
            # 应用搜索过滤
            if search_text and search_text not in file_info['rel_path'].lower():
                continue
            
            filtered.append(file_info)
        
        return filtered
    
    def on_search_changed(self, *args):
        """搜索内容改变时的回调"""
        self.display_files()
    
    def on_filter_changed(self, *args):
        """过滤器改变时的回调"""
        self.display_files()
    
    def select_all(self):
        """全选所有文件"""
        for var in self.file_vars.values():
            var.set(True)
    
    def deselect_all(self):
        """取消全选"""
        for var in self.file_vars.values():
            var.set(False)
    
    def select_filtered(self):
        """选择当前显示的文件"""
        filtered_files = self.get_filtered_files()
        for file_info in filtered_files:
            if file_info['full_path'] in self.file_vars:
                self.file_vars[file_info['full_path']].set(True)
    
    def update_selection_count(self):
        """更新选择计数"""
        selected_count = sum(1 for var in self.file_vars.values() if var.get())
        self.selected_count_var.set(f"已选择: {selected_count} 个文件")
    
    def confirm_selection(self):
        """确认选择"""
        selected_files = [path for path, var in self.file_vars.items() if var.get()]
        
        if not selected_files:
            # 显示警告
            warning_dialog = ctk.CTkToplevel(self.dialog)
            warning_dialog.title("提示")
            warning_dialog.geometry("300x150")
            warning_dialog.transient(self.dialog)
            warning_dialog.grab_set()
            
            # 居中显示
            warning_dialog.update_idletasks()
            x = (warning_dialog.winfo_screenwidth() // 2) - (300 // 2)
            y = (warning_dialog.winfo_screenheight() // 2) - (150 // 2)
            warning_dialog.geometry(f"300x150+{x}+{y}")
            
            warning_label = ctk.CTkLabel(
                warning_dialog,
                text="⚠️ 请至少选择一个文件",
                font=ctk.CTkFont(size=14)
            )
            warning_label.pack(pady=30)
            
            ok_btn = ctk.CTkButton(
                warning_dialog,
                text="确定",
                command=warning_dialog.destroy,
                width=80
            )
            ok_btn.pack(pady=10)
            
            return
        
        # 关闭对话框并调用回调
        self.dialog.destroy()
        self.on_confirm(selected_files)
    
    def show(self):
        """显示对话框"""
        # 确保父窗口已经完全渲染
        self.parent.update_idletasks()
        self.dialog.update_idletasks()
        
        # 获取AI助手容器的位置和大小
        # self.parent 是 AICodeAssistant，它是在 ai_container 中的
        try:
            # 获取AI助手的实际位置和大小
            parent_x = self.parent.winfo_rootx()
            parent_y = self.parent.winfo_rooty()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
        except:
            # 如果获取失败，使用屏幕中央
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            parent_x = screen_width // 4
            parent_y = screen_height // 4
            parent_width = screen_width // 2
            parent_height = screen_height // 2
        
        # 计算对话框在AI助手区域中间的位置
        dialog_width = 900
        dialog_height = 700
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # 确保对话框不会超出屏幕边界
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = max(0, min(x, screen_width - dialog_width))
        y = max(0, min(y, screen_height - dialog_height))
        
        # 重新设置对话框位置
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        self.dialog.focus()
        self.dialog.wait_window()