import customtkinter as ctk
import tkinter as tk
import threading
import os
import time
import uuid
import sys

from typing import Any, Dict, Callable

# 导入断点管理器
try:
    from .breakpoint_manager import BreakpointManager
except Exception:
    BreakpointManager = None

# 导入文件交互客户端
try:
    from .file_interaction_client import FileInteractionClient
except Exception:
    FileInteractionClient = None

try:
    from ..ui.file_selection_dialog import FileSelectionDialog
except Exception:
    FileSelectionDialog = None

# 优先使用绝对导入，运行脚本模式下更稳妥
try:
    from ui.thinking_animation import ThinkingAnimation, FileInteractionTag
except Exception:
    try:
        from ..ui.thinking_animation import ThinkingAnimation, FileInteractionTag
    except Exception:
        ThinkingAnimation = None
        FileInteractionTag = None

class AICodeAssistant(ctk.CTkFrame):
    def __init__(self, parent, model_manager=None, chat_manager=None, settings_manager=None, breakpoint_manager=None):
        super().__init__(parent)
        self.model_manager = model_manager
        self.chat_manager = chat_manager
        self.settings_manager = settings_manager
        self.breakpoint_manager = breakpoint_manager
        # 如果未传入断点管理器，尝试本地实例化；失败则保持为 None
        if self.breakpoint_manager is None and BreakpointManager is not None:
            try:
                self.breakpoint_manager = BreakpointManager()
            except Exception:
                self.breakpoint_manager = None
        self.file_contexts = {}
        self.current_project_path = None
        self.current_file_path = None
        self.on_file_open_request = None
        self.on_file_edit_request = None
        self.pending_query_after_readall = None
        self.last_readall_summary_message_id = None
        self.read_mode_menu = None
        self.stop_ai_request = False
        self.ai_thread = None
        self.waiting_dots = 0
        # 初始化消息与选择相关数据结构
        self.message_components = []
        self.messages = []
        self.selected_messages = set()
        self.selection_mode = False
        # Toast与动画
        self.current_toast = None
        self.toast_anchor_widget = None
        self.thinking_message_id = None
        self.thinking_animation_job = None
        self.thinking_animation = None
        
        # 文件交互标签
        self.file_interaction_tag = None
        # 文件交互标记
        self.file_interaction_active = False
        self.selected_files_for_interaction = []  # 存储选中的文件路径
        self.file_interaction_client = None  # 文件交互客户端
        self.file_interaction_counter = 0  # 文件交互计数器
        
        # 初始化文件交互客户端
        if FileInteractionClient:
            try:
                self.file_interaction_client = FileInteractionClient(model_manager=self.model_manager, chat_manager=self.chat_manager)
            except Exception as e:
                print(f"初始化文件交互客户端失败: {e}")
        
        # 进度UI
        self.progress_label = ctk.CTkLabel(self, text="")
        self.progress_bar = ctk.CTkProgressBar(self)
        
        # 顶部项目信息栏（显示当前项目名称）
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=10, pady=(10, 0))
        self.project_info_label = ctk.CTkLabel(header_frame, text="项目: 未选择项目", font=ctk.CTkFont(size=12, weight="bold"))
        self.project_info_label.pack(side="left")
        
        # 对话内容滚动区域 - 使用CTkScrollableFrame而不是CTkTextbox
        self.chat_display_frame = ctk.CTkFrame(self)
        self.chat_display_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # 对话内容滚动区域 - 使用CTkScrollableFrame而不是CTkTextbox
        self.chat_display = ctk.CTkScrollableFrame(self.chat_display_frame)
        self.chat_display.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # 批量工具栏
        self.create_batch_toolbar(self.chat_display_frame)
        
        # 底部文件标签栏（可折叠）
        self.create_bottom_tag_bar(self.chat_display_frame)
        
        # 预置快捷操作按钮（阅读/分析/清理）
        self.create_quick_actions(self.chat_display_frame)
        
        # 输入区域 - 与原始聊天模块保持一致
        self.create_input_area(self.chat_display_frame)
        
        # 绑定项目文件选择方法（使用独立模块提供的方法注入）
        try:
            from .show_project_files_selection import add_show_project_files_selection
            add_show_project_files_selection(type(self))
        except Exception:
            # 绑定失败不影响其他功能
            pass
    
    def create_batch_toolbar(self, parent):
        """创建批量操作工具栏 - 与原始聊天模块完全一致"""
        # 选择模式切换按钮
        self.selection_toggle_btn = ctk.CTkButton(
            parent, 
            text="选择消息", 
            width=80,
            command=self.toggle_selection_mode
        )
        self.selection_toggle_btn.pack(pady=(0, 10))
        
        # 批量操作工具栏
        self.batch_toolbar = ctk.CTkFrame(parent)
        # 初始隐藏工具栏
        
        # 批量操作按钮框架
        button_frame = ctk.CTkFrame(self.batch_toolbar, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=5)
        
        # 全选按钮
        self.select_all_btn = ctk.CTkButton(
            button_frame, 
            text="全选", 
            width=60,
            command=self.select_all_messages
        )
        self.select_all_btn.pack(side="left", padx=5)
        
        # 取消全选按钮
        self.deselect_all_btn = ctk.CTkButton(
            button_frame, 
            text="取消全选", 
            width=80,
            command=self.deselect_all_messages
        )
        self.deselect_all_btn.pack(side="left", padx=5)
        
        # 删除选中按钮
        self.delete_selected_btn = ctk.CTkButton(
            button_frame, 
            text="删除选中", 
            width=80,
            command=self.delete_selected_messages,
            fg_color="#dc3545", 
            hover_color="#c82333"
        )
        self.delete_selected_btn.pack(side="left", padx=5)
        
        # 选中数量标签
        self.selection_count_label = ctk.CTkLabel(button_frame, text="已选中: 0")
        self.selection_count_label.pack(side="right", padx=10)
    
    def create_quick_actions(self, parent):
        """创建快捷操作按钮"""
        try:
            quick_frame = ctk.CTkFrame(parent, fg_color="透明" if hasattr(ctk, 'TRANSPARENT') else "transparent")
            quick_frame.pack(fill="x", padx=10, pady=(0, 4))

            # 文件交互按钮（直接放在一级菜单）
            file_interaction_btn = ctk.CTkButton(quick_frame, text="📁 文件交互", width=110, height=28,
                                            command=lambda: self.on_select_read_mode("file_interaction"))
            file_interaction_btn.pack(side="left", padx=4, pady=(0, 0))
            
            # 环境搭建指导按钮（在文件交互按钮右侧）
            self.env_setup_btn = ctk.CTkButton(quick_frame, text="🔧 环境搭建指导", width=130, height=28,
                                             command=self.on_env_setup_guide, state="disabled")
            self.env_setup_btn.pack(side="left", padx=4, pady=(0, 0))

            # 漏洞审计按钮（在环境搭建指导按钮右侧）
            self.vuln_audit_btn = ctk.CTkButton(
                quick_frame,
                text="🛡️漏洞审计",
                width=110,
                height=28,
                command=self.on_vulnerability_audit,
                state="disabled"
            )
            self.vuln_audit_btn.pack(side="left", padx=4, pady=(0, 0))

            # 重启软件按钮（在最右侧）
            self.restart_btn = ctk.CTkButton(quick_frame, text="🔄 重启软件", width=110, height=28,
                                             command=self.on_restart_application)
            self.restart_btn.pack(side="right", padx=4, pady=(0, 0))

            # 在按钮右侧预置一个指示三角（默认不显示，展开时再pack）
            try:
                self.vuln_audit_indicator = ctk.CTkLabel(
                    quick_frame,
                    text="▶",
                    font=ctk.CTkFont(size=14, weight="bold")
                )
            except Exception:
                self.vuln_audit_indicator = None
            # 保存快捷操作容器引用用于定位
            self.quick_actions_frame = quick_frame
            # 初始化按钮状态
            try:
                self.update_vulnerability_audit_button_state()
            except Exception:
                pass
            
            # 存储当前选择的文件标签（具体容器在底部标签栏中创建）
            self.current_file_tags = []
            
        except Exception as e:
            try:
                self.show_toast(f"创建快捷操作按钮失败: {e}", "error")
            except Exception:
                pass
        
    def create_bottom_tag_bar(self, parent):
        """创建底部可折叠的文件标签栏"""
        try:
            self.bottom_tag_bar_frame = ctk.CTkFrame(parent)
            # 位于聊天区域底部、输入框之上
            self.bottom_tag_bar_frame.pack(fill="x", padx=10, pady=(0, 6))
            
            header = ctk.CTkFrame(self.bottom_tag_bar_frame, fg_color="transparent")
            header.pack(fill="x")
            
            self.bottom_tag_bar_collapsed = False
            
            self.tag_bar_toggle_btn = ctk.CTkButton(
                header,
                text="文件标签栏 ▾",
                width=110,
                command=self.toggle_tag_bar
            )
            self.tag_bar_toggle_btn.pack(side="left")
            
            self.tag_bar_status_label = ctk.CTkLabel(
                header,
                text="",
                font=ctk.CTkFont(size=11),
                text_color=("#666666", "#cccccc")
            )
            self.tag_bar_status_label.pack(side="left", padx=8)
            
            # 标签容器（底部统一创建）
            self.file_tags_frame = ctk.CTkFrame(self.bottom_tag_bar_frame, fg_color="transparent")
            self.file_tags_frame.pack(fill="x", padx=0, pady=(4, 0))
            self.file_tags_frame.pack_forget()
        except Exception as e:
            try:
                self.show_toast(f"创建标签栏失败: {e}", "error")
            except Exception:
                pass
    
    def toggle_tag_bar(self):
        """切换标签栏展开/收起"""
        try:
            if getattr(self, 'bottom_tag_bar_collapsed', False):
                # 展开
                self.file_tags_frame.pack(fill="x", padx=0, pady=(4, 0))
                self.tag_bar_toggle_btn.configure(text="文件标签栏 ▾")
                self.bottom_tag_bar_collapsed = False
            else:
                # 收起
                self.file_tags_frame.pack_forget()
                self.tag_bar_toggle_btn.configure(text="文件标签栏 ▸")
                self.bottom_tag_bar_collapsed = True
        except Exception:
            pass
    
    def create_input_area(self, parent):
        """创建输入区域 - 与原始聊天模块保持一致"""
        input_frame = ctk.CTkFrame(parent)
        input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # 输入文本框
        self.input_text = ctk.CTkTextbox(input_frame, height=80, wrap="word")
        self.input_text.pack(fill="x", padx=10, pady=(10, 5))
        
        # 按钮区域
        button_area = ctk.CTkFrame(input_frame)
        button_area.pack(fill="x", padx=10, pady=(0, 10))
        
        # 清空按钮（在左），发送按钮（在右），终止按钮（最右侧显示时）
        clear_button = ctk.CTkButton(button_area, text="清空", command=self.clear_input)
        # 发送按钮
        self.send_button = ctk.CTkButton(
            button_area, 
            text="发送", 
            command=self.send_message, 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.send_button.pack(side="right", padx=(10, 0))
        clear_button.pack(side="right")
        
        # 终止按钮
        self.stop_button = ctk.CTkButton(
            button_area, 
            text="终止", 
            command=self.stop_ai_response,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.stop_button.pack(side="right", padx=(5, 0))
        self.stop_button.pack_forget()  # 初始隐藏
        
        # 键盘绑定：回车发送，Ctrl+回车换行
        self.input_text.bind("<Return>", self._on_enter_send)
        self.input_text.bind("<Control-Return>", self._on_ctrl_enter_newline)
        
    def _on_enter_send(self, event=None):
        """按下回车发送消息"""
        try:
            # 在Text控件中，<Return> 默认会插入换行，这里阻止默认行为并发送消息
            self.send_message()
        finally:
            return "break"
    
    def _on_ctrl_enter_newline(self, event=None):
        """按下 Ctrl+Enter 插入换行"""
        try:
            self.input_text.insert("insert", "\n")
        finally:
            return "break"
    
    def show_thinking_animation(self):
        """显示AI思考动画"""
        try:
            if ThinkingAnimation is not None:
                # 清理可能残留的旧实例
                if self.thinking_animation:
                    try:
                        self.thinking_animation.hide()
                    except Exception:
                        pass
                    self.thinking_animation = None
                # 启用新版动画
                self.thinking_animation = ThinkingAnimation(
                    self.chat_display,
                    on_stop=self.stop_ai_response
                )
                self.thinking_animation.show()
                return
        except Exception:
            pass
        # 回退到旧的实现
        thinking_id = str(uuid.uuid4())
        self.thinking_message_id = thinking_id
        self.add_message_to_display("assistant", "正在思考...", thinking_id)
        self.start_thinking_animation()
    
    def start_thinking_animation(self):
        """开始思考动画（旧版本回退）"""
        def animate():
            if self.thinking_message_id and not self.stop_ai_request:
                # 更新思考消息
                dots = "." * ((self.waiting_dots % 3) + 1)
                thinking_text = f"正在思考{dots}"
                
                # 找到并更新思考消息
                for msg_info in self.message_components:
                    if msg_info['message_id'] == self.thinking_message_id:
                        # 找到消息内容标签并更新
                        for child in msg_info['frame'].winfo_children():
                            if isinstance(child, ctk.CTkLabel) and "正在思考" in child.cget("text"):
                                child.configure(text=thinking_text)
                                break
                        break
                
                self.waiting_dots += 1
                # 继续动画
                self.thinking_animation_job = self.after(500, animate)
        
        animate()
    
    def stop_thinking_animation(self):
        """停止思考动画"""
        # 停止新的动画组件
        if self.thinking_animation:
            self.thinking_animation.hide()
            self.thinking_animation = None
        
        # 停止旧的动画
        if self.thinking_animation_job:
            self.after_cancel(self.thinking_animation_job)
            self.thinking_animation_job = None
        
        # 删除思考消息
        if self.thinking_message_id:
            self.delete_single_message(self.thinking_message_id, silent=True)
            self.thinking_message_id = None
        
        self.waiting_dots = 0
    
    def stop_ai_response(self):
        """停止AI响应"""
        self.stop_ai_request = True
        self.stop_thinking_animation()
        self.show_toast("已终止AI响应", "warning")
        self.reset_ui_state()
    
    def on_ai_stopped(self):
        """AI被停止时的处理"""
        self.stop_thinking_animation()
        self.add_message_to_display("assistant", "[响应已被用户终止]")
        self.reset_ui_state()
    
    def reset_ui_state(self):
        """重置UI状态"""
        # 隐藏终止按钮，显示发送按钮
        self.stop_button.pack_forget()
        self.send_button.pack(side="right", padx=(10, 0))
        
        # 重置标志
        self.stop_ai_request = False
        self.ai_thread = None
    
    def add_message_to_display(self, role: str, content: str, message_id: str = None):
        """添加消息到显示区域 - 与原始聊天模块完全一致"""
        # 如果没有提供message_id，生成一个新的ID
        if message_id is None:
            message_id = str(uuid.uuid4())
        
        message_frame = ctk.CTkFrame(self.chat_display)
        message_frame.pack(fill="x", pady=5, padx=10)
        
        # 顶部框架：包含选择框、角色标签和操作按钮
        top_frame = ctk.CTkFrame(message_frame, fg_color="transparent")
        top_frame.pack(fill="x", padx=15, pady=(10, 5))
        
        # 选择框（仅在选择模式下显示）
        checkbox_var = tk.BooleanVar()
        checkbox = ctk.CTkCheckBox(
            top_frame, 
            text="", 
            variable=checkbox_var, 
            width=20,
            command=lambda: self.toggle_message_selection(message_id, checkbox_var.get())
        )
        if self.selection_mode:
            checkbox.pack(side="left", padx=(0, 10))
        
        # 角色标签
        role_text = "用户" if role == "user" else "AI助手"
        if role == "user":
            role_color = "#1f538d"  # 蓝色
        else:
            role_color = "#28a745"  # 绿色
        
        role_label = ctk.CTkLabel(
            top_frame, 
            text=f"{role_text}:", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=role_color
        )
        role_label.pack(side="left")
        
        # 操作按钮框架
        action_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        action_frame.pack(side="right")
        
        # 复制按钮
        copy_btn = ctk.CTkButton(
            action_frame, 
            text="📋", 
            width=30, 
            height=25,
            command=lambda: self.copy_message(content)
        )
        copy_btn.pack(side="right", padx=2)
        
        # 删除按钮
        delete_btn = ctk.CTkButton(
            action_frame, 
            text="🗑", 
            width=30, 
            height=25,
            command=lambda: self.delete_single_message(message_id),
            fg_color="#dc3545", 
            hover_color="#c82333"
        )
        delete_btn.pack(side="right", padx=2)
        
        # 消息内容 - 使用Text组件支持Markdown格式和选择复制
        font_size = self.settings_manager.get_font_size() if self.settings_manager else 12
        content_text = tk.Text(
            message_frame,
            wrap=tk.WORD,
            height=3,  # 初始高度，稍大，后续根据内容自动调整
            font=("Consolas", font_size),
            bg="#212121" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0",
            fg="#ffffff" if ctk.get_appearance_mode() == "Dark" else "#000000",
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=5,
            selectbackground="#0078d4",
            selectforeground="white",
            state="normal"
        )
        
        # 插入内容并应用Markdown格式
        content_text.insert("1.0", content)
        self._apply_markdown_formatting(content_text, content)
        
        # 设置为只读，但允许选择和复制
        # 使用normal状态允许选择，但绑定事件防止编辑
        content_text.configure(state="normal")
        
        # 绑定键盘事件，防止编辑但允许复制
        def prevent_edit(event):
            # 允许复制相关的快捷键
            if event.state & 0x4:  # Ctrl键被按下
                if event.keysym in ['c', 'C', 'a', 'A']:  # Ctrl+C 和 Ctrl+A
                    return None
            # 阻止其他所有键盘输入
            return "break"
        
        content_text.bind("<Key>", prevent_edit)
        content_text.bind("<Button-1>", lambda e: content_text.focus_set())  # 允许点击获得焦点
        
        # 添加右键菜单
        def create_context_menu():
            context_menu = tk.Menu(content_text, tearoff=0)
            context_menu.add_command(label="复制", command=lambda: self.copy_selected_text(content_text))
            context_menu.add_command(label="全选", command=lambda: content_text.tag_add(tk.SEL, "1.0", tk.END))
            context_menu.add_separator()
            context_menu.add_command(label="复制全部内容", command=lambda: self.copy_message(content))
            return context_menu
        
        def show_context_menu(event):
            try:
                context_menu = create_context_menu()
                context_menu.tk_popup(event.x_root, event.y_root)
            except Exception:
                pass
            finally:
                context_menu.grab_release()
        
        content_text.bind("<Button-3>", show_context_menu)  # 右键菜单
        
        # 根据内容调整高度 - 完全自适应显示所有行
        content_text.update_idletasks()
        line_count = int(content_text.index('end-1c').split('.')[0])
        # 有多少行就显示多少行，完全自适应
        content_text.configure(height=line_count)
        
        content_text.pack(anchor="w", padx=15, pady=(0, 10), fill="x")
        
        # 存储消息组件信息，用于选择模式切换与后续更新
        message_info = {
            'frame': message_frame,
            'checkbox': checkbox,
            'checkbox_var': checkbox_var,
            'message_id': message_id,
            'role': role,
            'content': content,
            'content_text': content_text,
        }
        
        self.message_components.append(message_info)
        
        # 存储消息数据
        message_data = {
            'id': message_id,
            'role': role,
            'content': content,
            'timestamp': time.strftime("%H:%M:%S")
        }
        self.messages.append(message_data)
        
        return message_id
    
    def add_system_message(self, content: str):
        """添加系统/助手消息到聊天显示"""
        try:
            self.add_message_to_display("assistant", content)
        except Exception as e:
            self.show_toast(f"添加系统消息失败: {e}", "error")
    
    def add_message(self, message: dict):
        """兼容旧接口：接受字典并添加到显示"""
        role = message.get("role", "assistant")
        content = message.get("content", "")
        self.add_message_to_display(role, content)
    
    def toggle_selection_mode(self):
        """切换选择模式 - 与原始聊天模块完全一致"""
        self.selection_mode = not self.selection_mode
        
        if self.selection_mode:
            self.selection_toggle_btn.configure(text="退出选择")
            self.batch_toolbar.pack(fill="x", padx=10, pady=(0, 10))
            # 显示所有选择框
            for msg_info in self.message_components:
                msg_info['checkbox'].pack(side="left", padx=(0, 10), before=msg_info['checkbox'].master.winfo_children()[1])
        else:
            self.selection_toggle_btn.configure(text="选择消息")
            self.batch_toolbar.pack_forget()
            # 隐藏所有选择框并清空选择
            for msg_info in self.message_components:
                msg_info['checkbox'].pack_forget()
                msg_info['checkbox_var'].set(False)
            self.selected_messages.clear()
            self.update_selection_count()
    
    def toggle_message_selection(self, message_id: str, selected: bool):
        """切换消息选择状态"""
        if selected:
            self.selected_messages.add(message_id)
        else:
            self.selected_messages.discard(message_id)
        self.update_selection_count()
    
    def update_selection_count(self):
        """更新选择数量显示"""
        count = len(self.selected_messages)
        self.selection_count_label.configure(text=f"已选中: {count}")
    
    def select_all_messages(self):
        """全选消息"""
        for msg_info in self.message_components:
            msg_info['checkbox_var'].set(True)
            self.selected_messages.add(msg_info['message_id'])
        self.update_selection_count()
    
    def deselect_all_messages(self):
        """取消全选"""
        for msg_info in self.message_components:
            msg_info['checkbox_var'].set(False)
        self.selected_messages.clear()
        self.update_selection_count()
    
    def copy_message(self, content: str):
        """复制消息内容到剪贴板"""
        try:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.show_toast("消息已复制到剪贴板", "success")
        except Exception as e:
            self.show_toast(f"复制失败: {str(e)}", "error")
    
    def copy_selected_text(self, text_widget: tk.Text):
        """复制Text组件中选中的文本到剪贴板"""
        try:
            # 检查是否有选中的文本
            if text_widget.tag_ranges(tk.SEL):
                selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                self.show_toast("选中文本已复制到剪贴板", "success")
            else:
                self.show_toast("请先选中要复制的文本", "warning")
        except Exception as e:
            self.show_toast(f"复制失败: {str(e)}", "error")
    
    def _apply_markdown_formatting(self, text_widget: tk.Text, content: str):
        """为Text组件应用Markdown格式化"""
        import re
        
        # 获取动态字体大小
        base_font_size = self.settings_manager.get_font_size()
        
        # 配置标签样式 - 不同级别的标题使用不同字体大小
        text_widget.tag_configure("heading1", font=("Consolas", base_font_size + 6, "bold"), foreground="#0078d4", spacing1=10, spacing3=5)
        text_widget.tag_configure("heading2", font=("Consolas", base_font_size + 4, "bold"), foreground="#0078d4", spacing1=8, spacing3=4)
        text_widget.tag_configure("heading3", font=("Consolas", base_font_size + 2, "bold"), foreground="#0078d4", spacing1=6, spacing3=3)
        text_widget.tag_configure("heading4", font=("Consolas", base_font_size + 1, "bold"), foreground="#0078d4", spacing1=4, spacing3=2)
        text_widget.tag_configure("heading5", font=("Consolas", base_font_size, "bold"), foreground="#0078d4", spacing1=2, spacing3=1)
        text_widget.tag_configure("heading6", font=("Consolas", base_font_size, "bold"), foreground="#6c757d", spacing1=2, spacing3=1)
        
        text_widget.tag_configure("code_block", font=("Consolas", max(8, base_font_size - 1)), background="#2d2d2d", foreground="#f8f8f2", lmargin1=10, lmargin2=10, spacing1=2, spacing3=2)
        text_widget.tag_configure("inline_code", font=("Consolas", max(8, base_font_size - 1)), background="#404040", foreground="#f8f8f2")
        text_widget.tag_configure("bold", font=("Consolas", base_font_size, "bold"))
        text_widget.tag_configure("italic", font=("Consolas", base_font_size, "italic"))
        text_widget.tag_configure("strikethrough", font=("Consolas", base_font_size), overstrike=True)
        text_widget.tag_configure("link", font=("Consolas", base_font_size, "underline"), foreground="#0078d4")
        
        # 列表样式 - 支持嵌套
        text_widget.tag_configure("list_item", font=("Consolas", base_font_size), lmargin1=20, lmargin2=30)
        text_widget.tag_configure("list_item_2", font=("Consolas", base_font_size), lmargin1=40, lmargin2=50)
        text_widget.tag_configure("list_item_3", font=("Consolas", base_font_size), lmargin1=60, lmargin2=70)
        text_widget.tag_configure("list_item_4", font=("Consolas", base_font_size), lmargin1=80, lmargin2=90)
        
        # 引用块样式
        text_widget.tag_configure("blockquote", font=("Consolas", base_font_size, "italic"), background="#f8f9fa", foreground="#6c757d", lmargin1=20, lmargin2=20, spacing1=2, spacing3=2)
        
        # 表格样式
        text_widget.tag_configure("table_header", font=("Consolas", base_font_size, "bold"), background="#e9ecef", foreground="#495057")
        text_widget.tag_configure("table_cell", font=("Consolas", base_font_size), background="#f8f9fa")
        
        # 分隔线样式
        text_widget.tag_configure("hr", font=("Consolas", base_font_size), foreground="#dee2e6", spacing1=10, spacing3=10)
        
        # 应用格式化
        lines = content.split('\n')
        in_code_block = False
        code_block_start = None
        
        for line_num, line in enumerate(lines, 1):
            line_start = f"{line_num}.0"
            line_end = f"{line_num}.{len(line)}"
            
            # 处理代码块 - 正确处理多行代码块
            if line.strip().startswith('```'):
                if not in_code_block:
                    # 代码块开始
                    in_code_block = True
                    code_block_start = line_num
                    text_widget.tag_add("code_block", line_start, line_end)
                else:
                    # 代码块结束
                    in_code_block = False
                    text_widget.tag_add("code_block", line_start, line_end)
                    # 为整个代码块添加格式
                    if code_block_start:
                        block_start = f"{code_block_start}.0"
                        block_end = f"{line_num}.{len(line)}"
                        text_widget.tag_add("code_block", block_start, block_end)
                continue
            
            # 如果在代码块内，整行应用代码块格式
            if in_code_block:
                text_widget.tag_add("code_block", line_start, line_end)
                continue
            
            # 标题格式化 - 支持不同级别
            heading_match = re.match(r'^(#{1,6})\s+', line)
            if heading_match:
                level = len(heading_match.group(1))
                tag_name = f"heading{level}"
                text_widget.tag_add(tag_name, line_start, line_end)
                continue
            
            # 分隔线
            if re.match(r'^[\s]*[-*_]{3,}[\s]*$', line):
                text_widget.tag_add("hr", line_start, line_end)
                continue
            
            # 引用块
            if re.match(r'^[\s]*>\s*', line):
                text_widget.tag_add("blockquote", line_start, line_end)
                continue
            
            # 列表项格式化 - 支持嵌套
            list_match = re.match(r'^(\s*)([-*+]|\d+\.)\s+', line)
            if list_match:
                indent_level = len(list_match.group(1)) // 2  # 每2个空格为一个缩进级别
                if indent_level == 0:
                    tag_name = "list_item"
                elif indent_level == 1:
                    tag_name = "list_item_2"
                elif indent_level == 2:
                    tag_name = "list_item_3"
                else:
                    tag_name = "list_item_4"
                text_widget.tag_add(tag_name, line_start, line_end)
            
            # 表格行检测
            if '|' in line and line.count('|') >= 2:
                if re.match(r'^[\s]*\|.*\|[\s]*$', line):
                    # 检查是否是表头分隔行
                    if re.match(r'^[\s]*\|[\s]*:?-+:?[\s]*(\|[\s]*:?-+:?[\s]*)*\|[\s]*$', line):
                        text_widget.tag_add("table_header", line_start, line_end)
                    else:
                        # 检查上一行是否是表头
                        if line_num > 1:
                            prev_line = lines[line_num - 2] if line_num - 2 < len(lines) else ""
                            if '|' in prev_line and prev_line.count('|') >= 2:
                                text_widget.tag_add("table_header", f"{line_num-1}.0", f"{line_num-1}.{len(prev_line)}")
                        text_widget.tag_add("table_cell", line_start, line_end)
            
            # 行内格式化（只在非代码块行中应用）
            
            # 行内代码格式化 - 避免与代码块冲突
            for match in re.finditer(r'(?<!`)`([^`\n]+)`(?!`)', line):
                start_col = match.start()
                end_col = match.end()
                tag_start = f"{line_num}.{start_col}"
                tag_end = f"{line_num}.{end_col}"
                text_widget.tag_add("inline_code", tag_start, tag_end)
            
            # 粗体格式化
            for match in re.finditer(r'\*\*([^*\n]+)\*\*', line):
                start_col = match.start()
                end_col = match.end()
                tag_start = f"{line_num}.{start_col}"
                tag_end = f"{line_num}.{end_col}"
                text_widget.tag_add("bold", tag_start, tag_end)
            
            # 斜体格式化 - 避免与粗体冲突
            for match in re.finditer(r'(?<!\*)\*([^*\n]+)\*(?!\*)', line):
                start_col = match.start()
                end_col = match.end()
                tag_start = f"{line_num}.{start_col}"
                tag_end = f"{line_num}.{end_col}"
                text_widget.tag_add("italic", tag_start, tag_end)
            
            # 删除线格式化
            for match in re.finditer(r'~~([^~\n]+)~~', line):
                start_col = match.start()
                end_col = match.end()
                tag_start = f"{line_num}.{start_col}"
                tag_end = f"{line_num}.{end_col}"
                text_widget.tag_add("strikethrough", tag_start, tag_end)
            
            # 链接格式化
            for match in re.finditer(r'\[([^\]]+)\]\([^)]+\)', line):
                start_col = match.start()
                end_col = match.end()
                tag_start = f"{line_num}.{start_col}"
                tag_end = f"{line_num}.{end_col}"
                text_widget.tag_add("link", tag_start, tag_end)
    
    def delete_single_message(self, message_id: str, silent: bool = False):
        """删除单条消息"""
        try:
            # 从消息列表中删除
            self.messages = [msg for msg in self.messages if msg['id'] != message_id]
            
            # 从组件列表中删除并销毁UI组件
            for i, msg_info in enumerate(self.message_components):
                if msg_info['message_id'] == message_id:
                    msg_info['frame'].destroy()
                    self.message_components.pop(i)
                    break
            
            # 从选中列表中移除
            self.selected_messages.discard(message_id)
            self.update_selection_count()
            
            if not silent:
                self.show_toast("消息已删除", "success")
        except Exception as e:
            self.show_toast(f"删除失败: {str(e)}", "error")
    
    def delete_selected_messages(self):
        """删除选中的消息"""
        if not self.selected_messages:
            self.show_toast("请先选择要删除的消息", "warning")
            return
        
        try:
            # 删除选中的消息
            for message_id in list(self.selected_messages):
                self.delete_single_message(message_id)
            
            self.show_toast("已删除选中消息", "success")
            self.selected_messages.clear()
            self.update_selection_count()
        except Exception as e:
            self.show_toast(f"批量删除失败: {str(e)}", "error")
    
    def show_toast(self, message: str, toast_type: str = "info", duration: int = 3000):
        """显示Toast通知 - 与原始聊天模块一致"""
        # 如果有当前通知，先关闭它
        if self.current_toast:
            try:
                if self.current_toast.winfo_exists():
                    self.current_toast.destroy()
            except Exception:
                pass
            self.current_toast = None
        
        # 创建Toast窗口
        toast = ctk.CTkToplevel(self)
        toast.withdraw()  # 先隐藏
        toast.overrideredirect(True)  # 无边框
        toast.attributes('-topmost', True)  # 置顶
        # 同步应用图标
        try:
            from pathlib import Path
            icon_path = Path(__file__).parent.parent / 'assets' / 'icon.ico'
            if icon_path.exists():
                toast.iconbitmap(default=str(icon_path))
            else:
                png_path = Path(__file__).parent.parent / 'assets' / 'icon.png'
                if png_path.exists():
                    _img = tk.PhotoImage(file=str(png_path))
                    toast.iconphoto(False, _img)
                    toast._icon_img_ref = _img
        except Exception:
            pass
        
        # 设置Toast样式
        if toast_type == "success":
            bg_color = "#4CAF50"
            text_color = "white"
            icon = "✓"
        elif toast_type == "error":
            bg_color = "#F44336"
            text_color = "white"
            icon = "✗"
        elif toast_type == "warning":
            bg_color = "#FF9800"
            text_color = "white"
            icon = "⚠"
        else:  # info
            bg_color = "#2196F3"
            text_color = "white"
            icon = "ℹ"
        
        # 创建Toast内容
        toast_frame = ctk.CTkFrame(toast, fg_color=bg_color, corner_radius=8)
        toast_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # 图标和消息
        content_frame = ctk.CTkFrame(toast_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        icon_label = ctk.CTkLabel(
            content_frame, 
            text=icon, 
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=text_color
        )
        icon_label.pack(side="left", padx=(0, 10))
        
        message_label = ctk.CTkLabel(
            content_frame, 
            text=message, 
            font=ctk.CTkFont(size=12),
            text_color=text_color, 
            wraplength=300
        )
        message_label.pack(side="left", fill="x", expand=True)
        
        # 完成显示并定位到父窗口右下角，支持自动隐藏
        try:
            toast.update_idletasks()
            req_w = toast.winfo_reqwidth()
            req_h = toast.winfo_reqheight()
            # 优先使用锚点控件（通过 set_toast_anchor 设定）
            anchor = getattr(self, "toast_anchor_widget", None)
            if anchor is not None and hasattr(anchor, "winfo_rootx"):
                base_x = anchor.winfo_rootx()
                base_y = anchor.winfo_rooty()
                base_w = anchor.winfo_width()
                base_h = anchor.winfo_height()
            else:
                base_x = self.winfo_rootx()
                base_y = self.winfo_rooty()
                base_w = self.winfo_width()
                base_h = self.winfo_height()
            x = max(base_x + base_w - req_w - 20, 0)
            y = max(base_y + base_h - req_h - 20, 0)
            toast.geometry(f"{req_w}x{req_h}+{x}+{y}")
            toast.deiconify()
            self.current_toast = toast
            # 自动隐藏
            try:
                toast.after(duration, lambda: (toast.destroy() if toast.winfo_exists() else None))
            except Exception:
                pass
            # 点击关闭
            for widget in (toast, toast_frame, content_frame, icon_label, message_label):
                try:
                    widget.bind("<Button-1>", lambda e: (toast.destroy() if toast.winfo_exists() else None))
                except Exception:
                    pass
        except Exception:
            # 最小化失败不影响程序
            pass
        
    def add_file_interaction_tag(self, files):
        """添加文件交互标签（支持累加多个文件和文件夹递归处理）"""
        try:
            # 处理文件和文件夹，收集所有实际文件
            processed_files = []
            display_items = []  # 用于显示的项目（文件夹显示文件夹名，文件显示文件名）
            
            for item in files:
                if os.path.isdir(item):
                    # 如果是文件夹，递归收集所有支持的文件
                    folder_files = self.collect_files_recursively(item)
                    if folder_files:
                        processed_files.extend(folder_files)
                        # 显示项目使用文件夹名
                        display_items.append({
                            'type': 'folder',
                            'path': item,
                            'display_name': os.path.basename(item),
                            'file_count': len(folder_files)
                        })
                elif os.path.isfile(item) and self.is_supported_file(item):
                    # 如果是支持的文件，直接添加
                    processed_files.append(item)
                    display_items.append({
                        'type': 'file',
                        'path': item,
                        'display_name': os.path.basename(item),
                        'file_count': 1
                    })
            
            if not processed_files:
                self.show_toast("没有找到支持的文件", "warning")
                return
            
            # 检查文件数量，给出警告
            total_file_count = len(processed_files)
            if total_file_count > 500:
                warning_msg = f"选择了 {total_file_count} 个文件，数量很大，请求可能需要较长时间"
                self.show_toast(warning_msg, "warning", 6000)
                print(f"警告: {warning_msg}")
            elif total_file_count > 100:
                info_msg = f"选择了 {total_file_count} 个文件，正在准备发送到云端模型"
                self.show_toast(info_msg, "info", 4000)
                print(f"提示: {info_msg}")
            elif total_file_count > 50:
                info_msg = f"选择了 {total_file_count} 个文件"
                self.show_toast(info_msg, "info", 3000)
                print(f"提示: {info_msg}")
            
            # 如果已经有文件交互状态，则累加新文件
            if self.file_interaction_active and self.selected_files_for_interaction:
                # 合并文件列表，去重
                existing_files = set(self.selected_files_for_interaction)
                new_files = [f for f in processed_files if f not in existing_files]
                
                if new_files:
                    # 添加新文件到现有列表
                    self.selected_files_for_interaction.extend(new_files)
                    
                    # 更新显示项目列表
                    if not hasattr(self, 'selected_display_items'):
                        self.selected_display_items = []
                    self.selected_display_items.extend(display_items)
                    
                    # 递增计数器
                    self.file_interaction_counter += 1
                    
                    # 更新底部标签栏（不在聊天区域显示）
                    self.add_file_tags_with_display_items(self.selected_display_items)
                    
                    total_files = len(self.selected_files_for_interaction)
                    self.show_toast(f"已添加 {len(new_files)} 个新文件，当前共 {total_files} 个文件", "success")
                else:
                    self.show_toast("选择的文件已存在于当前文件交互中", "info")
            else:
                # 首次创建文件交互标签
                # 递增计数器
                self.file_interaction_counter += 1
                
                # 只在底部标签栏添加文件标签（不在聊天区域显示）
                self.add_file_tags_with_display_items(display_items)
                
                # 设置文件交互状态
                self.file_interaction_active = True
                self.selected_files_for_interaction = processed_files
                self.selected_display_items = display_items
                
                total_files = len(processed_files)
                self.show_toast(f"已选择 {total_files} 个文件进行交互", "success")
            
            # 更新环境搭建按钮状态
            self.update_env_setup_button_state()
            # 更新漏洞审计按钮状态
            try:
                self.update_vulnerability_audit_button_state()
            except Exception:
                pass
            
        except Exception as e:
            print(f"添加文件交互标签失败: {e}")
            self.show_toast(f"添加文件交互标签失败: {e}", "error")
    
    def remove_file_interaction_tag(self):
        """移除文件交互标签"""
        try:
            # 清除底部标签栏的文件标签
            self.clear_file_tags()
            
            # 同步清除项目文件夹标签
            try:
                self.clear_project_folder_tags()
            except Exception:
                pass
            
            # 清除文件交互状态
            self.file_interaction_active = False
            self.selected_files_for_interaction = []
            if hasattr(self, 'selected_display_items'):
                self.selected_display_items = []
            
            # 更新环境搭建按钮状态
            self.update_env_setup_button_state()
            # 更新漏洞审计按钮状态
            try:
                self.update_vulnerability_audit_button_state()
            except Exception:
                pass
            
        except Exception as e:
            print(f"移除文件交互标签失败: {e}")
    

    def add_project_folder_tag(self, folder_name, folder_path):
        """添加项目文件夹标签"""
        try:
            # 确保底部标签栏容器已创建
            if not hasattr(self, "bottom_tag_bar_frame"):
                self.bottom_tag_bar_frame = ctk.CTkFrame(self)
                self.bottom_tag_bar_frame.pack(fill="x", padx=10, pady=(0, 6))
            
            # 确保文件标签容器已创建
            if not hasattr(self, "file_tags_frame"):
                self.file_tags_frame = ctk.CTkFrame(self.bottom_tag_bar_frame, fg_color="transparent")
                self.file_tags_frame.pack(side="left", fill="x", expand=True, padx=(5, 0))
            
            # 创建标签容器 - 直接使用file_tags_frame，与单文件标签放在一起
            tag_frame = ctk.CTkFrame(self.file_tags_frame, height=24)
            tag_frame.pack(side="left", padx=(0, 4), pady=2)
            
            # 创建标签文本
            tag_label = ctk.CTkLabel(tag_frame, text=f"📁 {folder_name}", font=("Arial", 10))
            tag_label.pack(side="left", padx=(4, 0), pady=2)
            
            # 创建删除按钮
            close_btn = ctk.CTkButton(tag_frame, text="×", width=16, height=16, 
                                     command=lambda: self.remove_project_folder_tag(tag_frame, folder_path),
                                     font=("Arial", 10), fg_color="transparent", hover_color="#ff6b6b")
            close_btn.pack(side="left", padx=(2, 4), pady=2)
            
            # 存储标签信息
            if not hasattr(self, "project_folder_tags"):
                self.project_folder_tags = {}
            self.project_folder_tags[folder_path] = tag_frame
            
            # 设置文件交互状态
            self.file_interaction_active = True
            if not hasattr(self, 'selected_files_for_interaction'):
                self.selected_files_for_interaction = []
            if folder_path not in self.selected_files_for_interaction:
                self.selected_files_for_interaction.append(folder_path)
            
            # 更新环境搭建按钮状态
            self.update_env_setup_button_state()
            # 更新漏洞审计按钮状态
            try:
                self.update_vulnerability_audit_button_state()
            except Exception:
                pass
            
            return tag_frame
        except Exception as e:
            print(f"添加项目文件夹标签失败: {e}")
            return None
    
    def remove_project_folder_tag(self, tag_frame, folder_path):
        """移除项目文件夹标签"""
        try:
            # 销毁标签UI
            if tag_frame:
                tag_frame.destroy()
            
            # 从存储中移除
            if hasattr(self, "project_folder_tags") and folder_path in self.project_folder_tags:
                del self.project_folder_tags[folder_path]
            
            # 从选择的文件列表中移除该文件夹及其下所有文件
            if hasattr(self, 'selected_files_for_interaction') and self.selected_files_for_interaction:
                try:
                    self.selected_files_for_interaction = [
                        p for p in self.selected_files_for_interaction
                        if not (p == folder_path or os.path.commonpath([p, folder_path]) == folder_path)
                    ]
                except Exception:
                    # 兼容：路径前缀匹配移除
                    try:
                        self.selected_files_for_interaction = [
                            p for p in self.selected_files_for_interaction
                            if not (p == folder_path or p.startswith(folder_path + os.sep))
                        ]
                    except Exception:
                        pass
            
            # 如果没有标签了，隐藏标签容器
            if hasattr(self, "project_folder_tags") and not self.project_folder_tags:
                if hasattr(self, "project_tags_frame") and self.project_tags_frame:
                    self.project_tags_frame.pack_forget()
            
            # 若项目文件夹标签与文件标签均为空，关闭文件交互状态
            has_proj_tags = hasattr(self, "project_folder_tags") and bool(self.project_folder_tags)
            has_file_tags = hasattr(self, "current_file_tags") and bool(self.current_file_tags)
            if not has_proj_tags and not has_file_tags:
                self.file_interaction_active = False
                self.selected_files_for_interaction = []
                if hasattr(self, 'selected_display_items'):
                    self.selected_display_items = []
                try:
                    if hasattr(self, "file_tags_frame"):
                        self.file_tags_frame.pack_forget()
                    if hasattr(self, "tag_bar_status_label"):
                        self.tag_bar_status_label.configure(text="")
                except Exception:
                    pass
                try:
                    self.show_toast("文件交互模式已关闭", "info")
                except Exception:
                    pass

            # 同步更新按钮状态
            self.update_env_setup_button_state()
            try:
                self.update_vulnerability_audit_button_state()
            except Exception:
                pass
            
        except Exception as e:
            print(f"移除项目文件夹标签失败: {e}")
    
    def clear_project_folder_tags(self):
        """清除所有项目文件夹标签"""
        try:
            # 记录即将移除的项目文件夹路径
            removed_paths = []
            if hasattr(self, "project_folder_tags"):
                try:
                    removed_paths = list(self.project_folder_tags.keys())
                except Exception:
                    removed_paths = []
            
            # 销毁所有标签
            if hasattr(self, "project_folder_tags"):
                for tag_frame in self.project_folder_tags.values():
                    if tag_frame:
                        tag_frame.destroy()
                self.project_folder_tags = {}
            
            # 从选择的文件列表中移除对应的文件夹路径及其下所有文件
            if hasattr(self, 'selected_files_for_interaction') and self.selected_files_for_interaction:
                if not removed_paths:
                    # 回退：移除列表中所有目录项
                    removed_paths = [p for p in self.selected_files_for_interaction if os.path.isdir(p)]
                try:
                    def _is_removed(path):
                        try:
                            for rp in removed_paths:
                                # 移除目标目录本身或其子路径
                                if path == rp or os.path.commonpath([path, rp]) == rp:
                                    return True
                        except Exception:
                            for rp in removed_paths:
                                if path == rp or path.startswith(rp + os.sep):
                                    return True
                        return False
                    self.selected_files_for_interaction = [
                        p for p in self.selected_files_for_interaction if not _is_removed(p)
                    ]
                except Exception:
                    # 保守策略：若出错则清空选择列表，避免误发旧文件
                    self.selected_files_for_interaction = []
            
            # 隐藏标签容器
            if hasattr(self, "project_tags_frame") and self.project_tags_frame:
                self.project_tags_frame.pack_forget()
            
            # 若同时没有文件标签或选择列表为空，关闭文件交互状态
            has_file_tags = hasattr(self, "current_file_tags") and bool(self.current_file_tags)
            has_selected = hasattr(self, "selected_files_for_interaction") and bool(self.selected_files_for_interaction)
            if not has_file_tags and not has_selected:
                self.file_interaction_active = False
                # 同步清空选择列表，彻底避免旧文件泄漏
                self.selected_files_for_interaction = []
                if hasattr(self, 'selected_display_items'):
                    self.selected_display_items = []
                try:
                    if hasattr(self, "file_tags_frame"):
                        self.file_tags_frame.pack_forget()
                    if hasattr(self, "tag_bar_status_label"):
                        self.tag_bar_status_label.configure(text="")
                except Exception:
                    pass
            
            # 同步更新按钮状态
            self.update_env_setup_button_state()
            try:
                self.update_vulnerability_audit_button_state()
            except Exception:
                pass
        except Exception as e:
            print(f"清除项目文件夹标签失败: {e}")
            
    def is_supported_file(self, file_path):
        """检查文件是否为支持的类型"""
        # 支持的文件扩展名
        supported_extensions = {
            '.py', '.js', '.ts', '.html', '.css', '.scss', '.less',
            '.json', '.xml', '.yaml', '.yml', '.md', '.txt', '.rst',
            '.c', '.cpp', '.h', '.hpp', '.java', '.cs', '.php',
            '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
            '.sql', '.sh', '.bat', '.ps1', '.dockerfile', '.gitignore'
        }
        
        # 检查文件是否存在且是文件
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return False
            
        # 检查文件扩展名
        _, ext = os.path.splitext(file_path.lower())
        return ext in supported_extensions
    
    def collect_files_recursively(self, folder_path):
        """递归收集文件夹中的所有支持的文件"""
        collected_files = []
        
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return collected_files
        
        try:
            for root, dirs, files in os.walk(folder_path):
                # 跳过隐藏文件夹和常见的忽略文件夹
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                    '__pycache__', 'node_modules', '.git', '.svn', '.hg',
                    'venv', 'env', '.venv', '.env', 'build', 'dist',
                    'target', 'bin', 'obj', '.idea', '.vscode'
                }]
                
                for file in files:
                    # 跳过隐藏文件
                    if file.startswith('.'):
                        continue
                    
                    file_path = os.path.join(root, file)
                    if self.is_supported_file(file_path):
                        collected_files.append(file_path)
            
        except Exception as e:
            print(f"Error collecting files from {folder_path}: {e}")
        
        return collected_files
                
    def add_file_tags(self, file_paths):
        """在文件交互按钮右侧添加文件标签"""
        try:
            # 清除现有标签
            self.clear_file_tags()
            
            # 若标签容器未展开，则展开（仅在有标签时占位）
            if not self.file_tags_frame.winfo_ismapped():
                self.file_tags_frame.pack(side="left", fill="x", expand=True, padx=(6, 0))
            # 更新底部状态
            try:
                self.tag_bar_status_label.configure(text=f"已选择 {len(file_paths)} 个文件")
            except Exception:
                pass

            # 为每个文件创建标签（更紧凑）
            for file_path in file_paths:
                file_name = os.path.basename(file_path)
                
                # 创建标签容器（降低高度与边距）
                tag_frame = ctk.CTkFrame(self.file_tags_frame, height=24)
                tag_frame.pack(side="left", padx=(0, 4), pady=1)
                tag_frame.pack_propagate(False)
                
                # 文件名标签（更小字号与内边距）
                file_label = ctk.CTkLabel(
                    tag_frame, 
                    text=f"📄 {file_name}", 
                    font=ctk.CTkFont(size=10),
                    text_color=("gray10", "gray90")
                )
                file_label.pack(side="left", padx=(6, 3), pady=2)
                
                # 删除按钮（更小尺寸）
                delete_btn = ctk.CTkButton(
                    tag_frame,
                    text="×",
                    width=18,
                    height=18,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color=("gray70", "gray30"),
                    hover_color=("red", "darkred"),
                    command=lambda fp=file_path, tf=tag_frame: self.remove_file_tag(fp, tf)
                )
                delete_btn.pack(side="right", padx=(0, 3), pady=2)
                
                # 存储标签信息
                self.current_file_tags.append({
                    'file_path': file_path,
                    'tag_frame': tag_frame
                })
            
            # 更新文件交互状态
            self.file_interaction_active = True
            self.selected_files_for_interaction = file_paths.copy()
            
            # 更新环境搭建按钮状态
            self.update_env_setup_button_state()
            # 更新漏洞审计按钮状态
            try:
                self.update_vulnerability_audit_button_state()
            except Exception:
                pass
            
            # 显示提示
            if file_paths:
                self.show_toast(f"已选择 {len(file_paths)} 个文件进行交互", "success")
                
        except Exception as e:
            print(f"添加文件标签失败: {e}")
            self.show_toast(f"添加文件标签失败: {e}", "error")
    
    def add_file_tags_with_display_items(self, display_items):
        """根据显示项目添加文件标签（支持文件夹和文件的不同显示）"""
        try:
            # 清除现有标签
            self.clear_file_tags()
            
            # 若标签容器未展开，则展开（仅在有标签时占位）
            if not self.file_tags_frame.winfo_ismapped():
                self.file_tags_frame.pack(side="left", fill="x", expand=True, padx=(6, 0))
            
            # 计算总文件数
            total_files = sum(item['file_count'] for item in display_items)
            
            # 更新底部状态
            try:
                self.tag_bar_status_label.configure(text=f"已选择 {total_files} 个文件")
            except Exception:
                pass

            # 为每个显示项目创建标签
            for item in display_items:
                display_name = item['display_name']
                item_type = item['type']
                file_count = item['file_count']
                
                # 创建标签容器
                tag_frame = ctk.CTkFrame(self.file_tags_frame, height=24)
                tag_frame.pack(side="left", padx=(0, 4), pady=1)
                tag_frame.pack_propagate(False)
                
                # 根据类型选择图标和显示文本
                if item_type == 'folder':
                    icon = "📁"
                    display_text = f"{display_name} ({file_count})"
                else:
                    icon = "📄"
                    display_text = display_name
                
                # 文件/文件夹名标签
                file_label = ctk.CTkLabel(
                    tag_frame, 
                    text=f"{icon} {display_text}", 
                    font=ctk.CTkFont(size=10),
                    text_color=("gray10", "gray90")
                )
                file_label.pack(side="left", padx=(6, 3), pady=2)
                
                # 删除按钮
                delete_btn = ctk.CTkButton(
                    tag_frame,
                    text="×",
                    width=18,
                    height=18,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color=("gray70", "gray30"),
                    hover_color=("red", "darkred"),
                    command=lambda it=item, tf=tag_frame: self.remove_display_item_tag(it, tf)
                )
                delete_btn.pack(side="right", padx=(0, 3), pady=2)
                
                # 存储标签信息
                self.current_file_tags.append({
                    'display_item': item,
                    'tag_frame': tag_frame
                })
            
            # 更新文件交互状态
            self.file_interaction_active = True
            
            # 更新环境搭建按钮状态
            self.update_env_setup_button_state()
            # 更新-u "http://cvehunter.test/coms/branch_list.php" --batch --level 5 --risk 3 --dbs --time-sec=3按钮状态
            try:
                self.update_vulnerability_audit_button_state()
            except Exception:
                pass
            
            # 显示提示
            if display_items:
                self.show_toast(f"已选择 {total_files} 个文件进行交互", "success")
                
        except Exception as e:
            print(f"添加文件标签失败: {e}")
            self.show_toast(f"添加文件标签失败: {e}", "error")
    
    def remove_file_tag(self, file_path, tag_frame):
        """移除单个文件标签"""
        try:
            # 从标签列表中移除
            self.current_file_tags = [
                tag for tag in self.current_file_tags 
                if tag['file_path'] != file_path
            ]
            
            # 从选择的文件列表中移除
            if file_path in self.selected_files_for_interaction:
                self.selected_files_for_interaction.remove(file_path)
            
            # 销毁标签框架
            tag_frame.destroy()
            
            # 如果没有文件了，清除文件交互状态并收起标签容器
            if not self.current_file_tags:
                self.file_interaction_active = False
                self.selected_files_for_interaction = []
                # 收起标签区域以避免占位
                try:
                    self.file_tags_frame.pack_forget()
                    self.tag_bar_status_label.configure(text="")
                except Exception:
                    pass
                self.show_toast("文件交互模式已关闭", "info")
            else:
                try:
                    self.tag_bar_status_label.configure(text=f"已选择 {len(self.current_file_tags)} 个文件")
                except Exception:
                    pass
                self.show_toast(f"已移除文件: {os.path.basename(file_path)}", "info")
                
        except Exception as e:
            print(f"移除文件标签失败: {e}")
        # 同步更新漏洞审计按钮状态
        try:
            self.update_vulnerability_audit_button_state()
        except Exception:
            pass
    
    def remove_display_item_tag(self, display_item, tag_frame):
        """移除显示项目标签（文件夹或文件）"""
        try:
            # 从标签列表中移除
            self.current_file_tags = [
                tag for tag in self.current_file_tags 
                if tag.get('display_item') != display_item
            ]
            
            # 从显示项目列表中移除
            if hasattr(self, 'selected_display_items') and display_item in self.selected_display_items:
                self.selected_display_items.remove(display_item)
            
            # 从实际文件列表中移除相关文件
            if display_item['type'] == 'folder':
                # 如果是文件夹，需要移除该文件夹下的所有文件
                folder_files = self.collect_files_recursively(display_item['path'])
                for file_path in folder_files:
                    if file_path in self.selected_files_for_interaction:
                        self.selected_files_for_interaction.remove(file_path)
            else:
                # 如果是文件，直接移除
                if display_item['path'] in self.selected_files_for_interaction:
                    self.selected_files_for_interaction.remove(display_item['path'])
            
            # 销毁标签框架
            tag_frame.destroy()
            
            # 如果没有标签了，清除文件交互状态并收起标签容器
            if not self.current_file_tags:
                self.file_interaction_active = False
                self.selected_files_for_interaction = []
                if hasattr(self, 'selected_display_items'):
                    self.selected_display_items = []
                # 收起标签区域以避免占位
                try:
                    self.file_tags_frame.pack_forget()
                    self.tag_bar_status_label.configure(text="")
                except Exception:
                    pass
                self.show_toast("文件交互模式已关闭", "info")
            else:
                # 重新计算总文件数
                total_files = len(self.selected_files_for_interaction)
                try:
                    self.tag_bar_status_label.configure(text=f"已选择 {total_files} 个文件")
                except Exception:
                    pass
                
                item_name = display_item['display_name']
                if display_item['type'] == 'folder':
                    self.show_toast(f"已移除文件夹: {item_name}", "info")
                else:
                    self.show_toast(f"已移除文件: {item_name}", "info")
                
        except Exception:
            pass
        # 同步更新漏洞审计按钮状态
        try:
            self.update_vulnerability_audit_button_state()
        except Exception:
            pass
    
    def clear_file_tags(self):
        """清除所有文件标签"""
        try:
            for tag_info in self.current_file_tags:
                tag_info['tag_frame'].destroy()
            
            self.current_file_tags = []
            self.file_interaction_active = False
            self.selected_files_for_interaction = []
            
            # 清除显示项目列表
            if hasattr(self, 'selected_display_items'):
                self.selected_display_items = []
            
            # 收起标签区域以避免占位
            try:
                self.file_tags_frame.pack_forget()
                self.tag_bar_status_label.configure(text="")
            except Exception:
                pass
            
        except Exception:
            pass
        # 同步更新漏洞审计按钮状态
        try:
            self.update_vulnerability_audit_button_state()
        except Exception:
            pass
    
    def analyze_selected_files_with_interaction(self, file_paths, question=""):
        """使用文件交互客户端分析选中的文件"""

        if not self.file_interaction_client:
            self.show_toast("文件交互客户端未初始化", "error")
            return
        
        # 显示思考动画
        self.show_thinking_animation()
        
        def worker():
            try:
                # 如果没有提供问题，使用默认问题
                if not question:
                    question = f"请分析这 {len(file_paths)} 个文件，说明它们的功能、结构和相互关系。请使用中文回复。"
                
                # 使用文件交互客户端分析文件
                response = self.file_interaction_client.analyze_files(file_paths, question)
                
                # 在主线程中更新UI
                def update_ui():
                    # 停止思考动画
                    self.stop_thinking_animation()
                    
                    # 添加文件列表到聊天记录
                    file_list = "\n".join([f"- {os.path.basename(f)}" for f in file_paths])
                    summary_msg = f"📁 已选择 {len(file_paths)} 个文件进行分析：\n{file_list}"
                    self.add_message_to_display("system", summary_msg)
                    
                    # 添加AI分析结果
                    self.add_message_to_display("assistant", response)
                    
                    # 设置文件交互模式
                    self.selected_files_for_interaction = file_paths
                    self.file_interaction_active = True
                    
                    # 添加文件交互标签
                    self.add_file_interaction_tag(file_paths)
                    
                    self.show_toast("文件分析完成", "success")
                
                self.after(0, update_ui)
                
            except Exception as e:
                def show_error():
                    # 停止思考动画
                    self.stop_thinking_animation()
                    self.show_toast(f"文件分析失败: {str(e)}", "error")
                self.after(0, show_error)
        
        # 在后台线程中执行分析
        threading.Thread(target=worker, daemon=True).start()
    
    def refresh_font_sizes(self):
        """刷新所有消息的字体大小"""
        if not hasattr(self, 'settings_manager') or not self.settings_manager:
            return
        
        new_size = self.settings_manager.get_font_size()
        for msg_info in getattr(self, 'message_components', []):
            text_widget = msg_info.get('content_text')
            if not text_widget:
                continue
            try:
                text_widget.configure(state="normal")
                text_widget.configure(font=("Consolas", new_size))
                self._apply_markdown_formatting(text_widget, msg_info.get('content', ''))
                text_widget.configure(state="disabled")
                text_widget.update_idletasks()
                line_count = int(text_widget.index('end-1c').split('.')[0])
                text_widget.configure(height=min(line_count, 60))
            except Exception:
                pass
    def set_toast_anchor(self, widget):
        """设置Toast的锚点控件（简化后不再绑定位置事件）"""
        self.toast_anchor_widget = widget
    
    # 核心功能方法
    def send_message(self):
        """发送消息 - 与原始聊天模块保持一致的交互方式"""
        message = self.input_text.get("1.0", "end").strip()
        if not message:
            return
        
        # 清空输入框
        self.input_text.delete("1.0", "end")
        
        # 显示用户消息
        self.add_message_to_display("user", message)
        
        # 检查是否是特殊命令
        if self.handle_special_commands(message):
            return
        
        # 如果文件交互模式激活且有选中的文件，使用文件交互客户端
        if (hasattr(self, 'file_interaction_active') and self.file_interaction_active and 
            hasattr(self, 'selected_files_for_interaction') and self.selected_files_for_interaction and
            self.file_interaction_client):
            
            self.send_file_interaction_message(message)
            return
        
        # 构建上下文信息
        context_info = self.build_context_info()
        
        # 构建完整的提示
        full_prompt = self.build_ai_prompt(message, context_info)
        
        # 发送给AI
        self.send_to_ai(full_prompt)

    def send_file_interaction_message(self, message):
        """使用文件交互客户端发送消息"""
        # 显示思考动画
        self.show_thinking_animation()
        
        # 显示文件上传状态
        self.show_file_upload_status()
        
        def worker():
            try:
                # 更新文件标签状态为"处理中"
                self.update_file_tags_status("processing")
                
                # 使用文件交互客户端分析文件
                response = self.file_interaction_client.analyze_files(
                    self.selected_files_for_interaction, 
                    message
                )
                
                # 统一清理AI输出中的重复脚本与Markdown代码块，并统一为 PY_PoC 标记
                def sanitize_response(text: str) -> str:
                    try:
                        import re
                        t = text or ""
                        if "—— 第" not in t and re.search(r"^\s*【\d+】\s*<中文权限", t, flags=re.MULTILINE):
                            def _fix_perm_line(m):
                                idx = m.group(1)
                                perm = (m.group(2) or "").strip()
                                return f"—— 第{idx}个相关漏洞 ——\n【15】{perm}"
                            t = re.sub(r"^\s*【(\d+)】\s*<中文权限[:：]?\s*([^>]+)>\s*$", _fix_perm_line, t, flags=re.MULTILINE)
                            t = re.sub(r"^\s*【14】\s*<([^>]+)>\s*$", r"【14】\1", t, flags=re.MULTILINE)
                        # 1) 将 Markdown 代码块转换为纯文本代码（避免直接丢失 PoC）
                        def _strip_fenced_code(m):
                            inner = (m.group(1) or "").strip("\n")
                            return inner + "\n"
                        t = re.sub(r"```(?:python|py)?\s*\n([\s\S]*?)```", _strip_fenced_code, t, flags=re.IGNORECASE)
                        # 2) 移除“【11】PoC.py：”之后到首个脚本标记之间的任何原始代码片段（避免重复）（大小写不敏感）
                        t = re.sub(
                            r"(【11】PoC\.py：)(.*?)(?=(===PY_(?:SCRIPT|POC)_START===))",
                            r"\1",
                            t,
                            flags=re.DOTALL | re.IGNORECASE,
                        )
                        # 3) 规范化脚本块：接受 PY_SCRIPT/PY_POC 两种旧标记，统一输出为 PY_PoC 标记（大小写不敏感）
                        block_pattern = r"(===PY_(?:SCRIPT|POC)_START===)(.*?)(===PY_(?:SCRIPT|POC)_END===)"
                        def _repl(m):
                            inner = m.group(2)
                            script_clean = inner.replace("`", "").strip()
                            return "===PY_PoC_START===\n" + script_clean + "\n===PY_PoC_END==="
                        t = re.sub(block_pattern, _repl, t, flags=re.DOTALL | re.IGNORECASE)
                        # 3.0) 若缺少脚本标记但已给出代码，尝试把 PoC 包裹到统一标记中
                        if "===PY_PoC_START===" not in t:
                            m = re.search(r"(【11】PoC\.py[:：].*?\n)([\s\S]*?)((?:\n【\d+】)|(?:\n——\s*第)|(?:\n=+)|\Z)", t)
                            if m:
                                label = m.group(1)
                                code = (m.group(2) or "").strip()
                                tail = m.group(3) or ""
                                looks_like_code = bool(re.search(r"\bimport\s+\w+|\brequests\b|\bdef\s+\w+\s*\(|\bsession\s*=", code))
                                if code and looks_like_code:
                                    wrapped = "===PY_PoC_START===\n" + code + "\n===PY_PoC_END===\n"
                                    t = t[:m.start()] + label + wrapped + tail + t[m.end():]
                        blocks = re.findall(r"===PY_PoC_START===.*?===PY_PoC_END===", t, flags=re.DOTALL)
                        t = re.sub(r"===PY_PoC_START===.*?===PY_PoC_END===", "", t, flags=re.DOTALL)
                        t = re.sub(r"(^【URL】)\s*`?\s*([^`\s]+)\s*`?\s*$", r"\1 \2", t, flags=re.MULTILINE)
                        parts = re.split(r"(——\s*第\d+个相关(?:漏洞|风险)\s*——)", t)
                        if len(parts) > 1 and blocks:
                            prefix = parts[0].strip()
                            out_sections = []
                            poc_i = 0
                            for i in range(1, len(parts), 2):
                                header = parts[i]
                                body = parts[i + 1] if i + 1 < len(parts) else ""
                                section = (header + body).strip()
                                if "===PY_PoC_START===" not in section:
                                    use_block = blocks[poc_i] if poc_i < len(blocks) else blocks[-1]
                                    sec_url = None
                                    murl = re.search(r"^\s*【URL】\s*([^\s]+)\s*$", section, flags=re.MULTILINE)
                                    if murl:
                                        sec_url = murl.group(1).strip("` ").strip()
                                    if sec_url:
                                        try:
                                            from urllib.parse import urlparse
                                            parsed = urlparse(sec_url)
                                            base_url = f"{parsed.scheme}://{parsed.netloc}"
                                            path_parts = [p for p in parsed.path.split("/") if p]
                                            root = base_url + ("/" + path_parts[0] if path_parts else "")
                                            if len(path_parts) >= 2:
                                                root = base_url + "/" + path_parts[0] + "/" + path_parts[1]
                                            def _adapt(code_block: str) -> str:
                                                cb = code_block.replace("`", "")
                                                cb = re.sub(r"^(\s*(?:upload_url|url|target_url)\s*=\s*['\"])([^'\"]+)(['\"])", r"\1" + sec_url + r"\3", cb, flags=re.MULTILINE)
                                                cb = re.sub(r"^(\s*(?:access_url)\s*=\s*f?['\"])\s*https?://[^'\"]+(/upload/)", r"\1" + root + r"\2", cb, flags=re.MULTILINE)
                                                return cb
                                            use_block = _adapt(use_block)
                                        except Exception:
                                            pass
                                    insert_block = use_block.strip() + "\n"
                                    if re.search(r"【11】PoC\.py[:：].*\n", section):
                                        section = re.sub(r"(【11】PoC\.py[:：].*\n)", r"\1" + insert_block, section, count=1)
                                    else:
                                        insert = "【11】PoC.py：\n" + insert_block
                                        if re.search(r"【9】.*\n", section):
                                            section = re.sub(r"(【9】.*\n)", r"\1" + insert, section, count=1)
                                        elif re.search(r"【URL】.*\n", section):
                                            section = re.sub(r"(【URL】.*\n)", r"\1" + insert, section, count=1)
                                        else:
                                            section = header + "\n" + insert + body
                                    poc_i += 1
                                out_sections.append(section.strip())
                            t = (prefix + "\n\n" if prefix else "") + "\n\n".join([s for s in out_sections if s])
                        elif blocks and "【11】PoC.py" not in t:
                            insert = "【11】PoC.py：\n" + blocks[0].strip() + "\n"
                            if "【9】" in t:
                                t = re.sub(r"(【9】.*\n)", r"\1" + insert, t, count=1)
                            elif "【URL】" in t:
                                t = re.sub(r"(【URL】.*\n)", r"\1" + insert, t, count=1)
                            else:
                                t = insert + "\n" + t
                        # 4) 收敛多余空行
                        t = re.sub(r"\n{3,}", "\n\n", t)
                        return t
                    except Exception:
                        return text
                
                # 在主线程中更新UI
                def update_ui():
                    self.stop_thinking_animation()
                    self.update_file_tags_status("completed")
                    sanitized = sanitize_response(response)
                    self.add_message_to_display("assistant", sanitized)
                    self.show_toast("文件分析完成", "success")
                
                self.after(0, update_ui)
                
            except Exception as e:
                error_message = str(e)  # 在闭包外捕获异常信息
                def show_error():
                    self.stop_thinking_animation()
                    self.update_file_tags_status("error")
                    error_msg = f"文件交互失败: {error_message}"
                    self.add_message_to_display("assistant", error_msg)
                    self.show_toast(error_msg, "error")
                
                self.after(0, show_error)
        
        # 在后台线程中执行
        threading.Thread(target=worker, daemon=True).start()
    
    def show_file_upload_status(self):
        """显示文件上传状态"""
        if hasattr(self, 'selected_files_for_interaction') and self.selected_files_for_interaction:
            file_count = len(self.selected_files_for_interaction)
            self.show_toast(f"正在处理 {file_count} 个文件...", "info", duration=2000)
    
    def update_file_tags_status(self, status):
        """更新文件标签的状态显示"""
        try:
            status_colors = {
                "processing": ("orange", "darkorange"),
                "completed": ("green", "darkgreen"), 
                "error": ("red", "darkred"),
                "normal": ("gray70", "gray30")
            }
            
            status_icons = {
                "processing": "⏳",
                "completed": "✅",
                "error": "❌",
                "normal": "📄"
            }
            
            for tag_info in self.current_file_tags:
                tag_frame = tag_info['tag_frame']
                file_path = tag_info['file_path']
                file_name = os.path.basename(file_path)
                
                # 更新文件标签的颜色和图标
                for widget in tag_frame.winfo_children():
                    if isinstance(widget, ctk.CTkLabel) and "📄" in widget.cget("text"):
                        icon = status_icons.get(status, "📄")
                        widget.configure(text=f"{icon} {file_name}")
                        
                        # 更新标签框的颜色
                        if status in status_colors:
                            tag_frame.configure(border_color=status_colors[status][0])
                            tag_frame.configure(border_width=2 if status != "normal" else 0)
                        break
                        
        except Exception as e:
            print(f"更新文件标签状态失败: {e}")
    
    def clear_input(self):
        """清空输入框"""
        try:
            self.input_text.delete("1.0", "end")
        except Exception:
            pass

    def insert_command_to_input(self, command_text: str):
        """将指令写入用户待输入框，并聚焦输入"""
        try:
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", command_text)
            # 聚焦到输入框，方便用户继续输入问题
            self.input_text.focus_set()
        except Exception as e:
            self.show_toast(f"写入指令失败: {e}", "error")

    def toggle_read_mode_menu(self):
        """切换显示/隐藏代码阅读模式菜单"""
        try:
            if self.read_mode_menu.winfo_ismapped():
                self.read_mode_menu.pack_forget()
            else:
                # 将菜单放到按钮下方靠左
                self.read_mode_menu.pack(side="left", padx=5, pady=5)
        except Exception as e:
            self.show_toast(f"切换阅读模式菜单失败: {e}", "error")

    def on_select_read_mode(self, mode: str):
        """处理阅读模式菜单选择，将相应指令写入输入框"""
        # 选择后隐藏菜单
        try:
            self.read_mode_menu.pack_forget()
        except Exception:
            pass
        
        if mode == "file_interaction":
            # 显示文件选择对话框
            self.show_project_files_selection()
            # 设置文件交互标记，所有后续问题都会带上此标记
            self.file_interaction_active = True
            self.show_toast("文件交互模式已激活，请选择要分析的文件", "info")
        elif mode == "project_all":
            # 保留原有功能，写入 /readall 指令
            self.insert_command_to_input("/readall ")
            # 给出提示
            self.show_toast("已填入指令 /readall ，请输入你的问题，如：找出项目中的管理员账号密码", "info")
        elif mode == "current_file":
            # 写入 /read <path> 指令
            file_path = getattr(self, "current_file_path", None)
            proj_path = getattr(self, "current_project_path", None)
            cmd = "/read "
            if file_path:
                try:
                    # 计算相对路径（若有项目路径）
                    if proj_path and os.path.commonpath([proj_path, file_path]) == proj_path:
                        rel = os.path.relpath(file_path, proj_path)
                        cmd = f"/read {rel} "
                    else:
                        cmd = f"/read {file_path} "
                except Exception:
                    cmd = f"/read {file_path} "
            else:
                self.show_toast("请先在左栏打开一个文件，再使用‘阅读当前文件’", "warning")
            self.insert_command_to_input(cmd)
        else:
            self.show_toast("未知的阅读模式", "error")
    
    def on_env_setup_guide(self):
        """处理环境搭建指导按钮点击"""
        try:
            # 检查是否有文件标签
            if not hasattr(self, 'file_interaction_active') or not self.file_interaction_active:
                self.show_toast("请先选择要分析的文件", "warning")
                return
            
            if not hasattr(self, 'selected_files_for_interaction') or not self.selected_files_for_interaction:
                self.show_toast("请先选择要分析的文件", "warning")
                return
            
            # 获取当前项目文件夹名称
            project_folder_name = "项目"
            if hasattr(self, 'current_project_path') and self.current_project_path:
                project_folder_name = os.path.basename(self.current_project_path)
            
            # 分析文件类型以提供针对性指导
            file_types = set()
            has_php = False
            has_sql = False
            has_config = False
            
            for file_path in self.selected_files_for_interaction:
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    file_types.add(ext)
                    if ext == '.php':
                        has_php = True
                    elif ext == '.sql':
                        has_sql = True
                    elif ext in ['.ini', '.conf', '.config', '.env']:
                        has_config = True
            
            # 从外部文件读取环境搭建指导prompt模板
            try:
                prompt_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts', 'env_setup_guide.txt')
                with open(prompt_file_path, 'r', encoding='utf-8') as f:
                    prompt_template = f.read()
                
                # 格式化提示词模板
                env_setup_prompt = prompt_template.format(
                    project_folder_name=project_folder_name,
                    file_types=', '.join(file_types)
                )
            except Exception as e:
                # 如果读取外部文件失败，使用备用的简化提示词
                print(f"读取环境搭建提示词文件失败: {e}")
                env_setup_prompt = f"""请基于提供的文件内容，为我提供详细的PHPStudy测试环境搭建指导。

项目文件夹名称: {project_folder_name}
检测到的文件类型: {', '.join(file_types)}

请提供详细的PHPStudy环境配置步骤，包括：
1. 文件部署到WWW目录
2. 启动PHPStudy服务
3. 数据库创建和配置（如果需要）
4. 项目特定配置

访问地址: http://cvehunter.test/{project_folder_name}

请使用中文回复，所有输出内容必须是中文。"""
            
            # 发送环境搭建指导请求
            self.send_file_interaction_message(env_setup_prompt)
            
            # 显示提示信息
            self.show_toast("正在生成详细的PHPStudy环境搭建指导...", "info")
            
        except Exception as e:
            self.show_toast(f"环境搭建指导失败: {e}", "error")
    
    def update_env_setup_button_state(self):
        """更新环境搭建指导按钮的启用/禁用状态"""
        try:
            if hasattr(self, 'env_setup_btn'):
                # 检查是否有任何类型的标签存在
                has_file_tags = (hasattr(self, 'current_file_tags') and self.current_file_tags)
                has_project_tags = (hasattr(self, 'project_folder_tags') and self.project_folder_tags)
                has_files_selected = (hasattr(self, 'selected_files_for_interaction') and self.selected_files_for_interaction)
                
                # 只要有任何一种标签存在就启用按钮
                if has_file_tags or has_project_tags or has_files_selected:
                    self.env_setup_btn.configure(state="normal")
                else:
                    self.env_setup_btn.configure(state="disabled")
        except Exception as e:
            print(f"更新环境搭建按钮状态失败: {e}")

    def update_vulnerability_audit_button_state(self):
        """更新漏洞审计按钮的启用/禁用状态（与文件交互选择保持一致）"""
        try:
            if hasattr(self, 'vuln_audit_btn'):
                has_file_tags = (hasattr(self, 'current_file_tags') and self.current_file_tags)
                has_project_tags = (hasattr(self, 'project_folder_tags') and self.project_folder_tags)
                has_files_selected = (hasattr(self, 'selected_files_for_interaction') and self.selected_files_for_interaction)
                interaction_active = getattr(self, 'file_interaction_active', False)
                # 存在标签或已选择文件进行交互时启用
                if has_file_tags or has_project_tags or (interaction_active and has_files_selected):
                    self.vuln_audit_btn.configure(state="normal")
                else:
                    self.vuln_audit_btn.configure(state="disabled")
        except Exception:
            pass

    def on_restart_application(self):
        """重启当前应用"""
        try:
            self.show_toast("正在重启软件...", "info")
        except Exception:
            pass
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            run_app_path = os.path.join(base_dir, "run_app.py")
            python = sys.executable
            os.execl(python, python, run_app_path)
        except Exception as e:
            try:
                self.show_toast(f"重启失败: {e}", "error")
            except Exception:
                pass

    def _ensure_vuln_panel(self):
        """确保漏洞审计选项条已创建（水平一字排开，靠按钮右侧）"""
        if hasattr(self, 'vuln_panel') and self.vuln_panel:
            return
        try:
            # 选项条挂载到快捷操作容器，保证与按钮同行
            parent = getattr(self, 'quick_actions_frame', self)
            panel = ctk.CTkFrame(parent, fg_color="transparent")

            options = [
                ("SQL注入漏洞", "sql_injection"),
                ("文件上传漏洞", "file_upload"),
                ("XSS漏洞", "xss"),
                ("弱口令风险", "weak_password"),
            ]

            def choose_vuln(label, key):
                try:
                    self.add_message_to_display("system", f"🛡️已选择漏洞审计类型：{label}")
                except Exception:
                    pass
                # 执行对应审计并收起面板
                try:
                    self.on_vuln_option_selected(key, label)
                except Exception as e:
                    try:
                        self.show_toast(f"审计选项触发失败: {e}", "error")
                    except Exception:
                        pass
                self._hide_vuln_panel()

            for text, key in options:
                btn = ctk.CTkButton(panel, text=text, height=28, width=110,
                                    command=lambda t=text, k=key: choose_vuln(t, k))
                btn.pack(side="left", padx=4, pady=(0, 0))

            # 保存引用供后续展示
            self.vuln_panel = panel
        except Exception as e:
            self.show_toast(f"创建漏洞审计选项失败: {e}", "error")

    def on_vuln_option_selected(self, key: str, label: str):
        """根据选择的漏洞类型执行审计动作"""
        try:
            has_files_selected = (hasattr(self, 'selected_files_for_interaction') and self.selected_files_for_interaction)
            interaction_active = getattr(self, 'file_interaction_active', False)
            if not (interaction_active and has_files_selected):
                self.show_toast("请先选择要分析的文件", "warning")
                return

            if key == "sql_injection":
                self.run_sql_injection_audit()
            elif key == "file_upload":
                self.run_file_upload_audit()
            elif key == "xss":
                self.run_xss_audit()
            elif key == "weak_password":
                self.run_weak_password_audit()
            else:
                self.show_toast("未知的漏洞类型", "error")
        except Exception as e:
            self.show_toast(f"执行漏洞审计失败: {e}", "error")

    def run_sql_injection_audit(self):
        """读取SQL注入提示词并通过文件交互客户端发送"""
        try:
            project_folder_name = "项目"
            if hasattr(self, 'current_project_path') and self.current_project_path:
                try:
                    project_folder_name = os.path.basename(self.current_project_path)
                except Exception:
                    pass

            base_dir = os.path.dirname(os.path.dirname(__file__))
            prompt_path = os.path.join(base_dir, 'prompts', 'SQL注入关键提示词.txt')
            prompt_text = ""
            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    prompt_text = f.read()
            except Exception as e:
                print(f"读取SQL注入提示词失败: {e}")

            if not prompt_text:
                prompt_text = f"""请作为资深代码审计专家，审计选中文件中的SQL注入风险。
- 严格输出漏洞报告结构，覆盖权限、文件路径、请求方式、URL调用路径、漏洞参数、sqlmap命令等要点。
- 访问地址模板：http://cvehunter.test/{project_folder_name}
请使用中文回复，并按要求在关键点前输出编号标记。"""
            else:
                # 将项目名插入到提示词的URL占位
                prompt_text = prompt_text.replace("{提供的项目文件夹}", project_folder_name)

            # 发送审计请求
            self.send_file_interaction_message(prompt_text)
            self.show_toast("正在执行SQL注入漏洞审计...", "info")
        except Exception as e:
            self.show_toast(f"SQL注入审计失败: {e}", "error")

    def run_file_upload_audit(self):
        """读取文件上传提示词并通过文件交互客户端发送"""
        try:
            project_folder_name = "项目"
            if hasattr(self, 'current_project_path') and self.current_project_path:
                try:
                    project_folder_name = os.path.basename(self.current_project_path)
                except Exception:
                    pass

            base_dir = os.path.dirname(os.path.dirname(__file__))
            prompt_path = os.path.join(base_dir, 'prompts', '文件上传关键提示词.txt')
            prompt_text = ""
            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    prompt_text = f.read()
            except Exception:
                pass

            if not prompt_text:
                prompt_text = (
                    "你是一名资深的代码审计专家，你现在受邀为刚开发完成的系统进行代码审计。\n"
                    "你这次的目标是读取得到的所有文件，并找到该系统中的所有文件上传漏洞。\n"
                    "该系统的厂商已经在本地搭建好测试系统，并映射为：\n"
                    "http://cvehunter.test/{提供的项目文件夹}\n"
                    "所以后续需要输出的漏洞信息都要有关于该url。\n\n"
                    "输出规则（请务必严格遵守）：\n"
                    "0、你每发现一个漏洞就将该漏洞信息对应的后面的每个规则都输出一遍。你的每次回答均不需要说明你的原因，你只需要输出与要求最相近的结果，且简略易看。\n"
                    "1、发现并输出该处文件上传需要的权限？（输出的时候在\"无需登录或授权即可利用此漏洞\\需要基本用户权限才能利用此漏洞\\需要管理员权限才能利用此漏洞\"中选一个，并在前面加上【15】；同时在\"No login or authorization is required to exploit this vulnerability\\Need basic user permissions to exploit this vulnerability\\Need admin permission to exploit this vulnerability\"中选一个，并在前面加上【14】）\n"
                    "2、发现并输出存在该处漏洞的文件相对路径？（输出的时候在前面加上【7】）\n"
                    "3、发现并输出处理文件上传的请求方式是GET/POST类型？\n"
                    "4、发现并输出该处的漏洞的web端url调用路径？\n"
                    "5、发现并输出用于文件上传的表单字段名或参数？（输出的时候在前面加上【9】）\n"
                    "6、输出用于验证该文件上传漏洞的测试PoC.py（输出的时候在前面加上【11】）。PoC需使用分隔标记===PY_PoC_START===与===PY_PoC_END===包裹，且木马内容必须为：<?php $f=chr(115).chr(121).chr(115).chr(116).chr(101).chr(109); $f($_REQUEST['x']); ?>（密码参数名为x）。Python字符串不得使用f前缀（如f\"...\"），避免花括号被误解析。不要删除已上传的文件，上传成功后请明确输出webshell最终URL、服务器保存路径，并执行whoami，打印HTTP状态码与响应正文。严禁在标记外输出任何Python或PHP代码；“【11】PoC.py”行仅作标签，下一行必须是===PY_PoC_START===。URL字面量不得包含反引号或额外空格；命令执行参数固定为x（例如requests.get(shell_url, params={\"x\": \"whoami\"})）；文件名示例为file_name = str(random.randint(1000,9999)) + \".php\"（禁止使用f-string）；脚本开头必须显式声明password = 'x'。遵循最简与最高可用原则：仅保留核心导入与逻辑（requests、os、random）；输出只包含最终 webshell URL、服务器保存路径、whoami 的 HTTP 状态码与正文；避免多余日志与解释；脚本长度尽量控制在 120 行以内；不得重复变量与函数；禁止无关的 try/except 与 sleep/循环。\n\n"
                    "好了，开始吧"
                )
            else:
                prompt_text = prompt_text.replace("{提供的项目文件夹}", project_folder_name)

            # 发送审计请求
            self.send_file_interaction_message(prompt_text)
            self.show_toast("正在执行文件上传漏洞审计...", "info")
        except Exception as e:
            self.show_toast(f"文件上传审计失败: {e}", "error")

    def run_xss_audit(self):
        """读取XSS提示词并通过文件交互客户端发送"""
        try:
            project_folder_name = "项目"
            if hasattr(self, 'current_project_path') and self.current_project_path:
                try:
                    project_folder_name = os.path.basename(self.current_project_path)
                except Exception:
                    pass

            base_dir = os.path.dirname(os.path.dirname(__file__))
            prompt_path = os.path.join(base_dir, 'prompts', 'XSS关键提示词.txt')
            prompt_text = ""
            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    prompt_text = f.read()
            except Exception:
                pass

            if not prompt_text:
                prompt_text = (
                    "你是一名资深的代码审计专家，你现在受邀为刚开发完成的系统进行代码审计。\n"
                    "你这次的目标是读取得到的所有文件，并找到该系统中的所有XSS漏洞。\n"
                    "该系统的厂商已经在本地搭建好测试系统，并映射为：\n"
                    "http://cvehunter.test/{提供的项目文件夹}\n"
                    "所以后续需要输出的漏洞信息都要有关于该url。\n\n"
                    "输出规则（请务必严格遵守）：\n"
                    "0、你每发现一个漏洞就将该漏洞信息对应的后面的每个规则都输出一遍。你的每次回答均不需要说明你的原因，你只需要输出与要求最相近的结果，且简略易看。\n"
                    "1、发现并输出该处XSS需要的权限？（输出的时候在\"无需登录或授权即可利用此漏洞\\需要基本用户权限才能利用此漏洞\\需要管理员权限才能利用此漏洞\"中选一个，并在前面加上【15】；同时在\"No login or authorization is required to exploit this vulnerability\\Need basic user permissions to exploit this vulnerability\\Need admin permission to exploit this vulnerability\"中选一个，并在前面加上【14】）\n"
                    "2、发现并输出存在该处漏洞的文件相对路径？（输出的时候在前面加上【7】）\n"
                    "3、发现并输出触发该XSS的请求方式是GET/POST类型？\n"
                    "4、发现并输出该处的漏洞的web端url调用路径？\n"
                    "5、发现并输出url或表单中传递的漏洞参数？（输出的时候在前面加上【9】）\n"
                    "6、输出用于验证该XSS漏洞的测试payload（输出的时候在前面加上【11】）。\n\n"
                    "好了，开始吧"
                )
            else:
                prompt_text = prompt_text.replace("{提供的项目文件夹}", project_folder_name)

            # 发送审计请求
            self.send_file_interaction_message(prompt_text)
            self.show_toast("正在执行XSS漏洞审计...", "info")
        except Exception as e:
            self.show_toast(f"XSS审计失败: {e}", "error")

    def run_rce_audit(self):
        """读取RCE提示词并通过文件交互客户端发送"""
        try:
            project_folder_name = "项目"
            if hasattr(self, 'current_project_path') and self.current_project_path:
                try:
                    project_folder_name = os.path.basename(self.current_project_path)
                except Exception:
                    pass

            base_dir = os.path.dirname(os.path.dirname(__file__))
            prompt_path = os.path.join(base_dir, 'prompts', 'RCE关键提示词.txt')
            prompt_text = ""
            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    prompt_text = f.read()
            except Exception:
                pass

            if not prompt_text:
                prompt_text = (
                    "你是一名资深的代码审计专家，你现在受邀为刚开发完成的系统进行代码审计。\n"
                    "你这次的目标是读取得到的所有文件，并找到该系统中的所有远程代码执行（RCE）漏洞。\n"
                    "该系统的厂商已经在本地搭建好测试系统，并映射为：\n"
                    f"http://cvehunter.test/{project_folder_name}\n"
                    "所以后续需要输出的漏洞信息都要有关于该url。\n\n"
                    "请根据统一模板输出结构化的漏洞信息，并提供用于验证该RCE漏洞的PoC.py（纯Python，禁止Markdown代码块，脚本使用===PY_SCRIPT_START===与===PY_SCRIPT_END===分隔，且不使用#注释）。\n"
                )
            else:
                prompt_text = prompt_text.replace("{提供的项目文件夹}", project_folder_name)

            # 发送审计请求
            self.send_file_interaction_message(prompt_text)
            self.show_toast("正在执行RCE漏洞审计...", "info")
        except Exception as e:
            self.show_toast(f"RCE审计失败: {e}", "error")

    def run_weak_password_audit(self):
        """读取弱口令提示词并通过文件交互客户端发送（不生成PoC）"""
        try:
            project_folder_name = "项目"
            if hasattr(self, 'current_project_path') and self.current_project_path:
                try:
                    project_folder_name = os.path.basename(self.current_project_path)
                except Exception:
                    pass

            base_dir = os.path.dirname(os.path.dirname(__file__))
            prompt_path = os.path.join(base_dir, 'prompts', '弱口令关键提示词.txt')
            prompt_text = ""
            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    prompt_text = f.read()
            except Exception:
                pass

            if not prompt_text:
                prompt_text = (
                    "你是一名资深的代码审计专家，你现在受邀为刚开发完成的系统进行代码审计。\n"
                    "你这次的目标是读取得到的所有文件，并发现弱口令/默认口令/硬编码凭据/登录绕过风险。\n"
                    "该系统的厂商已经在本地搭建好测试系统，并映射为：\n"
                    f"http://cvehunter.test/{project_folder_name}\n"
                    "所以后续需要输出的风险信息都要有关于该url。\n\n"
                    "请根据统一模板输出结构化的弱口令帐密信息（【16】弱口令帐密），无需生成PoC脚本。\n"
                )
            else:
                prompt_text = prompt_text.replace("{提供的项目文件夹}", project_folder_name)

            # 发送审计请求
            self.send_file_interaction_message(prompt_text)
            self.show_toast("正在执行弱口令风险审计...", "info")
        except Exception as e:
            self.show_toast(f"弱口令审计失败: {e}", "error")

    def _hide_vuln_panel(self):
        try:
            if hasattr(self, 'vuln_panel') and self.vuln_panel and self.vuln_panel.winfo_ismapped():
                try:
                    self.vuln_panel.pack_forget()
                except Exception:
                    self.vuln_panel.place_forget()
            # 同步隐藏右侧三角指示器
            try:
                if hasattr(self, 'vuln_audit_indicator') and self.vuln_audit_indicator and self.vuln_audit_indicator.winfo_ismapped():
                    self.vuln_audit_indicator.pack_forget()
            except Exception:
                pass
        except Exception:
            pass

    def on_vulnerability_audit(self):
        """点击漏洞审计：在按钮右侧水平展开四个选项，重复点击收起"""
        try:
            # 触发条件与环境搭建指导一致：存在文件/项目标签或已选择用于交互的文件
            has_file_tags = (hasattr(self, 'current_file_tags') and self.current_file_tags)
            has_project_tags = (hasattr(self, 'project_folder_tags') and self.project_folder_tags)
            has_files_selected = (hasattr(self, 'selected_files_for_interaction') and self.selected_files_for_interaction)
            if not (has_file_tags or has_project_tags or has_files_selected):
                self.show_toast("请先选择要分析的文件或项目", "warning")
                return

            self._ensure_vuln_panel()
            panel = self.vuln_panel

            # 已显示则收起（切换）
            if panel.winfo_ismapped():
                self._hide_vuln_panel()
                return

            # 与按钮同一行，靠右侧水平展开
            try:
                panel.pack(side="left", padx=6, pady=(0, 0))
                # 展开时显示右侧三角指示器
                try:
                    if hasattr(self, 'vuln_audit_indicator') and self.vuln_audit_indicator:
                        self.vuln_audit_indicator.pack(side="left", padx=(2, 0))
                except Exception:
                    pass
                panel.lift()
            except Exception:
                # 兜底：无法 pack 时，改用 place 挨着按钮右侧
                parent = getattr(self, 'quick_actions_frame', self)
                parent.update_idletasks()
                self.vuln_audit_btn.update_idletasks()
                panel.update_idletasks()

                bx = self.vuln_audit_btn.winfo_x()
                by = self.vuln_audit_btn.winfo_y()
                bw = self.vuln_audit_btn.winfo_width()
                x = bx + bw + 8
                y = max(by - 1, 0)
                panel.place(x=x, y=y)
                panel.lift()
                # 兜底情况下也显示指示器
                try:
                    if hasattr(self, 'vuln_audit_indicator') and self.vuln_audit_indicator and not self.vuln_audit_indicator.winfo_ismapped():
                        self.vuln_audit_indicator.pack(side="left", padx=(2, 0))
                except Exception:
                    pass
        except Exception as e:
            self.show_toast(f"展开漏洞审计选项失败: {e}", "error")
    
    def handle_special_commands(self, message: str) -> bool:
        """处理特殊命令"""
        message_lower = message.lower().strip()
        
        # 文件分析命令
        if message_lower.startswith("/analyze") or message_lower.startswith("/readall"):
            # 提取命令后面的内容（保留原始大小写）
            command_prefix = "/analyze" if message_lower.startswith("/analyze") else "/readall"
            tail = message[len(command_prefix):].strip()
            
            # 解析选项
            options = {
                "upload": "--upload" in tail,
                "all": "--all" in tail
            }
            
            # 移除选项标志，保留实际查询内容
            for option in ["--upload", "--all"]:
                if option in tail:
                    tail = tail.replace(option, "").strip()
                
            if tail:
                # 记录待在读取完成后自动提问的内容
                self.pending_query_after_readall = tail
            
            # 直接在对话中处理文件分析
            if options["all"]:
                # 执行批量读取所有文件
                self.read_all_project_files(upload_to_model=options["upload"])
            else:
                # 获取当前打开的文件列表
                open_files = self.get_open_files()
                if open_files:
                    # 直接分析当前打开的文件
                    self.analyze_selected_files(open_files, upload_to_model=options["upload"], question=tail)
                else:
                    # 兼容旧方法，此处直接调用新方法
                    self.show_project_files_selection(upload_to_model=options["upload"])
            
            return True
        
        if message_lower.startswith("/read "):
            # 读取文件命令
            file_path = message[6:].strip()
            self.read_file_command(file_path)
            return True
        
        elif message_lower.startswith("/analyze "):
            # 分析文件命令
            file_path = message[9:].strip()
            self.analyze_file_command(file_path)
            return True
        
        elif message_lower == "/project":
            # 分析项目结构
            self.analyze_project_structure()
            return True
        
        elif message_lower == "/current":
            # 分析当前文件
            self.analyze_current_file()
            return True
        
        elif message_lower == "/help":
            # 显示帮助
            self.show_help()
            return True
        
        return False
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """🤖 AI代码助手帮助

特殊命令:
/read <文件路径> - 读取指定文件
/analyze <文件路径> - 分析指定文件
/project - 分析项目结构
/current - 分析当前文件
/help - 显示此帮助

功能按钮:
📄 分析当前文件 - 分析当前打开的文件
📁 分析项目结构 - 分析整个项目的结构
💡 代码建议 - 获取代码改进建议
🧹 清理断点 - 清理过期的文件断点

快捷键:
Enter - 发送消息
Ctrl+Enter - 换行

大文件处理:
- 自动检测大文件并分块读取
- 支持断点续传
- 智能选择重要代码段"""
        
        self.add_message_to_display("assistant", help_text.strip())
    
    def build_context_info(self) -> Dict[str, Any]:
        """构建上下文信息"""
        context = {
            'project_path': self.current_project_path,
            'current_file': self.current_file_path,
            'file_contexts': self.file_contexts,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 添加项目结构信息（如果有）
        if self.current_project_path and os.path.exists(self.current_project_path):
            context['project_structure'] = self.get_project_structure_summary()
        
        return context
    
    def build_ai_prompt(self, user_message: str, context_info: Dict[str, Any]) -> str:
        """构建AI提示（带上下文预算与相关内容筛选，避免超出令牌限制）"""
        # 简单的预算控制（以字符为近似，避免超长）：
        MAX_PROMPT_CHARS = 160_000
        MAX_CONTEXT_CHARS = 120_000
        MAX_FILES_IN_CONTEXT = 40
        PER_FILE_MAX_CHARS = 5_000
        
        def filter_file_contexts(user_msg: str, file_contexts: Dict[str, Any]) -> Dict[str, Any]:
            """根据用户问题对文件上下文进行相关性筛选与摘要截取，控制总长度预算。"""
            import re
            if not file_contexts:
                return {}
            # 提取关键词（中英文混合），用于粗略相关性评分
            raw = (user_msg or "").lower()
            # 常见凭据/安全相关关键词（提高权重）
            extra_keys = [
                "admin", "administrator", "root", "superuser",
                "账号", "帐户", "用户", "管理员", "密码", "口令", "密钥", "凭据", "认证", "登录",
                "login", "auth", "credential", "password", "passwd", "pwd",
                "secret", "token", "apikey", "api_key", "access_key", "key_id",
                "private key", "jwt", "bearer", "oauth", "ssh", "AKIA"
            ]
            # 基于简单分词（空白与标点）
            msg_terms = re.split(r"[\s,;，。:：()\[\]{}<>\-/]+", raw)
            keywords = set([t for t in msg_terms if t]) | set(extra_keys)
            # 评分与片段提取
            # 片段策略：每个匹配项提取上下各2行作为片段，最多5个片段
            def extract_snippets(text: str, patterns: list[str], max_snippets: int = 5, context_lines: int = 2) -> list[str]:
                lines = text.splitlines()
                snippets = []
                for i, line in enumerate(lines):
                    if any(re.search(p, line, flags=re.IGNORECASE) for p in patterns):
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        snippet = "\n".join(lines[start:end])
                        snippets.append(snippet)
                        if len(snippets) >= max_snippets:
                            break
                return snippets
            # 构造正则模式集合
            patt = [
                r"admin", r"administrator", r"root", r"superuser",
                r"账号|帐户|用户|管理员|密码|口令|密钥|凭据|认证|登录",
                r"login|auth|credential|password|passwd|pwd",
                r"secret|token|api[_-]?key|access[_-]?key|key[_-]?id|AKIA[0-9A-Z]{16}",
                r"-----BEGIN[\s]+PRIVATE[\s]+KEY-----"
            ]
            # 对每个文件进行粗略相关性评分
            scored_items = []
            for fpath, fc in file_contexts.items():
                text = str(fc.get("content", ""))
                if not text:
                    continue
                # 基于关键词出现次数的评分
                score = 0
                for kw in keywords:
                    try:
                        score += text.lower().count(kw.lower())
                    except Exception:
                        pass
                # 基于模式匹配加权
                for p in patt:
                    try:
                        if re.search(p, text, flags=re.IGNORECASE):
                            score += 5
                    except Exception:
                        pass
                # 提取片段作为压缩内容
                snippets = extract_snippets(text, patt, max_snippets=5, context_lines=2)
                compressed = "\n...\n".join(snippets) if snippets else text[:PER_FILE_MAX_CHARS]
                scored_items.append((fpath, fc, score, compressed))
            # 依据分数排序，取前N个文件并按预算截断
            scored_items.sort(key=lambda x: x[2], reverse=True)
            filtered: Dict[str, Any] = {}
            total_chars = 0
            count = 0
            for fpath, fc, score, compressed in scored_items:
                if count >= MAX_FILES_IN_CONTEXT:
                    break
                # 若无明显相关性且预算紧张，跳过
                if score <= 0 and total_chars > (MAX_CONTEXT_CHARS * 0.6):
                    continue
                # 截断到每文件上限
                part = compressed[:PER_FILE_MAX_CHARS]
                # 防止超预算
                if total_chars + len(part) > MAX_CONTEXT_CHARS:
                    remain = MAX_CONTEXT_CHARS - total_chars
                    if remain <= 0:
                        break
                    part = part[:remain]
                filtered[fpath] = {
                    "content": part,
                    "is_truncated": True,
                    "summary": fc.get("summary", "") or "基于相关性提取的片段",
                    "relative_path": fc.get("relative_path"),
                    "size": fc.get("size")
                }
                total_chars += len(part)
                count += 1
            return filtered
        
        # 生成上下文（过滤版）
        safe_file_contexts = filter_file_contexts(user_message, context_info.get("file_contexts", {}))
        
        prompt_parts: list[str] = []
        # 系统角色定义
        prompt_parts.append(
            """你是一个专业的AI代码助手，具有以下能力：
1. 代码分析和理解
2. 代码优化建议
3. 错误诊断和修复
4. 项目结构分析
5. 代码重构建议

请根据用户的问题和提供的上下文信息，给出专业、准确、有用的回答。请使用中文回复，所有输出内容必须是中文。"""
        )
        
        # 添加项目上下文
        if context_info.get('project_path'):
            prompt_parts.append(f"\n当前项目路径: {context_info['project_path']}")
        if context_info.get('current_file'):
            prompt_parts.append(f"当前文件: {context_info['current_file']}")
        
        # 添加项目结构信息
        if context_info.get('project_structure'):
            structure = context_info['project_structure']
            prompt_parts.append(f"\n项目结构摘要:")
            prompt_parts.append(f"- 总文件数: {structure.get('total_files', 0)}")
            prompt_parts.append(f"- 文件类型: {structure.get('file_types', {})}")
            if structure.get('main_files'):
                prompt_parts.append(f"- 主要文件: {', '.join(structure['main_files'])}")
        
        # 添加过滤后的文件上下文
        if safe_file_contexts:
            prompt_parts.append("\n相关文件内容（已根据问题筛选与压缩）：")
            for fpath, fc in safe_file_contexts.items():
                prompt_parts.append(f"\n--- {fpath} ---")
                if fc.get('is_truncated'):
                    prompt_parts.append(f"[片段提取] {fc.get('summary', '')}")
                prompt_parts.append(fc.get('content', ''))
        else:
            # 若无法筛选出内容，提示AI基于结构与问题进行推理
            prompt_parts.append("\n未筛选到显著相关的文件片段，请基于项目结构与问题进行推理，并给出下一步建议（如需要我精读哪些文件）。")
        
        # 添加用户问题
        prompt_parts.append(f"\n用户问题: {user_message}")
        
        # 合并并做最终长度保护
        prompt = "\n".join(prompt_parts)
        if len(prompt) > MAX_PROMPT_CHARS:
            # 超长时，保留末尾用户问题与开头系统说明，截断中间上下文
            head = prompt_parts[0]
            tail = f"\n用户问题: {user_message}"
            prompt = f"{head}\n\n（上下文过长，已自动压缩）\n" + tail
        return prompt
    
    def send_to_ai(self, prompt: str):
        """发送消息给AI"""
        try:
            # 重置停止标志
            self.stop_ai_request = False
            
            # 显示思考动画
            self.show_thinking_animation()
            
            # 显示终止按钮，隐藏发送按钮
            self.send_button.pack_forget()
            self.stop_button.pack(side="right", padx=(10, 0))
            
            def ai_thread():
                try:
                    if not self.stop_ai_request:
                        response = self.chat_manager.send_message(prompt)
                        if not self.stop_ai_request:
                            self.after(0, lambda: self.on_ai_response(response))
                        else:
                            self.after(0, lambda: self.on_ai_stopped())
                except Exception as e:
                    # 任何异常都需要停止思考动画并给出失败提示
                    self.after(0, self.stop_thinking_animation)
                    if not self.stop_ai_request:
                        err_msg = str(e)
                        def _fail_ui():
                            self.show_toast(f"AI响应错误: {err_msg}", "error")
                            target_id = getattr(self, 'append_response_to_message_id', None)
                            if target_id:
                                self.update_message_content(target_id, f"\n\n[交互失败] {err_msg}", mode="append")
                                self.append_response_to_message_id = None
                            else:
                                self.add_message_to_display("assistant", f"[交互失败] {err_msg}")
                            self.reset_ui_state()
                        self.after(0, _fail_ui)
            
            self.ai_thread = threading.Thread(target=ai_thread, daemon=True)
            self.ai_thread.start()
        except Exception as e:
            # 外层异常同样需要停止思考动画并输出失败信息
            self.stop_thinking_animation()
            self.show_toast(f"发送失败: {str(e)}", "error")
            target_id = getattr(self, 'append_response_to_message_id', None)
            if target_id:
                self.update_message_content(target_id, f"\n\n[交互失败] {e}", mode="append")
                self.append_response_to_message_id = None
            else:
                self.add_message_to_display("assistant", f"[交互失败] {e}")
            self.reset_ui_state()
    
    def on_ai_response(self, response: str):
        """处理AI响应"""
        # 停止思考动画
        self.stop_thinking_animation()
        
        # 如果需要把回答连到某条消息后，则更新该消息；否则正常新增一条助手消息
        target_id = getattr(self, 'append_response_to_message_id', None)
        if target_id:
            # 追加格式：空行 + 回答标题 + 正文
            appended = "\n\n回答：\n" + response
            ok = self.update_message_content(target_id, appended, mode="append")
            # 清理标记
            self.append_response_to_message_id = None
            if not ok:
                # 兜底：追加失败则作为新消息加入
                self.add_message_to_display("assistant", response)
        else:
            # 添加AI响应
            self.add_message_to_display("assistant", response)
        
        # 恢复UI状态
        self.reset_ui_state()

    def parse_ai_suggestions(self, response: str):
        """解析AI建议中的文件操作"""
        # 这里可以添加解析AI响应的逻辑
        # 例如识别"打开文件"、"编辑文件"等建议
        pass
    
    # 文件和项目分析方法
    def set_project_path(self, project_path: str):
        """设置项目路径"""
        self.current_project_path = project_path
        project_name = os.path.basename(project_path) if project_path else "未选择项目"
        self.project_info_label.configure(text=f"项目: {project_name}")
        
        if project_path:
            self.show_toast(f"已切换到项目: {project_name}", "success")
    
    def set_current_file(self, file_path: str):
        """设置当前文件"""
        self.current_file_path = file_path
        if file_path:
            file_name = os.path.basename(file_path)
            self.show_toast(f"当前文件: {file_name}", "info")
            
    def get_open_files(self):
        """获取当前打开的文件列表"""
        open_files = []
        if self.current_file_path and os.path.exists(self.current_file_path):
            open_files.append(self.current_file_path)
        return open_files
    
    def set_callbacks(self, on_file_open: Callable[[str], None], on_file_edit: Callable[[str, str], None]):
        """设置回调函数"""
        self.on_file_open_request = on_file_open
        self.on_file_edit_request = on_file_edit
    
    def analyze_current_file(self):
        """分析当前文件"""
        if not self.current_file_path:
            self.show_toast("没有当前文件", "error")
            return
        
        self.analyze_file_with_ai(self.current_file_path)
    
    def analyze_file_with_ai(self, file_path: str):
        """使用AI分析文件"""
        if not os.path.exists(file_path):
            self.show_toast(f"文件不存在: {file_path}", "error")
            return
        
        def analyze_thread():
            try:
                # 读取文件内容
                self.after(0, lambda: self.update_progress("正在读取文件...", 0.2))
                
                # 断点管理器空值防护：不可用则直接读取全文
                if self.breakpoint_manager:
                    file_context = self.breakpoint_manager.get_context_for_ai(file_path)
                else:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            _content = f.read()
                        file_context = {
                            'content': _content,
                            'summary': f"完整文件内容 ({_content.count('\n') + 1} 行)",
                            'is_truncated': False
                        }
                    except Exception as _e:
                        self.after(0, lambda: self.show_toast(f"读取文件失败: {_e}", "error"))
                        file_context = {'content': '', 'summary': f"读取失败: {_e}"}
                
                self.after(0, lambda: self.update_progress("正在分析文件...", 0.5))
                
                # 构建分析提示
                analyze_prompt = f"""请分析以下文件的代码：

文件路径: {file_path}
{file_context.get('summary', '')}

文件内容:
{file_context.get('content', '')}

请提供以下分析：
1. 代码结构和功能概述
2. 代码质量评估
3. 潜在问题和改进建议
4. 代码风格和最佳实践建议

请使用中文回复，所有输出内容必须是中文。"""
                
                # 发送给AI
                response = self.chat_manager.send_message(analyze_prompt)
                
                self.after(0, lambda: self.update_progress("分析完成", 1.0))
                self.after(0, lambda: self.on_ai_response(response))
                
                # 保存文件上下文
                self.file_contexts[file_path] = file_context
                
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"分析文件失败: {e}", "error"))
                self.after(0, lambda: self.update_progress("分析失败", 0))
        
        threading.Thread(target=analyze_thread, daemon=True).start()
    
    def analyze_project_structure(self):
        """分析项目结构"""
        if not self.current_project_path:
            self.show_toast("没有选择项目", "error")
            return
        
        def analyze_thread():
            try:
                self.after(0, lambda: self.update_progress("正在分析项目结构...", 0.3))
                
                structure = self.get_project_structure_summary()
                
                # 构建分析提示
                analyze_prompt = f"""请分析以下项目结构：

项目路径: {self.current_project_path}
总文件数: {structure.get('total_files', 0)}
文件类型分布: {structure.get('file_types', {})}

请使用中文回复，所有输出内容必须是中文。"""
                
                self.after(0, lambda: self.update_progress("正在生成分析报告...", 0.7))
                
                response = self.chat_manager.send_message(analyze_prompt)
                
                self.after(0, lambda: self.update_progress("分析完成", 1.0))
                self.after(0, lambda: self.on_ai_response(response))
                
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"分析项目失败: {e}", "error"))
                self.after(0, lambda: self.update_progress("分析失败", 0))
        
        threading.Thread(target=analyze_thread, daemon=True).start()
    
    def get_project_structure_summary(self) -> Dict[str, Any]:
        """获取项目结构摘要"""
        structure = {
            'total_files': 0,
            'file_types': {},
            'directories': [],
            'main_files': []
        }
        
        try:
            for root, dirs, files in os.walk(self.current_project_path):
                # 跳过隐藏目录和常见的忽略目录
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', 'env']]
                
                rel_root = os.path.relpath(root, self.current_project_path)
                if rel_root != '.':
                    structure['directories'].append(rel_root)
                
                for file in files:
                    if file.startswith('.'):
                        continue
                    
                    structure['total_files'] += 1
                    
                    # 统计文件类型
                    ext = os.path.splitext(file)[1].lower()
                    structure['file_types'][ext] = structure['file_types'].get(ext, 0) + 1
                    
                    # 识别主要文件
                    if file in ['main.py', 'app.py', 'index.html', 'package.json', 'requirements.txt', 'README.md']:
                        file_path = os.path.join(rel_root, file) if rel_root != '.' else file
                        structure['main_files'].append(file_path)
        
        except Exception as e:
            structure['error'] = str(e)
        
        return structure
    
    def get_code_suggestions(self):
        """获取代码建议"""
        if not self.current_file_path:
            self.show_toast("没有当前文件", "error")
            return
        
        # 获取当前文件的上下文
        file_context = self.file_contexts.get(self.current_file_path)
        if not file_context:
            self.show_toast("请先分析当前文件", "error")
            return
        
        suggest_prompt = f"""基于之前分析的文件 {self.current_file_path}，请提供具体的代码改进建议：

1. 性能优化建议
2. 代码重构建议
3. 安全性改进
4. 可读性提升
5. 错误处理改进

请提供具体的代码示例和修改建议。请使用中文回复，所有输出内容必须是中文。"""
        
        self.add_message_to_display("user", "请提供代码改进建议")
        self.send_to_ai(suggest_prompt)
    
    def read_file_command(self, file_path: str):
        """读取文件命令"""
        if not file_path:
            self.show_toast("请指定文件路径", "error")
            return
        
        # 如果是相对路径，基于当前项目路径
        if not os.path.isabs(file_path) and self.current_project_path:
            file_path = os.path.join(self.current_project_path, file_path)
        
        self.read_file_with_progress(file_path)
    
    def analyze_file_command(self, file_path: str):
        """分析文件命令"""
        if not file_path:
            self.show_toast("请指定文件路径", "error")
            return
        
        # 如果是相对路径，基于当前项目路径
        if not os.path.isabs(file_path) and self.current_project_path:
            file_path = os.path.join(self.current_project_path, file_path)
        
        self.analyze_file_with_ai(file_path)
    
    def _read_full_file_context(self, file_path: str, batch_chunks: int = 10) -> Dict[str, Any]:
        """通过断点管理器分批次读取，直到完整读取整个文件内容。返回与
        BreakpointManager.read_file_with_breakpoints 相同结构的结果，但 content 为完整内容。"""
        try:
            # 断点管理器空值防护：不可用则直接读取全文
            if not self.breakpoint_manager:
                with open(file_path, 'r', encoding='utf-8') as f:
                    _content = f.read()
                _size = len(_content)
                return {
                    'success': True,
                    'content': _content,
                    'is_complete': True,
                    'progress': 100.0,
                    'file_info': {
                        'size': _size,
                        'lines': _content.count('\n') + 1,
                        'is_large_file': _size > 65536
                    }
                }
            # 无论文件大小，都重置断点状态，确保从头开始读取
            self.breakpoint_manager.reset_breakpoint(file_path)
            parts: list[str] = []
            last_progress = 0.0
            while True:
                res = self.breakpoint_manager.read_file_with_breakpoints(file_path, max_chunks=batch_chunks)
                if not res.get('success'):
                    return res
                piece = res.get('content', '')
                if piece:
                    parts.append(piece)
                prog = float(res.get('progress', 0.0))
                if prog > last_progress:
                    last_progress = prog
                    # 更新进度到 UI
                    self.after(0, lambda p=prog: self.update_progress(f"读取进度: {p:.1f}%", p / 100))
                if res.get('is_complete'):
                    final_content = ''.join(parts)
                    res.update({
                        'content': final_content,
                        'is_complete': True,
                        'progress': 100.0
                    })
                    return res
        except Exception as exc:
            return {'success': False, 'error': str(exc)}
    
    def read_file_with_progress(self, file_path: str):
        """带进度显示的文件读取"""
        def read_thread():
            try:
                self.after(0, lambda: self.update_progress("正在读取文件...", 0.1))
                
                # 通过批次读取确保完整内容
                result = self._read_full_file_context(file_path, batch_chunks=10)
                
                if result['success']:
                    self.after(0, lambda: self.update_progress(
                        f"读取进度: {result['progress']:.1f}%", 
                        result['progress'] / 100
                    ))
                    
                    # 显示文件内容
                    file_info = result['file_info']
                    content_preview = result['content'][:500] + "..." if len(result['content']) > 500 else result['content']
                    
                    message = f"""文件读取结果:
文件: {file_path}
大小: {file_info.get('size', 0)} 字节
{'已分块完整读取' if file_info.get('is_large_file') else '小文件完整读取'}

内容预览:
{content_preview}"""
                    
                    self.after(0, lambda: self.add_message_to_display("assistant", message))
                    self.after(0, lambda: self.show_toast(f"文件读取完成: {os.path.basename(file_path)}", "success"))
                    
                    # 保存文件上下文（完整内容）
                    self.file_contexts[file_path] = {
                        'content': result['content'],
                        'summary': f"文件读取 - {result['progress']:.1f}% 完成",
                        'is_truncated': False
                    }
                    
                else:
                    self.after(0, lambda: self.show_toast(f"读取文件失败: {result.get('error', '未知错误')}", "error"))
                
                self.after(0, lambda: self.update_progress("就绪", 0))
                
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"读取文件异常: {e}", "error"))
                self.after(0, lambda: self.update_progress("就绪", 0))
        
        threading.Thread(target=read_thread, daemon=True).start()
    
    def update_progress(self, text: str, progress: float):
        """更新进度显示"""
        self.progress_label.configure(text=text)
        self.progress_bar.set(progress)
    
    def hide_progress(self):
        """隐藏进度显示，复位为就绪"""
        try:
            self.update_progress("就绪", 0)
        except Exception:
            pass
    
    def cleanup_breakpoints(self):
        """清理断点"""
        def cleanup_thread():
            try:
                self.after(0, lambda: self.update_progress("正在清理断点...", 0.5))
                
                if self.breakpoint_manager:
                    self.breakpoint_manager.cleanup_old_breakpoints(max_age_days=7)
                    self.after(0, lambda: self.show_toast("断点清理完成", "success"))
                else:
                    self.after(0, lambda: self.show_toast("断点管理器不可用，已跳过清理", "warning"))
                
                self.after(0, lambda: self.update_progress("就绪", 0))
                
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"清理断点失败: {e}", "error"))
                self.after(0, lambda: self.update_progress("就绪", 0))
        
        threading.Thread(target=cleanup_thread, daemon=True).start()

    def show_file_selection_dialog(self, upload_to_model: bool = False):
        """显示文件选择对话框（兼容旧方法，委托到高级选择对话框）"""
        return self.show_project_files_selection(upload_to_model)
        tk.Label(
            header_frame, 
            text="请选择要分析的文件", 
            font=("Arial", 12, "bold"),
            bg="#f5f5f5"
        ).pack(side="left")
        
        # 文件列表框架
        list_frame = tk.Frame(dialog, bg="white")
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # 创建滚动条
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        # 创建文件列表
        file_list = tk.Listbox(
            list_frame,
            selectmode="multiple",
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            bg="white",
            bd=0
        )
        file_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=file_list.yview)
        
        # 文件选择变量和复选框
        file_vars = {}
        file_paths = []
        
        # 收集项目文件
        include_exts = {
            ".py", ".ipynb", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".txt",
            ".html", ".css", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf",
            ".xml", ".csv", ".tsv", ".sql", ".env", ".bat", ".ps1", ".sh",
            ".c", ".h", ".cpp", ".hpp", ".java", ".kt", ".go", ".rs", ".cs", ".rb", ".php"
        }
        
        dir_excludes = {"__pycache__", "node_modules", "venv", "env", ".git", ".svn", ".hg", ".idea", ".vscode", "dist", "build", "out", ".next"}
        
        # 收集文件
        for root, dirs, files in os.walk(self.current_project_path):
            dirs[:] = [d for d in dirs if d not in dir_excludes and not d.startswith('.')]
            for file in files:
                if file.startswith('.'):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in include_exts:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.current_project_path)
                    file_paths.append(full_path)
                    file_list.insert(tk.END, rel_path)
                    file_vars[rel_path] = full_path
        
        # 底部按钮框架
        button_frame = tk.Frame(dialog, bg="#f5f5f5")
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # 取消按钮
        tk.Button(
            button_frame,
            text="取消",
            command=dialog.destroy,
            bg="#f0f0f0",
            relief="flat",
            padx=15
        ).pack(side="right", padx=5)
        
        # 确定按钮
        def on_confirm():
            selected_indices = file_list.curselection()
            selected_files = [file_paths[i] for i in selected_indices]
            if selected_files:
                dialog.destroy()
                self.analyze_selected_files(selected_files, upload_to_model)
            else:
                self.show_toast("请至少选择一个文件", "warning")
        
        tk.Button(
            button_frame,
            text="分析选中文件",
            command=on_confirm,
            bg="#4CAF50",
            fg="white",
            relief="flat",
            padx=15
        ).pack(side="right", padx=5)
        
        # 全选按钮
        def select_all():
            file_list.selection_set(0, tk.END)
        
        tk.Button(
            button_frame,
            text="全选",
            command=select_all,
            bg="#f0f0f0",
            relief="flat",
            padx=15
        ).pack(side="left", padx=5)
        
        # 取消全选按钮
        def deselect_all():
            file_list.selection_clear(0, tk.END)
        
        tk.Button(
            button_frame,
            text="取消全选",
            command=deselect_all,
            bg="#f0f0f0",
            relief="flat",
            padx=15
        ).pack(side="left", padx=5)
    
    def analyze_selected_files(self, file_paths: list[str], upload_to_model: bool = False):
        """分析选中的文件
        
        Args:
            file_paths: 选中的文件路径列表
            upload_to_model: 是否将文件上传到模型
        """
        if not file_paths:
            self.show_toast("没有选择文件", "error")
            return
            
        # 清空当前文件上下文
        self.file_contexts = []
        
        # 显示进度
        self.update_progress(f"正在处理选中的 {len(file_paths)} 个文件...", 0.1)
        
        # 读取文件内容
        loaded_files = []
        skipped_files = []
        uploaded_files = []
        upload_errors = []
        total_size = 0
        max_size_per_file = 2 * 1024 * 1024  # 2MB
        
        for i, file_path in enumerate(file_paths):
            try:
                # 更新进度
                progress = 0.1 + 0.8 * (i / len(file_paths))
                self.update_progress(f"处理文件 {i+1}/{len(file_paths)}: {os.path.basename(file_path)}", progress)
                
                # 检查文件大小
                file_size = os.path.getsize(file_path)
                if file_size > max_size_per_file:
                    skipped_files.append((os.path.relpath(file_path, self.current_project_path), f"文件过大 ({file_size/1024/1024:.1f}MB)"))
                    continue
                    
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # 添加到文件上下文
                rel_path = os.path.relpath(file_path, self.current_project_path)
                self.file_contexts.append({
                    'path': rel_path,
                    'content': content,
                    'size': len(content)
                })
                
                loaded_files.append(rel_path)
                total_size += len(content)
                
                # 上传到模型
                if upload_to_model:
                    try:
                        # 上传文件内容
                        result = self.chat_manager.model_manager.upload_file_content(
                            content=content,
                            filename=os.path.basename(file_path),
                        )
                        uploaded_files.append((rel_path, result.get('id', 'unknown')))
                    except Exception as e:
                        upload_errors.append((rel_path, str(e)))
                
            except Exception as e:
                skipped_files.append((os.path.relpath(file_path, self.current_project_path), str(e)))
        
        # 完成进度
        self.update_progress("文件处理完成", 1.0)
        self.after(500, self.hide_progress)
        
        # 生成摘要
        summary = []
        summary.append(f"已加载 {len(loaded_files)} 个文件，总大小 {total_size/1024:.1f}KB")
        
        if skipped_files:
            summary.append(f"跳过 {len(skipped_files)} 个文件:")
            for path, reason in skipped_files[:5]:
                summary.append(f"- {path}: {reason}")
            if len(skipped_files) > 5:
                summary.append(f"- ... 等 {len(skipped_files) - 5} 个文件")
        
        if upload_to_model:
            if uploaded_files:
                summary.append(f"已上传 {len(uploaded_files)} 个文件到模型:")
                for path, file_id in uploaded_files[:5]:
                    summary.append(f"- {path}: ID={file_id}")
                if len(uploaded_files) > 5:
                    summary.append(f"- ... 等 {len(uploaded_files) - 5} 个文件")
            
            if upload_errors:
                summary.append(f"上传失败 {len(upload_errors)} 个文件:")
                for path, error in upload_errors[:5]:
                    summary.append(f"- {path}: {error}")
                if len(upload_errors) > 5:
                    summary.append(f"- ... 等 {len(upload_errors) - 5} 个文件")
        
        # 显示摘要
        summary_text = "\n".join(summary)
        self.show_toast(summary_text, "info", duration=10000)
        
        # 添加到聊天
        self.add_system_message(summary_text)
        
        # 如果有待处理的查询，自动发送
        if self.pending_query_after_readall:
            query = self.pending_query_after_readall
            self.pending_query_after_readall = None
            self.after(1000, lambda: self.send_message(query))
    
    def show_file_selection_dialog(self, upload_to_model: bool = False):
        return self.show_project_files_selection(upload_to_model)

        dialog.title("文件分析 - 选择文件")
        dialog.geometry("800x600")
        dialog.transient(self)
        dialog.grab_set()
        
        # 设置对话框样式
        dialog.configure(bg="#2b2b2b")
        
        # 创建标题标签
        title_label = tk.Label(dialog, text="选择要分析的文件", font=("Arial", 14), bg="#2b2b2b", fg="white")
        title_label.pack(pady=10)
        
        # 创建文件列表框架
        list_frame = tk.Frame(dialog, bg="#2b2b2b")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 创建滚动条
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建文件列表
        file_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, bg="#3c3f41", fg="white", 
                                 font=("Arial", 10), bd=0, highlightthickness=0,
                                 yscrollcommand=scrollbar.set)
        file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=file_listbox.yview)
        
        # 文件选择变量
        selected_files = []
        
        # 添加文件到列表
        include_exts = {
            ".py", ".ipynb", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".txt",
            ".html", ".css", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf",
            ".xml", ".csv", ".tsv", ".sql", ".env", ".bat", ".ps1", ".sh",
            ".c", ".h", ".cpp", ".hpp", ".java", ".kt", ".go", ".rs", ".cs", ".rb", ".php"
        }
        
        dir_excludes = {"__pycache__", "node_modules", "venv", "env", ".git", ".svn", ".hg", ".idea", ".vscode", "dist", "build", "out", ".next"}
        
        # 收集文件
        files_to_show = []
        for root, dirs, files in os.walk(self.current_project_path):
            dirs[:] = [d for d in dirs if d not in dir_excludes and not d.startswith('.')]
            for file in files:
                if file.startswith('.'):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in include_exts:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.current_project_path)
                    files_to_show.append((rel_path, file_path))
        
        # 按相对路径排序
        files_to_show.sort(key=lambda x: x[0])
        
        # 添加到列表框
        for rel_path, full_path in files_to_show:
            file_listbox.insert(tk.END, rel_path)
        
        # 创建按钮框架
        button_frame = tk.Frame(dialog, bg="#2b2b2b")
        button_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # 创建确认按钮
        def on_confirm():
            # 获取选中的文件
            selected_indices = file_listbox.curselection()
            selected_files.clear()
            for i in selected_indices:
                selected_files.append(files_to_show[i][1])  # 添加完整路径
            
            # 关闭对话框
            dialog.destroy()
            
            # 分析选中的文件
            if selected_files:
                self.analyze_selected_files(selected_files, upload_to_model)
            else:
                self.show_toast("未选择任何文件", "warning")
        
        confirm_button = tk.Button(button_frame, text="分析选中文件", command=on_confirm,
                                  bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
                                  relief=tk.FLAT, padx=15, pady=8)
        confirm_button.pack(side=tk.RIGHT, padx=5)
        
        # 创建取消按钮
        def on_cancel():
            dialog.destroy()
        
        cancel_button = tk.Button(button_frame, text="取消", command=on_cancel,
                                 bg="#f44336", fg="white", font=("Arial", 10),
                                 relief=tk.FLAT, padx=15, pady=8)
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # 创建全选按钮
        def select_all():
            file_listbox.selection_set(0, tk.END)
        
        select_all_button = tk.Button(button_frame, text="全选", command=select_all,
                                     bg="#2196F3", fg="white", font=("Arial", 10),
                                     relief=tk.FLAT, padx=15, pady=8)
        select_all_button.pack(side=tk.LEFT, padx=5)
        
        # 创建取消全选按钮
        def deselect_all():
            file_listbox.selection_clear(0, tk.END)
        
        deselect_all_button = tk.Button(button_frame, text="取消全选", command=deselect_all,
                                       bg="#607D8B", fg="white", font=("Arial", 10),
                                       relief=tk.FLAT, padx=15, pady=8)
        deselect_all_button.pack(side=tk.LEFT, padx=5)
        
        # 设置对话框居中
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # 显示对话框
        dialog.focus_set()
        
    def analyze_selected_files(self, file_paths, upload_to_model=False):
        """分析选中的文件"""
        if not file_paths:
            return
            
        def worker():
            try:
                self.after(0, lambda: self.update_progress(f"正在分析 {len(file_paths)} 个文件...", 0.1))
                
                # 清空当前文件上下文
                self.file_contexts = []
                
                # 读取文件内容
                loaded_files = []
                skipped_files = []
                uploaded_files = []
                upload_errors = []
                file_ids = []  # 存储上传文件的ID，用于批量处理
                total_size = 0
                max_size_per_file = 2 * 1024 * 1024  # 2MB
                
                # 第一阶段：读取和上传文件
                for i, file_path in enumerate(file_paths):
                    try:
                        # 更新进度
                        progress = 0.1 + 0.4 * (i / len(file_paths))
                        self.after(0, lambda p=progress, f=file_path: self.update_progress(
                            f"分析文件 {i+1}/{len(file_paths)}: {os.path.basename(f)}", p))
                        
                        # 检查文件大小
                        file_size = os.path.getsize(file_path)
                        if file_size > max_size_per_file:
                            rel_path = os.path.relpath(file_path, self.current_project_path)
                            skipped_files.append((rel_path, f"文件过大 ({file_size/1024/1024:.1f}MB > {max_size_per_file/1024/1024:.1f}MB)"))
                            continue
                        
                        # 读取文件内容
                        content = self._read_full_file_context(file_path)
                        if content:
                            # 添加到文件上下文
                            rel_path = os.path.relpath(file_path, self.current_project_path)
                            self.file_contexts.append({
                                'path': rel_path,
                                'content': content,
                                'size': len(content)
                            })
                            loaded_files.append(rel_path)
                            total_size += len(content)
                            
                            # 上传到模型
                            if upload_to_model:
                                try:
                                    # 更新进度信息
                                    self.after(0, lambda f=file_path: self.update_progress(
                                        f"上传文件: {os.path.basename(f)}", progress))
                                    
                                    # 上传文件内容
                                    result = self.chat_manager.model_manager.upload_file_content(
                                        content=content,
                                        filename=os.path.basename(file_path),
                                    )
                                    file_id = result.get('id')
                                    if file_id:
                                        file_ids.append(file_id)
                                        uploaded_files.append((rel_path, file_id))
                                    else:
                                        upload_errors.append((rel_path, "上传成功但未返回文件ID"))
                                except Exception as e:
                                    upload_errors.append((rel_path, str(e)))
                        else:
                            rel_path = os.path.relpath(file_path, self.current_project_path)
                            skipped_files.append((rel_path, "无法读取文件内容"))
                    except Exception as e:
                        rel_path = os.path.relpath(file_path, self.current_project_path)
                        skipped_files.append((rel_path, str(e)))
                
                # 第二阶段：如果有上传的文件，创建批处理任务
                batch_info = None
                if upload_to_model and file_ids:
                    try:
                        self.after(0, lambda: self.update_progress("创建批处理任务...", 0.6))
                        batch_info = self.chat_manager.model_manager.create_batch(file_ids)
                        
                        # 等待批处理任务完成
                        batch_id = batch_info.get('id')
                        if batch_id:
                            max_checks = 10
                            for check in range(max_checks):
                                progress = 0.6 + 0.3 * (check / max_checks)
                                self.after(0, lambda p=progress: self.update_progress(
                                    f"等待批处理任务完成 ({check+1}/{max_checks})...", p))
                                
                                # 等待一段时间
                                time.sleep(1)
                                
                                # 检查批处理任务状态
                                try:
                                    batch_status = self.chat_manager.model_manager.get_batch(batch_id)
                                    status = batch_status.get('status')
                                    
                                    if status == 'completed':
                                        self.after(0, lambda: self.update_progress(
                                            "批处理任务已完成", 0.9))
                                        break
                                    elif status in ['failed', 'cancelled']:
                                        self.after(0, lambda: self.update_progress(
                                            f"批处理任务失败: {status}", 0.9))
                                        break
                                except Exception as e:
                                    # 检查状态失败，但继续等待
                                    pass
                    except Exception as e:
                        self.after(0, lambda: self.show_toast(f"创建批处理任务失败: {str(e)}", "error"))
                
                # 更新进度
                self.after(0, lambda: self.update_progress("生成分析摘要...", 0.95))
                
                # 生成摘要
                summary = f"已加载 {len(loaded_files)} 个文件，总大小 {total_size/1024:.1f}KB"
                if skipped_files:
                    summary += f"，跳过 {len(skipped_files)} 个文件"
                
                # 添加上传信息
                if upload_to_model:
                    if uploaded_files:
                        summary += f"\n已上传 {len(uploaded_files)} 个文件到模型"
                        if batch_info and batch_info.get('id'):
                            summary += f"\n批处理任务ID: {batch_info.get('id')}"
                    else:
                        summary += "\n警告：没有文件被上传到模型"
                
                # 显示摘要
                self.after(0, lambda: self.show_toast(summary, "info", duration=5000))
                
                # 添加摘要消息
                message_id = str(uuid.uuid4())
                message = {
                    "id": message_id,
                    "role": "assistant",
                    "content": f"📁 **文件分析摘要**\n\n{summary}\n\n"
                }
                
                # 添加已加载文件列表
                if loaded_files:
                    message["content"] += "**已加载文件：**\n"
                    for file in loaded_files[:10]:  # 只显示前10个
                        message["content"] += f"- `{file}`\n"
                    if len(loaded_files) > 10:
                        message["content"] += f"- ... 等共 {len(loaded_files)} 个文件\n"
                    message["content"] += "\n"
                
                # 添加已上传文件列表
                if uploaded_files:
                    message["content"] += "**已上传文件：**\n"
                    for file, file_id in uploaded_files[:10]:  # 只显示前10个
                        message["content"] += f"- `{file}` (ID: {file_id})\n"
                    if len(uploaded_files) > 10:
                        message["content"] += f"- ... 等共 {len(uploaded_files)} 个文件\n"
                    message["content"] += "\n"
                    
                    # 添加批处理任务信息
                    if batch_info and batch_info.get('id'):
                        message["content"] += f"**批处理任务：**\n- ID: {batch_info.get('id')}\n- 状态: {batch_info.get('status', '未知')}\n\n"
                
                # 添加跳过文件列表
                if skipped_files:
                    message["content"] += "**跳过文件：**\n"
                    for file, reason in skipped_files[:10]:  # 只显示前10个
                        message["content"] += f"- `{file}`: {reason}\n"
                    if len(skipped_files) > 10:
                        message["content"] += f"- ... 等共 {len(skipped_files)} 个文件\n"
                
                # 添加上传错误列表
                if upload_errors:
                    message["content"] += "\n**上传错误：**\n"
                    for file, error in upload_errors[:10]:  # 只显示前10个
                        message["content"] += f"- `{file}`: {error}\n"
                    if len(upload_errors) > 10:
                        message["content"] += f"- ... 等共 {len(upload_errors)} 个错误\n"
                
                # 添加消息
                self.after(0, lambda: self.add_message(message))
                self.last_readall_summary_message_id = message_id
                
                # 隐藏进度条
                self.after(0, self.hide_progress)
                
                # 如果有待处理的查询，自动提问
                if self.pending_query_after_readall:
                    query = self.pending_query_after_readall
                    self.pending_query_after_readall = None
                    self.after(0, lambda: self.send_message(query))
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"分析文件时出错: {str(e)}", "error"))
                self.after(0, self.hide_progress)
        
        # 启动工作线程
        threading.Thread(target=worker, daemon=True).start()
        
    def read_all_project_files(self, include_exts: set | None = None, max_files: int = 2000,
                               max_size_per_file: int = 5 * 1024 * 1024, total_size_limit: int = 100 * 1024 * 1024,
                               upload_to_model: bool = False):
        """批量读取项目中的代码文件到上下文，避免一次性读取过多导致卡顿
        - include_exts: 要读取的文件后缀集合（默认常见代码/文本类型）
        - max_files: 最多读取文件数
        - max_size_per_file: 单文件最大字节数（超过则使用分块并标记为截断）
        - total_size_limit: 读取总大小上限
        - upload_to_model: 是否将文件内容上传到大模型（通过文件上传API）
        """
        if not self.current_project_path or not os.path.exists(self.current_project_path):
            self.show_toast("没有选择项目", "error")
            return
        
        if include_exts is None:
            include_exts = {
                ".py", ".ipynb", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".txt",
                ".html", ".css", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf",
                ".xml", ".csv", ".tsv", ".sql", ".env", ".bat", ".ps1", ".sh",
                ".c", ".h", ".cpp", ".hpp", ".java", ".kt", ".go", ".rs", ".cs", ".rb", ".php"
            }
        
        def worker():
            try:
                self.after(0, lambda: self.update_progress("正在扫描项目文件...", 0.1))
                dir_excludes = {"__pycache__", "node_modules", "venv", "env", ".git", ".svn", ".hg", ".idea", ".vscode", "dist", "build", "out", ".next"}
                files_to_read: list[str] = []
                total_size_est = 0
                
                # 收集候选文件
                for root, dirs, files in os.walk(self.current_project_path):
                    dirs[:] = [d for d in dirs if d not in dir_excludes and not d.startswith('.')]
                    for file in files:
                        if file.startswith('.'):
                            continue
                        ext = os.path.splitext(file)[1].lower()
                        if ext not in include_exts:
                            continue
                        path = os.path.join(root, file)
                        try:
                            size = os.path.getsize(path)
                        except Exception:
                            size = 0
                        files_to_read.append(path)
                        total_size_est += size
                        if len(files_to_read) >= max_files or total_size_est >= total_size_limit:
                            break
                    if len(files_to_read) >= max_files or total_size_est >= total_size_limit:
                        break
                
                if not files_to_read:
                    self.after(0, lambda: self.show_toast("没有可读取的代码文件", "warning"))
                    return
                
                self.after(0, lambda: self.update_progress(f"准备读取 {len(files_to_read)} 个文件...", 0.2))
                loaded = 0
                skipped = 0
                loaded_bytes = 0
                skipped_files = []  # 收集跳过的文件信息
                
                for idx, path in enumerate(files_to_read, start=1):
                    # 读取文件（分批确保完整读取）
                    try:
                        result = self._read_full_file_context(path, batch_chunks=10)
                        if result.get('success'):
                            file_info = result.get('file_info', {})
                            content = result.get('content', '')
                            size = int(file_info.get('size', 0))
                            loaded_bytes += size
                            rel_path = os.path.relpath(path, self.current_project_path)
                            # 保存到上下文（完整内容）
                            self.file_contexts[path] = {
                                'content': content,
                                'is_truncated': False,
                                'summary': f"文件完整读取，大小 {size} 字节",
                                'size': size,
                                'relative_path': rel_path
                            }
                            loaded += 1
                        else:
                            skipped += 1
                            rel_path = os.path.relpath(path, self.current_project_path)
                            error_msg = result.get('error', '未知错误')
                            skipped_files.append({
                                'path': rel_path,
                                'reason': error_msg
                            })
                    except Exception as e:
                        skipped += 1
                        rel_path = os.path.relpath(path, self.current_project_path)
                        skipped_files.append({
                            'path': rel_path,
                            'reason': f"异常: {str(e)}"
                        })
                    
                    # 进度更新
                    progress = 0.2 + 0.7 * (idx / len(files_to_read))
                    self.after(0, lambda p=progress: self.update_progress("正在读取项目文件...", p))
                
                # 如果需要上传到模型，执行上传操作
                uploaded_files = []
                if upload_to_model:
                    self.after(0, lambda: self.update_progress("正在上传文件到大模型...", 0.9))
                    
                    # 获取当前模型配置
                    model = None
                    if hasattr(self, 'chat_manager') and hasattr(self.chat_manager, 'model_manager'):
                        model_id = getattr(self.chat_manager, 'current_model_id', None)
                        if model_id:
                            model = self.chat_manager.model_manager.get_model(model_id)
                    
                    if not model:
                        self.after(0, lambda: self.show_toast("无法获取当前模型配置，上传失败", "error"))
                    else:
                        # 上传文件内容
                        try:
                            for path, file_info in self.file_contexts.items():
                                if len(uploaded_files) >= 10:  # 限制上传文件数量
                                    break
                                
                                content = file_info.get('content', '')
                                if not content:
                                    continue
                                
                                rel_path = file_info.get('relative_path', os.path.basename(path))
                                try:
                                    # 上传文件内容
                                    result = self.chat_manager.model_manager.upload_file_content(
                                        model, 
                                        content, 
                                        rel_path, 
                                        purpose="assistants"
                                    )
                                    uploaded_files.append({
                                        'path': rel_path,
                                        'file_id': result.get('id', ''),
                                        'size': file_info.get('size', 0)
                                    })
                                except Exception as e:
                                    self.after(0, lambda: self.show_toast(f"文件上传失败: {e}", "error"))
                        except Exception as e:
                            self.after(0, lambda: self.show_toast(f"文件上传过程出错: {e}", "error"))
                
                # 汇总输出
                summary = f"读取完成：共选取 {len(files_to_read)} 个文件，成功 {loaded}，跳过 {skipped}，累计 {loaded_bytes} 字节。\n"
                
                # 如果有跳过的文件，添加详细信息
                if skipped_files:
                    summary += "\n**跳过的文件详情：**\n"
                    for skip_info in skipped_files:
                        summary += f"- `{skip_info['path']}`: {skip_info['reason']}\n"
                    summary += "\n"
                
                # 如果上传了文件，添加上传信息
                if uploaded_files:
                    summary += "\n**上传到大模型的文件：**\n"
                    for file_info in uploaded_files:
                        summary += f"- `{file_info['path']}`: 文件ID {file_info['file_id']}\n"
                    summary += "\n"
                
                summary += "提示：可通过 /read <相对路径> 精读某文件，或 /analyze <相对路径> 进行深入分析。"
                if not uploaded_files and upload_to_model:
                    summary += "\n\n**注意：** 文件上传失败或未上传任何文件。请检查模型配置或重试。"
                
                # 将总结消息加入并记录其 message_id，用于稍后把AI回答追加到同一条消息
                self.after(0, lambda: self._add_readall_summary(summary))
                self.after(0, lambda: self.show_toast("项目文件读取完成", "success"))
                self.after(0, lambda: self.update_progress("读取完成", 1.0))
                # 如果用户在 /readall 后附带了问题，则在读取完成后自动发起该问题的回答（连着显示在总结后）
                self.after(0, self._maybe_ask_follow_up_after_readall)
            except Exception as e:
                self.after(0, lambda: self.show_toast(f"批量读取失败: {e}", "error"))
                self.after(0, lambda: self.update_progress("读取失败", 0))
        
        threading.Thread(target=worker, daemon=True).start()

    def _add_readall_summary(self, summary: str):
        """添加 /readall 总结消息并记录其ID。"""
        msg_id = self.add_message_to_display("assistant", summary)
        self.last_readall_summary_message_id = msg_id

    def _maybe_ask_follow_up_after_readall(self):
        """
        在 /readall 完成后，如果存在用户的追问，则直接把回答连到总结消息后显示。
        """
        try:
            # 若用户已点击“终止”，不再触发自动追问
            if getattr(self, "stop_ai_request", False):
                return
            query = getattr(self, "pending_query_after_readall", None)
            # 清空挂起的追问，避免重复触发
            self.pending_query_after_readall = None
            if not query or not isinstance(query, str) or not query.strip():
                return
            query = query.strip()
            # 构建上下文并发送给 AI，同时指定把响应追加到总结消息
            context_info = self.build_context_info()
            prompt = self.build_ai_prompt(query, context_info)
            # 标记需要把AI回答追加到总结消息
            self.append_response_to_message_id = getattr(self, 'last_readall_summary_message_id', None)
            self.send_to_ai(prompt)
        except Exception as e:
            # 提示错误但不影响主流程
            self.show_toast(f"自动追问发送失败: {e}", "error")

    def on_ai_response(self, response: str):
        """处理AI响应"""
        # 停止思考动画
        self.stop_thinking_animation()
        
        # 如果需要把回答连到某条消息后，则更新该消息；否则正常新增一条助手消息
        target_id = getattr(self, 'append_response_to_message_id', None)
        if target_id:
            # 追加格式：空行 + 回答标题 + 正文
            appended = "\n\n回答：\n" + response
            ok = self.update_message_content(target_id, appended, mode="append")
            # 清理标记
            self.append_response_to_message_id = None
            if not ok:
                # 兜底：追加失败则作为新消息加入
                self.add_message_to_display("assistant", response)
        else:
            # 添加AI响应
            self.add_message_to_display("assistant", response)
        
        # 恢复UI状态
        self.reset_ui_state()

    def update_message_content(self, message_id: str, new_content: str, mode: str = "replace"):
        """更新指定消息的文本内容。mode 可选值：'replace' 或 'append'。"""
        try:
            for msg_info in self.message_components:
                if msg_info.get('message_id') == message_id:
                    content_text = msg_info.get('content_text')
                    old_text = msg_info.get('content', '')
                    if mode == "append":
                        merged = old_text + new_content
                    else:
                        merged = new_content
                    if content_text:
                        content_text.configure(state="normal")
                        if mode == "append":
                            content_text.insert("end", new_content)
                        else:
                            content_text.delete("1.0", "end")
                            content_text.insert("1.0", new_content)
                        # 重新应用Markdown格式
                        self._apply_markdown_formatting(content_text, merged)
                        # 保持normal状态以允许选择和复制，事件绑定已在创建时设置
                        # 调整高度
                        content_text.update_idletasks()
                        line_count = int(content_text.index('end-1c').split('.')[0])
                        content_text.configure(height=min(line_count, 60))
                    msg_info['content'] = merged
                    # 同步到 self.messages
                    for msg in self.messages:
                        if msg['id'] == message_id:
                            msg['content'] = merged
                            break
                    return True
        except Exception:
            pass
        return False

