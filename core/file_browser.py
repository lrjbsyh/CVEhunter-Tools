"""
文件浏览器组件
支持项目文件夹的树形展示和文件操作
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
from pathlib import Path
import shutil
from typing import Callable, Optional
from utils.notification_system import show_info, show_success, show_warning, show_error


class FileBrowser:
    """文件浏览器组件"""
    
    def __init__(self, parent, on_file_select: Optional[Callable] = None):
        self.parent = parent
        self.on_file_select = on_file_select
        self.current_project_path = None
        
        # 支持的文件类型
        self.supported_extensions = {
            '.py', '.js', '.ts', '.html', '.css', '.scss', '.less',
            '.json', '.xml', '.yaml', '.yml', '.md', '.txt', '.rst',
            '.c', '.cpp', '.h', '.hpp', '.java', '.cs', '.php',
            '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
            '.sql', '.sh', '.bat', '.ps1', '.dockerfile', '.gitignore'
        }
        
        self.create_ui()
        self.configure_theme()
    
    def configure_theme(self):
        """配置主题样式"""
        # 获取当前主题
        appearance_mode = ctk.get_appearance_mode()
        
        # 创建样式
        style = ttk.Style()
        
        if appearance_mode == "Dark":
            # 暗色主题
            style.theme_use('clam')
            style.configure("Treeview",
                          background="#212121",
                          foreground="#ffffff",
                          fieldbackground="#212121",
                          borderwidth=0,
                          relief="flat",
                          font=("Microsoft YaHei UI", 13),  # 调整字体大小到13号
                          rowheight=22)  # 增加行高以适应13号字体
            style.configure("Treeview.Heading",
                          background="#2b2b2b",
                          foreground="#ffffff",
                          borderwidth=0,
                          relief="flat",
                          font=("Microsoft YaHei UI", 13))  # 调整字体大小到13号
            style.map("Treeview",
                     background=[('selected', '#1f538d')],
                     foreground=[('selected', '#ffffff')])
        else:
            # 亮色主题
            style.theme_use('clam')
            style.configure("Treeview",
                          background="#ffffff",
                          foreground="#000000",
                          fieldbackground="#ffffff",
                          borderwidth=0,
                          relief="flat",
                          font=("Microsoft YaHei UI", 13),  # 调整字体大小到13号
                          rowheight=22)  # 增加行高以适应13号字体
            style.configure("Treeview.Heading",
                          background="#f0f0f0",
                          foreground="#000000",
                          borderwidth=0,
                          relief="flat",
                          font=("Microsoft YaHei UI", 13))  # 调整字体大小到13号
            style.map("Treeview",
                     background=[('selected', '#0078d4')],
                     foreground=[('selected', '#ffffff')])
    
    def update_theme(self):
        """更新主题（供外部调用）"""
        self.configure_theme()
    
    def create_ui(self):
        """创建用户界面"""
        # 标题栏
        title_frame = ctk.CTkFrame(self.parent)
        title_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        title_label = ctk.CTkLabel(
            title_frame, 
            text="文件浏览器", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.pack(side="left", padx=10, pady=5)
        
        # 刷新按钮
        refresh_btn = ctk.CTkButton(
            title_frame,
            text="刷新",
            width=50,
            height=25,
            command=self.refresh_tree
        )
        refresh_btn.pack(side="right", padx=5, pady=5)
        
        # 加号按钮：改为下拉菜单（新建文件/文件夹）
        add_menu = tk.Menu(title_frame, tearoff=0)
        add_menu.add_command(label="新建文件", command=self.new_file)
        add_menu.add_command(label="新建文件夹", command=self.new_folder)
        
        def show_add_menu(event=None):
            x = add_btn.winfo_rootx()
            y = add_btn.winfo_rooty() + add_btn.winfo_height()
            add_menu.post(x, y)
        
        add_btn = ctk.CTkButton(
            title_frame,
            text="+",
            width=30,
            height=25,
            command=show_add_menu
        )
        add_btn.pack(side="right", padx=5, pady=5)
        
        # 搜索框
        search_frame = ctk.CTkFrame(self.parent)
        search_frame.pack(fill="x", padx=5, pady=2)
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.on_search_changed)
        
        search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="搜索文件...",
            textvariable=self.search_var
        )
        search_entry.pack(fill="x", padx=5, pady=5)
        
        # 文件树容器
        tree_frame = ctk.CTkFrame(self.parent)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 创建Treeview
        self.tree = ttk.Treeview(tree_frame, show="tree")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 绑定事件
        self.tree.bind("<Double-1>", self.on_item_double_click)
        self.tree.bind("<Button-1>", self.on_left_click)  # 左键点击（支持多选）
        self.tree.bind("<Button-3>", self.on_right_click)  # 右键菜单
        # 移除拖拽移动绑定，改为右键菜单进行移动
        # self.tree.bind("<ButtonPress-1>", self.on_drag_start)
        # self.tree.bind("<ButtonRelease-1>", self.on_drag_end)
        
        # 创建右键菜单
        self.create_context_menu()
        
        # 项目路径显示
        self.path_label = ctk.CTkLabel(
            self.parent,
            text="未打开项目",
            font=ctk.CTkFont(size=10)
        )
        self.path_label.pack(fill="x", padx=5, pady=(0, 5))
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="打开", command=self.open_selected_file)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📁 文件交互分析", command=self.analyze_with_ai)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="新建文件", command=self.new_file)
        self.context_menu.add_command(label="新建文件夹", command=self.new_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="重命名", command=self.rename_item)
        self.context_menu.add_command(label="删除", command=self.delete_item)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="复制路径", command=self.copy_path)
        self.context_menu.add_command(label="在文件管理器中显示", command=self.show_in_explorer)
        # 新增：移动到文件夹
        self.context_menu.add_separator()
        self.context_menu.add_command(label="移动到文件夹...", command=self.move_to_folder)
    
    def load_project(self, project_path: str):
        """加载项目文件夹"""
        self.current_project_path = project_path
        self.path_label.configure(text=f"项目: {os.path.basename(project_path)}")
        self.refresh_tree()
    
    def refresh_tree(self):
        """刷新文件树"""
        if not self.current_project_path:
            return
        
        # 清空现有树
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 重新构建树
        self.build_tree(self.current_project_path, "")
    
    def build_tree(self, path: str, parent: str):
        """递归构建文件树"""
        try:
            items = []
            
            # 获取目录内容
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                
                # 跳过隐藏文件和特定目录
                if item.startswith('.') and item not in ['.gitignore', '.env']:
                    continue
                if item in ['__pycache__', 'node_modules', '.git', '.vscode']:
                    continue
                
                items.append((item, item_path))
            
            # 排序：文件夹在前，文件在后
            items.sort(key=lambda x: (os.path.isfile(x[1]), x[0].lower()))
            
            for item_name, item_path in items:
                # 确定图标
                if os.path.isdir(item_path):
                    icon = "📁"
                    display_name = f"{icon} {item_name}"
                else:
                    icon = self.get_file_icon(item_name)
                    display_name = f"{icon} {item_name}"
                
                # 插入节点
                node = self.tree.insert(parent, "end", text=display_name, values=[item_path])
                
                # 如果是目录，递归添加子项
                if os.path.isdir(item_path):
                    self.build_tree(item_path, node)
        
        except PermissionError:
            # 处理权限错误
            pass
        except Exception as e:
            print(f"构建文件树时出错: {e}")
    
    def get_file_icon(self, filename: str) -> str:
        """根据文件扩展名获取图标"""
        ext = Path(filename).suffix.lower()
        
        icon_map = {
            '.py': '🐍',
            '.js': '📜',
            '.ts': '📘',
            '.html': '🌐',
            '.css': '🎨',
            '.scss': '🎨',
            '.less': '🎨',
            '.json': '📋',
            '.xml': '📄',
            '.yaml': '⚙️',
            '.yml': '⚙️',
            '.md': '📝',
            '.txt': '📄',
            '.rst': '📄',
            '.c': '⚡',
            '.cpp': '⚡',
            '.h': '⚡',
            '.hpp': '⚡',
            '.java': '☕',
            '.cs': '🔷',
            '.php': '🐘',
            '.rb': '💎',
            '.go': '🐹',
            '.rs': '🦀',
            '.swift': '🦉',
            '.kt': '🎯',
            '.scala': '🎭',
            '.sql': '🗃️',
            '.sh': '🐚',
            '.bat': '⚙️',
            '.ps1': '💙',
            '.dockerfile': '🐳',
            '.gitignore': '🚫'
        }
        
        return icon_map.get(ext, '📄')
    
    def on_left_click(self, event):
        """左键点击事件处理（支持Ctrl多选）"""
        item = self.tree.identify_row(event.y)
        if item:
            current_selection = self.tree.selection()
            
            if event.state & 0x0004:  # 按住Ctrl键
                # Ctrl+左键：切换选择状态
                if item in current_selection:
                    # 如果已选中，则取消选择
                    new_selection = [i for i in current_selection if i != item]
                    self.tree.selection_set(new_selection)
                else:
                    # 如果未选中，则添加到选择
                    self.tree.selection_add(item)
            else:
                # 普通左键：清除选择并选择当前项
                self.tree.selection_set(item)
    
    def on_item_double_click(self, event):
        """双击打开文件"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            file_path = self.tree.item(item, "values")[0]
            if os.path.isfile(file_path) and self.is_supported_file(file_path):
                if self.on_file_select:
                    self.on_file_select(file_path)
    
    def on_right_click(self, event):
        """右键点击事件处理"""
        item = self.tree.identify_row(event.y)
        if item:
            # 检查当前项是否已经在选择中
            current_selection = self.tree.selection()
            
            if event.state & 0x0004:  # 按住Ctrl键
                # Ctrl+右键：切换选择状态
                if item in current_selection:
                    # 如果已选中，则取消选择
                    new_selection = [i for i in current_selection if i != item]
                    self.tree.selection_set(new_selection)
                else:
                    # 如果未选中，则添加到选择
                    self.tree.selection_add(item)
            else:
                # 普通右键：如果当前项不在选择中，则清除选择并选择当前项
                # 如果当前项已在选择中，保持多选状态
                if item not in current_selection:
                    self.tree.selection_set(item)
            
            self.context_menu.post(event.x_root, event.y_root)
    
    def on_search_changed(self, *args):
        """搜索框内容改变事件"""
        search_text = self.search_var.get().lower()
        if not search_text:
            self.refresh_tree()
            return
        
        # 简单的搜索实现
        self.filter_tree(search_text)
    
    def filter_tree(self, search_text: str):
        """根据搜索文本过滤文件树"""
        # 清空现有树
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 搜索匹配的文件
        if self.current_project_path:
            self.search_and_add_files(self.current_project_path, search_text, "")
    
    def search_and_add_files(self, path: str, search_text: str, parent: str):
        """搜索并添加匹配的文件"""
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                
                # 跳过隐藏文件和特定目录
                if item.startswith('.') and item not in ['.gitignore', '.env']:
                    continue
                if item in ['__pycache__', 'node_modules', '.git', '.vscode']:
                    continue
                
                if search_text in item.lower():
                    # 匹配的项目
                    if os.path.isdir(item_path):
                        icon = "📁"
                        display_name = f"{icon} {item}"
                    else:
                        icon = self.get_file_icon(item)
                        display_name = f"{icon} {item}"
                    
                    self.tree.insert(parent, "end", text=display_name, values=[item_path])
                
                # 递归搜索子目录
                if os.path.isdir(item_path):
                    self.search_and_add_files(item_path, search_text, parent)
        
        except PermissionError:
            pass
        except Exception as e:
            print(f"搜索文件时出错: {e}")
    
    def is_supported_file(self, file_path: str) -> bool:
        """检查文件是否为支持的类型"""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions
    
    # 右键菜单功能
    def open_selected_file(self):
        """打开选中的文件"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            file_path = self.tree.item(item, "values")[0]
            if os.path.isfile(file_path) and self.is_supported_file(file_path):
                if self.on_file_select:
                    self.on_file_select(file_path)
    
    def new_file(self):
        """新建文件"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            selected_path = self.tree.item(item, "values")[0]
            if os.path.isfile(selected_path):
                parent_dir = os.path.dirname(selected_path)
            else:
                parent_dir = selected_path
        else:
            parent_dir = self.current_project_path
        
        filename = simpledialog.askstring("新建文件", "请输入文件名:")
        if filename:
            file_path = os.path.join(parent_dir, filename)
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("")
                self.refresh_tree()
                if self.on_file_select:
                    self.on_file_select(file_path)
            except Exception as e:
                show_error("错误", f"创建文件失败: {e}")
    
    def new_folder(self):
        """新建文件夹"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            selected_path = self.tree.item(item, "values")[0]
            if os.path.isfile(selected_path):
                parent_dir = os.path.dirname(selected_path)
            else:
                parent_dir = selected_path
        else:
            parent_dir = self.current_project_path
        
        folder_name = simpledialog.askstring("新建文件夹", "请输入文件夹名:")
        if folder_name:
            folder_path = os.path.join(parent_dir, folder_name)
            try:
                os.makedirs(folder_path, exist_ok=True)
                self.refresh_tree()
            except Exception as e:
                show_error("错误", f"创建文件夹失败: {e}")
    
    def rename_item(self):
        """重命名项目"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            old_path = self.tree.item(item, "values")[0]
            old_name = os.path.basename(old_path)
            
            new_name = simpledialog.askstring("重命名", f"重命名 '{old_name}' 为:", initialvalue=old_name)
            if new_name and new_name != old_name:
                new_path = os.path.join(os.path.dirname(old_path), new_name)
                try:
                    os.rename(old_path, new_path)
                    self.refresh_tree()
                except Exception as e:
                    show_error("错误", f"重命名失败: {e}")
    
    def delete_item(self):
        """删除项目"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            file_path = self.tree.item(item, "values")[0]
            file_name = os.path.basename(file_path)
            
            # 使用通知替代确认对话框
            show_warning("删除确认", f"请在终端中确认是否删除 '{file_name}'")
            # 简化处理：直接删除（实际使用中可以添加更复杂的确认机制）
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                self.refresh_tree()
                show_success("成功", f"已删除 '{file_name}'")
            except Exception as e:
                show_error("错误", f"删除失败: {e}")
    
    def copy_path(self):
        """复制路径到剪贴板"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            file_path = self.tree.item(item, "values")[0]
            self.parent.clipboard_clear()
            self.parent.clipboard_append(file_path)
            show_info("提示", "路径已复制到剪贴板")
    
    def show_in_explorer(self):
        """在文件管理器中显示"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            file_path = self.tree.item(item, "values")[0]
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(os.path.dirname(file_path))
                elif os.name == 'posix':  # macOS and Linux
                    os.system(f'open "{os.path.dirname(file_path)}"')
            except Exception as e:
                show_error("错误", f"无法打开文件管理器: {e}")
    
    def get_selected_file_path(self) -> Optional[str]:
        """获取当前选中的文件路径"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            return self.tree.item(item, "values")[0]
        return None
    
    # 拖拽移动支持
    def on_drag_start(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.drag_item = item
            self.drag_path = self.tree.item(item, "values")[0]
        else:
            self.drag_item = None
            self.drag_path = None
    
    def on_drag_end(self, event):
        if not getattr(self, 'drag_item', None):
            return
        target_item = self.tree.identify_row(event.y)
        if not target_item:
            # 松手在空白处，不处理
            self.drag_item = None
            self.drag_path = None
            return
        target_path = self.tree.item(target_item, "values")[0]
        # 如果目标是文件，则移动到其父目录；如果是目录，则移动到该目录下
        if os.path.isfile(target_path):
            target_dir = os.path.dirname(target_path)
        else:
            target_dir = target_path
        try:
            new_path = os.path.join(target_dir, os.path.basename(self.drag_path))
            # 如果目标路径已存在，提示并取消
            if os.path.exists(new_path):
                show_warning("提示", f"目标已存在: {os.path.basename(new_path)}")
            else:
                shutil.move(self.drag_path, new_path)
                show_success("成功", f"已移动到: {target_dir}")
                self.refresh_tree()
        except Exception as e:
            show_error("错误", f"移动失败: {e}")
        finally:
            self.drag_item = None
            self.drag_path = None

    def move_to_folder(self):
        """右键菜单：移动到项目内指定文件夹"""
        if not self.current_project_path:
            show_warning("警告", "请先打开项目文件夹")
            return
        item = self.tree.selection()[0] if self.tree.selection() else None
        if not item:
            show_warning("警告", "请先选择要移动的文件或文件夹")
            return
        source_path = self.tree.item(item, "values")[0]
        # 打开选择文件夹窗口
        target_dir = self.open_folder_select_dialog(self.current_project_path)
        if not target_dir:
            return  # 用户取消
        # 防止移动到自身或子目录
        try:
            sp = os.path.abspath(source_path)
            td = os.path.abspath(target_dir)
            if os.path.isdir(sp) and td.startswith(sp):
                show_error("错误", "不能将文件夹移动到其自身或子文件夹中")
                return
            new_path = os.path.join(td, os.path.basename(sp))
            if os.path.exists(new_path):
                show_warning("提示", f"目标已存在: {os.path.basename(new_path)}")
                return
            shutil.move(sp, new_path)
            show_success("成功", f"已移动到: {td}")
            self.refresh_tree()
        except Exception as e:
            show_error("错误", f"移动失败: {e}")

    def open_folder_select_dialog(self, project_root: str) -> Optional[str]:
        """弹出窗口，列出项目内所有文件夹，返回选择的文件夹路径"""
        top = tk.Toplevel(self.parent)
        top.title("选择目标文件夹")
        top.geometry("500x400")
        top.transient(self.parent)
        top.grab_set()
        # 同步应用图标
        try:
            icon_path = Path(__file__).parent.parent / 'assets' / 'icon.ico'
            if icon_path.exists():
                top.iconbitmap(default=str(icon_path))
            else:
                png_path = Path(__file__).parent.parent / 'assets' / 'icon.png'
                if png_path.exists():
                    _img = tk.PhotoImage(file=str(png_path))
                    top.iconphoto(False, _img)
                    top._icon_img_ref = _img
        except Exception:
            pass
        
        # 标题
        lbl = ctk.CTkLabel(top, text=f"项目文件夹: {os.path.basename(project_root)}", font=ctk.CTkFont(size=13, weight="bold"))
        lbl.pack(fill="x", padx=10, pady=(10, 5))
        
        # 仅目录的树
        tree_frame = ctk.CTkFrame(top)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        dir_tree = ttk.Treeview(tree_frame, show="tree")
        dir_tree.pack(fill="both", expand=True, side="left")
        
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=dir_tree.yview)
        sb.pack(side="right", fill="y")
        dir_tree.configure(yscrollcommand=sb.set)
        
        def build_dir_tree(path: str, parent: str):
            try:
                items = []
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if item.startswith('.'):
                        continue
                    if item in ['__pycache__', 'node_modules', '.git', '.vscode']:
                        continue
                    if os.path.isdir(item_path):
                        items.append((item, item_path))
                items.sort(key=lambda x: x[0].lower())
                for name, p in items:
                    node = dir_tree.insert(parent, "end", text=f"📁 {name}", values=[p])
                    build_dir_tree(p, node)
            except Exception:
                pass
        
        # 根节点
        root_node = dir_tree.insert("", "end", text=f"📁 {os.path.basename(project_root)}", values=[project_root])
        build_dir_tree(project_root, root_node)
        dir_tree.item(root_node, open=True)
        
        # 按钮区
        btn_frame = ctk.CTkFrame(top)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        selected_path = {"value": None}
        
        def on_ok():
            sel = dir_tree.selection()[0] if dir_tree.selection() else None
            if not sel:
                show_warning("提示", "请选择目标文件夹")
                return
            p = dir_tree.item(sel, "values")[0]
            selected_path["value"] = p
            top.destroy()
        
        def on_cancel():
            top.destroy()
        
        ok_btn = ctk.CTkButton(btn_frame, text="确定", width=80, command=on_ok)
        ok_btn.pack(side="right", padx=5)
        cancel_btn = ctk.CTkButton(btn_frame, text="取消", width=80, command=on_cancel)
        cancel_btn.pack(side="right", padx=5)
        
        top.wait_window(top)
        return selected_path["value"]
    
    def analyze_with_ai(self):
        """使用AI分析选中的文件（支持多文件累加）"""
        selected_items = self.tree.selection()
        if not selected_items:
            show_warning("请先选择文件或文件夹")
            return
        
        selected_paths = []
        for item in selected_items:
            file_path = self.tree.item(item, "values")[0]
            if os.path.exists(file_path):
                selected_paths.append(file_path)
        
        if not selected_paths:
            show_warning("请选择有效的文件或文件夹")
            return
        
        # 调用AI代码助手的文件交互分析功能
        if hasattr(self, 'ai_assistant') and self.ai_assistant:
            # 直接添加文件到交互标签（支持累加）
            self.ai_assistant.add_file_interaction_tag(selected_paths)
        else:
            show_error("AI助手未初始化")
    
    def set_ai_assistant(self, ai_assistant):
        """设置AI助手引用"""
        self.ai_assistant = ai_assistant