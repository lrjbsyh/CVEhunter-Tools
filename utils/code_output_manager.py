"""
代码输出管理器
处理代码执行、输出显示和结果管理
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import threading
import time
import os
import sys
import signal
from typing import Dict, List, Optional, Any, Callable
import queue
import json
from pathlib import Path
from utils.notification_system import show_info, show_success, show_warning, show_error
import re


class CodeExecutionResult:
    """代码执行结果"""
    
    def __init__(self):
        self.start_time = time.time()
        self.end_time = None
        self.return_code = None
        self.stdout = ""
        self.stderr = ""
        self.execution_time = 0
        self.command = ""
        self.working_directory = ""
        self.process = None
        self.is_running = False
        self.is_cancelled = False
    
    def finish(self, return_code: int, stdout: str, stderr: str):
        """完成执行"""
        self.end_time = time.time()
        self.execution_time = self.end_time - self.start_time
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        self.is_running = False
    
    def cancel(self):
        """取消执行"""
        self.is_cancelled = True
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
            except:
                pass
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'execution_time': self.execution_time,
            'return_code': self.return_code,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'command': self.command,
            'working_directory': self.working_directory,
            'is_running': self.is_running,
            'is_cancelled': self.is_cancelled
        }


class CodeOutputManager(ctk.CTkFrame):
    """代码输出管理器组件"""
    
    def __init__(self, parent, minimal_ui: bool = False, **kwargs):
        super().__init__(parent, **kwargs)
        
        # 是否使用精简UI
        self.minimal_ui = minimal_ui
        
        # 自动滚动控制（默认开启，可由外部关闭）
        self.auto_scroll = True
        
        # 执行历史
        self.execution_history: List[CodeExecutionResult] = []
        self.current_execution: Optional[CodeExecutionResult] = None
        
        # 输出队列
        self.output_queue = queue.Queue()
        
        # 回调函数
        self.on_execution_complete: Optional[Callable[[CodeExecutionResult], None]] = None
        
        # 创建UI
        self.create_widgets()
        
        # 启动输出处理线程
        self.start_output_processor()
    
    def create_widgets(self):
        """创建UI组件"""
        if self.minimal_ui:
            # 精简模式：仅一个输出文本框，支持右键菜单与彩色输出
            self.output_text = ctk.CTkTextbox(
                self,
                font=ctk.CTkFont(family="Consolas", size=12),
                wrap="word"
            )
            self.output_text.pack(fill="both", expand=True, padx=5, pady=5)
            # 精简模式不使用错误/历史/标题栏
            self.error_text = None
            self.notebook = None
            self.status_label = None
            self.time_label = None
            self.stop_btn = None
            self.clear_btn = None
            self.save_btn = None
            # 右键菜单
            self.create_context_menu()
            return
        
        # 标题栏
        title_frame = ctk.CTkFrame(self)
        title_frame.pack(fill="x", padx=5, pady=5)
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="🖥️ 代码执行输出",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(side="left", padx=10, pady=5)
        
        # 控制按钮
        self.stop_btn = ctk.CTkButton(
            title_frame,
            text="⏹️ 停止",
            command=self.stop_execution,
            width=80,
            state="disabled"
        )
        self.stop_btn.pack(side="right", padx=5, pady=5)
        
        self.clear_btn = ctk.CTkButton(
            title_frame,
            text="🧹 清空",
            command=self.clear_output,
            width=80
        )
        self.clear_btn.pack(side="right", padx=5, pady=5)
        
        self.save_btn = ctk.CTkButton(
            title_frame,
            text="💾 保存",
            command=self.save_output,
            width=80
        )
        self.save_btn.pack(side="right", padx=5, pady=5)
        
        # 执行信息栏
        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=5, pady=5)
        
        self.status_label = ctk.CTkLabel(
            info_frame,
            text="就绪",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(side="left", padx=10, pady=5)
        
        self.time_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.time_label.pack(side="right", padx=10, pady=5)
        
        # 选项卡
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 输出选项卡
        self.output_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(self.output_frame, text="输出")
        
        self.output_text = ctk.CTkTextbox(
            self.output_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word"
        )
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 错误选项卡
        self.error_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(self.error_frame, text="错误")
        
        self.error_text = ctk.CTkTextbox(
            self.error_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word"
        )
        self.error_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 历史选项卡
        self.history_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(self.history_frame, text="历史")
        
        # 历史列表
        history_list_frame = ctk.CTkFrame(self.history_frame)
        history_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 创建Treeview用于显示历史
        columns = ("时间", "命令", "状态", "耗时")
        self.history_tree = ttk.Treeview(
            history_list_frame,
            columns=columns,
            show="headings",
            height=10
        )
        
        # 设置列标题
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=100)
        
        # 滚动条
        history_scrollbar = ttk.Scrollbar(
            history_list_frame,
            orient="vertical",
            command=self.history_tree.yview
        )
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)
        
        self.history_tree.pack(side="left", fill="both", expand=True)
        history_scrollbar.pack(side="right", fill="y")
        
        # 绑定历史选择事件
        self.history_tree.bind("<<TreeviewSelect>>", self.on_history_select)
        
        # 历史详情
        history_detail_frame = ctk.CTkFrame(self.history_frame)
        history_detail_frame.pack(fill="x", padx=5, pady=5)
        
        self.history_detail_text = ctk.CTkTextbox(
            history_detail_frame,
            height=100,
            font=ctk.CTkFont(family="Consolas", size=10)
        )
        self.history_detail_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 右键菜单
        self.create_context_menu()
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="复制", command=self.copy_output)
        self.context_menu.add_command(label="全选", command=self.select_all_output)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="清空输出", command=self.clear_output)
        self.context_menu.add_command(label="保存输出", command=self.save_output)
        
        # 绑定右键菜单
        self.output_text.bind("<Button-3>", self.show_context_menu)
        if self.error_text:
            self.error_text.bind("<Button-3>", self.show_context_menu)
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def copy_output(self):
        """复制输出"""
        try:
            # 支持精简UI：仅有一个输出文本框
            if getattr(self, "minimal_ui", False) or not getattr(self, "notebook", None):
                try:
                    selected_text = self.output_text.selection_get()
                except tk.TclError:
                    selected_text = self.output_text.get("1.0", "end").strip()
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                return

            # 标准UI：根据当前选项卡复制
            current_tab = self.notebook.index(self.notebook.select())
            if current_tab == 0:  # 输出选项卡
                try:
                    selected_text = self.output_text.selection_get()
                except tk.TclError:
                    selected_text = self.output_text.get("1.0", "end").strip()
            elif current_tab == 1:  # 错误选项卡
                try:
                    selected_text = self.error_text.selection_get()
                except tk.TclError:
                    selected_text = self.error_text.get("1.0", "end").strip()
            else:
                return

            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except Exception:
            # 安全兜底：复制输出文本框全部内容
            try:
                text = self.output_text.get("1.0", "end").strip()
                self.clipboard_clear()
                self.clipboard_append(text)
            except Exception:
                pass
    
    def select_all_output(self):
        """全选输出"""
        if self.minimal_ui:
            self.output_text.tag_add("sel", "1.0", "end")
            return
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # 输出选项卡
            self.output_text.tag_add("sel", "1.0", "end")
        elif current_tab == 1:  # 错误选项卡
            self.error_text.tag_add("sel", "1.0", "end")
    
    def start_output_processor(self):
        """启动输出处理线程"""
        def process_output():
            while True:
                try:
                    item = self.output_queue.get(timeout=0.1)
                    if item is None:  # 退出信号
                        break
                    
                    output_type, content = item
                    self.after(0, lambda t=output_type, c=content: self.append_output(t, c))
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"输出处理错误: {e}")
        
        self.output_thread = threading.Thread(target=process_output, daemon=True)
        self.output_thread.start()
    
    def append_output(self, output_type: str, content: str):
        """添加输出内容"""
        if self.minimal_ui:
            self._insert_ansi(self.output_text, content, is_error=(output_type == "stderr"))
            if getattr(self, "auto_scroll", True):
                try:
                    self.output_text.see("end")
                except Exception:
                    pass
            return
        if output_type == "stdout":
            self._insert_ansi(self.output_text, content, is_error=False)
            if getattr(self, "auto_scroll", True):
                try:
                    self.output_text.see("end")
                except Exception:
                    pass
        elif output_type == "stderr":
            self._insert_ansi(self.error_text, content, is_error=True)
            if getattr(self, "auto_scroll", True):
                try:
                    self.error_text.see("end")
                except Exception:
                    pass
            # 如果有错误，切换到错误选项卡
            if self.notebook:
                try:
                    self.notebook.select(1)
                except Exception:
                    pass
    
    def execute_code(self, command: str, working_directory: str = None, env: Dict[str, str] = None) -> CodeExecutionResult:
        """执行代码"""
        if self.current_execution and self.current_execution.is_running:
            show_warning("警告", "已有代码在执行中，请先停止当前执行")
            return None
        
        # 创建执行结果对象
        result = CodeExecutionResult()
        result.command = command
        result.working_directory = working_directory or os.getcwd()
        result.is_running = True
        
        self.current_execution = result
        
        # 更新UI状态
        if self.status_label:
            self.status_label.configure(text="正在执行...")
        if self.stop_btn:
            self.stop_btn.configure(state="normal")
        self.clear_output()
        
        # 在后台线程中执行
        def execute_thread():
            try:
                # 准备环境
                exec_env = os.environ.copy()
                if env:
                    exec_env.update(env)
                
                # 启动进程
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=result.working_directory,
                    env=exec_env,
                    bufsize=1,
                    universal_newlines=True
                )
                
                result.process = process
                
                # 实时读取输出
                stdout_lines = []
                stderr_lines = []
                
                def read_stdout():
                    for line in iter(process.stdout.readline, ''):
                        if result.is_cancelled:
                            break
                        stdout_lines.append(line)
                        self.output_queue.put(("stdout", line))
                    process.stdout.close()
                
                def read_stderr():
                    for line in iter(process.stderr.readline, ''):
                        if result.is_cancelled:
                            break
                        stderr_lines.append(line)
                        self.output_queue.put(("stderr", line))
                    process.stderr.close()
                
                # 启动读取线程
                stdout_thread = threading.Thread(target=read_stdout, daemon=True)
                stderr_thread = threading.Thread(target=read_stderr, daemon=True)
                
                stdout_thread.start()
                stderr_thread.start()
                
                # 等待进程完成
                return_code = process.wait()
                
                # 等待读取线程完成
                stdout_thread.join(timeout=1)
                stderr_thread.join(timeout=1)
                
                # 完成执行
                stdout_text = ''.join(stdout_lines)
                stderr_text = ''.join(stderr_lines)
                
                result.finish(return_code, stdout_text, stderr_text)
                
                # 更新UI
                self.after(0, lambda: self.on_execution_finished(result))
                
            except Exception as e:
                result.finish(-1, "", str(e))
                self.after(0, lambda: self.on_execution_finished(result))
        
        # 启动执行线程
        threading.Thread(target=execute_thread, daemon=True).start()
        
        return result
    
    def execute_python_code(self, code: str, working_directory: str = None) -> CodeExecutionResult:
        """执行Python代码"""
        # 创建临时文件
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # 执行Python文件
            command = f'python "{temp_file}"'
            result = self.execute_code(command, working_directory)
            
            # 设置清理回调
            if result:
                original_finish = result.finish
                def cleanup_finish(*args, **kwargs):
                    original_finish(*args, **kwargs)
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
                result.finish = cleanup_finish
            
            return result
            
        except Exception as e:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except:
                pass
            raise e
    
    def execute_file(self, file_path: str, working_directory: str = None) -> CodeExecutionResult:
        """执行文件"""
        if not os.path.exists(file_path):
            show_error("错误", f"文件不存在: {file_path}")
            return None
        
        # 根据文件扩展名确定执行命令
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.py':
            command = f'python "{file_path}"'
        elif ext == '.js':
            command = f'node "{file_path}"'
        elif ext == '.bat':
            command = f'"{file_path}"'
        elif ext == '.ps1':
            command = f'powershell -ExecutionPolicy Bypass -File "{file_path}"'
        else:
            # 尝试直接执行
            command = f'"{file_path}"'
        
        return self.execute_code(command, working_directory)
    
    def stop_execution(self):
        """停止执行"""
        if self.current_execution and self.current_execution.is_running:
            self.current_execution.cancel()
            if self.status_label:
                self.status_label.configure(text="已取消")
            if self.stop_btn:
                self.stop_btn.configure(state="disabled")
    
    def on_execution_finished(self, result: CodeExecutionResult):
        """执行完成回调"""
        # 更新UI状态
        if self.status_label:
            if result.is_cancelled:
                status_text = "已取消"
            elif result.return_code == 0:
                status_text = "执行成功"
            else:
                status_text = f"执行失败 (退出码: {result.return_code})"
            self.status_label.configure(text=status_text)
        if self.time_label:
            self.time_label.configure(text=f"耗时: {result.execution_time:.2f}s")
        if self.stop_btn:
            self.stop_btn.configure(state="disabled")
        
        # 添加到历史（精简模式也记录，但不显示）
        self.execution_history.append(result)
        if not self.minimal_ui:
            self.update_history_display()
        
        # 调用回调函数
        if self.on_execution_complete:
            self.on_execution_complete(result)
        
        self.current_execution = None
    
    def update_history_display(self):
        """更新历史显示"""
        # 清空现有项目
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # 添加历史项目
        for i, result in enumerate(reversed(self.execution_history[-50:])):  # 只显示最近50个
            start_time = time.strftime("%H:%M:%S", time.localtime(result.start_time))
            command = result.command[:50] + "..." if len(result.command) > 50 else result.command
            
            if result.is_cancelled:
                status = "已取消"
            elif result.return_code == 0:
                status = "成功"
            else:
                status = f"失败({result.return_code})"
            
            execution_time = f"{result.execution_time:.2f}s"
            
            self.history_tree.insert(
                "",
                "end",
                values=(start_time, command, status, execution_time),
                tags=(str(len(self.execution_history) - 1 - i),)
            )
    
    def on_history_select(self, event):
        """历史选择事件"""
        selection = self.history_tree.selection()
        if not selection:
            return
        
        item = self.history_tree.item(selection[0])
        if not item['tags']:
            return
        
        history_index = int(item['tags'][0])
        if 0 <= history_index < len(self.execution_history):
            result = self.execution_history[history_index]
            self.show_history_detail(result)
    
    def show_history_detail(self, result: CodeExecutionResult):
        """显示历史详情"""
        detail_text = f"""命令: {result.command}
工作目录: {result.working_directory}
开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result.start_time))}
结束时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result.end_time)) if result.end_time else '未完成'}
执行时间: {result.execution_time:.2f}秒
退出码: {result.return_code}
状态: {'已取消' if result.is_cancelled else ('成功' if result.return_code == 0 else '失败')}

标准输出:
{result.stdout}

错误输出:
{result.stderr}
"""
        
        self.history_detail_text.delete("1.0", "end")
        self.history_detail_text.insert("1.0", detail_text)
    
    def clear_output(self):
        """清空输出"""
        self.output_text.delete("1.0", "end")
        if self.error_text:
            self.error_text.delete("1.0", "end")
    
    def save_output(self):
        """保存输出"""
        file_path = filedialog.asksaveasfilename(
            title="保存输出",
            defaultextension=".txt",
            filetypes=[
                ("文本文件", "*.txt"),
                ("日志文件", "*.log"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("=== 标准/错误输出 ===\n")
                    f.write(self.output_text.get("1.0", "end"))
                    if not self.minimal_ui and self.error_text:
                        f.write("\n=== 错误输出 ===\n")
                        f.write(self.error_text.get("1.0", "end"))
                show_success("成功", "输出已保存")
            except Exception as e:
                show_error("错误", f"保存失败: {e}")
    
    def get_current_output(self) -> Dict[str, str]:
        """获取当前输出"""
        return {
            'stdout': self.output_text.get("1.0", "end"),
            'stderr': self.error_text.get("1.0", "end")
        }
    
    def set_execution_callback(self, callback: Callable[[CodeExecutionResult], None]):
        """设置执行完成回调"""
        self.on_execution_complete = callback

    def set_auto_scroll(self, enabled: bool):
        """设置是否自动滚动到最新输出"""
        try:
            self.auto_scroll = bool(enabled)
        except Exception:
            self.auto_scroll = True

    def _insert_ansi(self, ctktb: Any, content: str, is_error: bool = False):
        """支持ANSI颜色的插入，如果底层文本控件支持tag则应用颜色"""
        # 获取底层tk.Text（customtkinter的CTkTextbox通常包含 textbox/_textbox）
        text_widget = getattr(ctktb, "textbox", None) or getattr(ctktb, "_textbox", None)
        if text_widget is None:
            # 无法获取底层文本控件，普通插入
            ctktb.insert("end", content)
            return
        
        # 在解析ANSI前，应用SQLmap原版颜色规则（SQLmap在非TTY时不会输出ANSI）
        try:
            content = self._apply_sqlmap_color_rules(content)
        except Exception:
            pass
        
        # 初始化颜色tag
        self._ensure_ansi_tags(text_widget)
        
        # 解析ANSI序列
        segments = self._parse_ansi_segments(content)
        current_tags = []
        if is_error:
            current_tags.append("ansi_red")
        for text, tags in segments:
            # 合并当前tags
            apply_tags = list(set(current_tags + tags))
            text_widget.insert("end", text, apply_tags)
        
    def _ensure_ansi_tags(self, text_widget: tk.Text):
        if getattr(text_widget, "_ansi_tags_inited", False):
            return
        # 前景色映射（使用Tk标准色，贴近SQLmap默认终端色）
        fg_colors = {
            "ansi_default": "#e5e7eb",
            "ansi_black": "black",
            "ansi_red": "red",
            "ansi_green": "green",
            "ansi_yellow": "yellow",
            "ansi_blue": "blue",
            "ansi_magenta": "magenta",
            "ansi_cyan": "cyan",
            "ansi_white": "white",
            "ansi_bright_black": "gray50",
            "ansi_bright_red": "tomato",
            "ansi_bright_green": "spring green",
            "ansi_bright_yellow": "gold",
            "ansi_bright_blue": "dodger blue",
            "ansi_bright_magenta": "violet",
            "ansi_bright_cyan": "turquoise",
            "ansi_bright_white": "snow",
        }
        for tag, color in fg_colors.items():
            try:
                text_widget.tag_configure(tag, foreground=color)
            except Exception:
                pass
        # 背景色映射
        bg_colors = {
            "ansi_bg_black": "black",
            "ansi_bg_red": "red",
            "ansi_bg_green": "green",
            "ansi_bg_yellow": "yellow",
            "ansi_bg_blue": "blue",
            "ansi_bg_magenta": "magenta",
            "ansi_bg_cyan": "cyan",
            "ansi_bg_white": "white",
        }
        for tag, color in bg_colors.items():
            try:
                text_widget.tag_configure(tag, background=color)
            except Exception:
                pass
        # 样式tag
        try:
            text_widget.tag_configure("ansi_bold", font=("Consolas", 12, "bold"))
        except Exception:
            pass
        try:
            text_widget.tag_configure("ansi_underline", underline=True)
        except Exception:
            pass
        setattr(text_widget, "_ansi_tags_inited", True)

    def _apply_sqlmap_color_rules(self, s: str) -> str:
        """按SQLmap段落级规则着色：
        - 给时间段(`[HH:MM:SS]`)着青色
        - 给日志级别(`[INFO]`, `[WARNING]` 等)按级别着色
        - 给计数段(`[#1]`)着黄色
        - 非 PAYLOAD 行，给单引号内内容着白色（跳过包含 `Payload:` 的行）
        - 若输入已含ANSI序列，则不重复着色
        """
        try:
            import re
        except Exception:
            return s
        # 若已有ANSI，直接返回
        if "\x1b[" in s:
            return s
        # 颜色码映射
        fg_code = {"black":30,"red":31,"green":32,"yellow":33,"blue":34,"magenta":35,"cyan":36,"white":37}
        bg_code = {"black":40,"red":41,"green":42,"yellow":43,"blue":44,"magenta":45,"cyan":46,"white":47}
        level_map = {
            "DEBUG": (None, "blue", False),
            "INFO": (None, "green", False),
            "WARNING": (None, "yellow", False),
            "ERROR": (None, "red", False),
            "CRITICAL": ("red", "white", False),
            # 自定义级别：与 sqlmap/lib/core/log.py 保持一致
            "PAYLOAD": (None, "cyan", False),
            "TRAFFIC OUT": (None, "magenta", False),
            "TRAFFIC IN": ("magenta", None, False),
        }
        def wrap_params(bg, fg, bold):
            params = []
            if bg is not None:
                params.append(str(bg_code[bg]))
            if fg is not None:
                params.append(str(fg_code[fg]))
            if bold:
                params.append("1")
            return "\x1b[" + ";".join(params) + "m" if params else ""
        out_lines = []
        for line in s.splitlines(True):  # 保留换行
            prefix_match = re.match(r"^(\s+)", line)
            prefix = prefix_match.group(1) if prefix_match else ""
            msg = line[len(prefix):]
            lvl_match = re.search(r"\[([A-Z ]+)\]", msg)
            if lvl_match:
                level_name = lvl_match.group(1)
                # 着色级别名（仅括号内文本）
                if level_name in level_map:
                    start, end = lvl_match.span(1)
                    bg, fg, bold = level_map[level_name]
                    start_seq = wrap_params(bg, fg, bold)
                    reset = "\x1b[0m"
                    msg = msg[:start] + start_seq + level_name + reset + msg[end:]
                # 时间段着青色
                time_match = re.match(r"^\s*\[([\d:]+)\]", msg)
                if time_match:
                    tstart, tend = time_match.span(1)
                    msg = msg[:tstart] + "\x1b[36m" + time_match.group(1) + "\x1b[0m" + msg[tend:]
                # 计数段着黄色
                for cm in re.finditer(r"\[(#\d+)\]", msg):
                    cstart, cend = cm.span(1)
                    msg = msg[:cstart] + "\x1b[33m" + cm.group(1) + "\x1b[0m" + msg[cend:]
                # 引号内部着白（跳过Payload行）
                if level_name != "PAYLOAD" and "Payload:" not in msg:
                    for qm in re.finditer(r"[^\w]'([^'\n]+)'", msg):
                        inner = qm.group(1)
                        # 仅替换一次以避免重复位置错乱
                        msg = msg.replace("'%s'" % inner, "'\x1b[37m%s\x1b[0m'" % inner, 1)
            else:
                # banner 简单启发式整体着黄
                if "___" in msg or "__H__" in msg or "V..." in msg:
                    msg = "\x1b[33m" + msg + "\x1b[0m"
            out_lines.append(prefix + msg)
        return "".join(out_lines)
        
    def _parse_ansi_segments(self, s: str) -> List[tuple]:
        """ANSI序列解析，支持前景/背景色、粗体和下划线"""
        segments: List[tuple] = []
        i = 0
        buf = []
        active_tags: List[str] = ["ansi_default"]
        
        fg_tags = {
            "ansi_black", "ansi_red", "ansi_green", "ansi_yellow", "ansi_blue", "ansi_magenta", "ansi_cyan", "ansi_white",
            "ansi_bright_black", "ansi_bright_red", "ansi_bright_green", "ansi_bright_yellow", "ansi_bright_blue", "ansi_bright_magenta", "ansi_bright_cyan", "ansi_bright_white"
        }
        bg_tags = {
            "ansi_bg_black", "ansi_bg_red", "ansi_bg_green", "ansi_bg_yellow", "ansi_bg_blue", "ansi_bg_magenta", "ansi_bg_cyan", "ansi_bg_white"
        }
        
        def flush_buf():
            nonlocal buf, segments, active_tags
            if buf:
                segments.append((''.join(buf), active_tags.copy()))
                buf.clear()
        
        while i < len(s):
            ch = s[i]
            if ch == "\x1b" and i + 1 < len(s) and s[i+1] == "[":
                flush_buf()
                i += 2
                params = []
                num = ""
                while i < len(s) and s[i] != "m":
                    if s[i].isdigit():
                        num += s[i]
                    elif s[i] == ";":
                        if num:
                            params.append(int(num)); num = ""
                    i += 1
                if num:
                    params.append(int(num))
                if not params:
                    params = [0]
                for code in params:
                    if code == 0:
                        # 重置所有样式
                        active_tags = ["ansi_default"]
                    elif code == 1:
                        if "ansi_bold" not in active_tags:
                            active_tags.append("ansi_bold")
                    elif code == 4:
                        if "ansi_underline" not in active_tags:
                            active_tags.append("ansi_underline")
                    elif 30 <= code <= 37:
                        # 前景色
                        active_tags = [t for t in active_tags if t not in fg_tags] + [
                            {
                                30: "ansi_black", 31: "ansi_red", 32: "ansi_green", 33: "ansi_yellow",
                                34: "ansi_blue", 35: "ansi_magenta", 36: "ansi_cyan", 37: "ansi_white",
                            }[code]
                        ]
                    elif 90 <= code <= 97:
                        # 亮前景色
                        active_tags = [t for t in active_tags if t not in fg_tags] + [
                            {
                                90: "ansi_bright_black", 91: "ansi_bright_red", 92: "ansi_bright_green", 93: "ansi_bright_yellow",
                                94: "ansi_bright_blue", 95: "ansi_bright_magenta", 96: "ansi_bright_cyan", 97: "ansi_bright_white",
                            }[code]
                        ]
                    elif code == 39:
                        # 默认前景色
                        active_tags = [t for t in active_tags if t not in fg_tags] + ["ansi_default"]
                    elif 40 <= code <= 47:
                        # 背景色
                        # 先移除已有背景色
                        active_tags = [t for t in active_tags if t not in bg_tags]
                        active_tags.append({
                            40: "ansi_bg_black", 41: "ansi_bg_red", 42: "ansi_bg_green", 43: "ansi_bg_yellow",
                            44: "ansi_bg_blue", 45: "ansi_bg_magenta", 46: "ansi_bg_cyan", 47: "ansi_bg_white",
                        }[code])
                    elif 100 <= code <= 107:
                        # 亮背景色（映射到同色背景）
                        active_tags = [t for t in active_tags if t not in bg_tags]
                        active_tags.append({
                            100: "ansi_bg_black", 101: "ansi_bg_red", 102: "ansi_bg_green", 103: "ansi_bg_yellow",
                            104: "ansi_bg_blue", 105: "ansi_bg_magenta", 106: "ansi_bg_cyan", 107: "ansi_bg_white",
                        }[code])
                    elif code == 49:
                        # 默认背景色
                        active_tags = [t for t in active_tags if t not in bg_tags]
                    else:
                        # 其他SGR忽略
                        pass
                i += 1
            else:
                buf.append(ch)
                i += 1
        flush_buf()
        return segments


if __name__ == "__main__":
    # 测试代码
    root = ctk.CTk()
    root.title("代码输出管理器测试")
    root.geometry("800x600")
    
    output_manager = CodeOutputManager(root)
    output_manager.pack(fill="both", expand=True)
    
    # 测试按钮
    test_frame = ctk.CTkFrame(root)
    test_frame.pack(fill="x", padx=5, pady=5)
    
    def test_python():
        code = """
print("Hello, World!")
import time
for i in range(5):
    print(f"计数: {i}")
    time.sleep(0.5)
print("完成!")
"""
        output_manager.execute_python_code(code)
    
    def test_command():
        output_manager.execute_code("dir" if os.name == 'nt' else "ls -la")
    
    ctk.CTkButton(test_frame, text="测试Python代码", command=test_python).pack(side="left", padx=5)
    ctk.CTkButton(test_frame, text="测试命令", command=test_command).pack(side="left", padx=5)
    
    root.mainloop()

    def _insert_ansi(self, ctktb: Any, content: str, is_error: bool = False):
        """支持ANSI颜色的插入，如果底层文本控件支持tag则应用颜色"""
        # 获取底层tk.Text（customtkinter的CTkTextbox通常包含 textbox/_textbox）
        text_widget = getattr(ctktb, "textbox", None) or getattr(ctktb, "_textbox", None)
        if text_widget is None:
            # 无法获取底层文本控件，普通插入
            ctktb.insert("end", content)
            return
        
        # 初始化颜色tag
        self._ensure_ansi_tags(text_widget)
        
        # 解析ANSI序列
        segments = self._parse_ansi_segments(content)
        current_tags = []
        if is_error:
            current_tags.append("ansi_red")
        for text, tags in segments:
            # 合并当前tags
            apply_tags = list(set(current_tags + tags))
            text_widget.insert("end", text, apply_tags)
        
    def _ensure_ansi_tags(self, text_widget: tk.Text):
        if getattr(text_widget, "_ansi_tags_inited", False):
            return
        # 颜色映射（暗色主题）
        colors = {
            "ansi_default": "#e5e7eb",  # 默认前景
            "ansi_black": "#000000",
            "ansi_red": "#ef4444",
            "ansi_green": "#10b981",
            "ansi_yellow": "#f59e0b",
            "ansi_blue": "#3b82f6",
            "ansi_magenta": "#a855f7",
            "ansi_cyan": "#06b6d4",
            "ansi_white": "#ffffff",
            "ansi_bright_black": "#4b5563",
            "ansi_bright_red": "#f87171",
            "ansi_bright_green": "#34d399",
            "ansi_bright_yellow": "#fbbf24",
            "ansi_bright_blue": "#60a5fa",
            "ansi_bright_magenta": "#c084fc",
            "ansi_bright_cyan": "#22d3ee",
            "ansi_bright_white": "#f3f4f6",
        }
        for tag, color in colors.items():
            try:
                text_widget.tag_configure(tag, foreground=color)
            except Exception:
                pass
        # 样式tag
        try:
            text_widget.tag_configure("ansi_bold", font=("Consolas", 12, "bold"))
            text_widget.tag_configure("ansi_dim", foreground="#9ca3af")
        except Exception:
            pass
        # 背景与基础样式
        try:
            text_widget.configure(bg="#1f2937")
        except Exception:
            pass
        setattr(text_widget, "_ansi_tags_inited", True)
        
    def _parse_ansi_segments(self, s: str) -> List[tuple]:
        """将包含ANSI颜色序列的字符串拆分为(文本, tags)段"""
        segments: List[tuple] = []
        i = 0
        buf = []
        active_tags: List[str] = []
        def flush_buf():
            if buf:
                segments.append((''.join(buf), active_tags.copy()))
                buf.clear()
        while i < len(s):
            if s[i] == "\x1b" and i + 1 < len(s) and s[i+1] == "[":
                # 终端转义序列
                j = i + 2
                while j < len(s) and s[j] != 'm':
                    j += 1
                if j < len(s) and s[j] == 'm':
                    params = s[i+2:j]
                    flush_buf()
                    # 处理参数
                    for p in (params.split(';') if params else ['0']):
                        try:
                            code = int(p)
                        except ValueError:
                            code = 0
                        if code == 0:
                            active_tags = []
                        elif code == 1:
                            if "ansi_bold" not in active_tags:
                                active_tags.append("ansi_bold")
                        elif code == 2:
                            if "ansi_dim" not in active_tags:
                                active_tags.append("ansi_dim")
                        elif 30 <= code <= 37:
                            color_tags = [t for t in active_tags if t.startswith("ansi_") and not t.startswith("ansi_bold") and not t.startswith("ansi_dim")]
                            # 移除已有前景色标签
                            for t in color_tags:
                                try:
                                    active_tags.remove(t)
                                except ValueError:
                                    pass
                            mapping = {
                                30: "ansi_black", 31: "ansi_red", 32: "ansi_green", 33: "ansi_yellow",
                                34: "ansi_blue", 35: "ansi_magenta", 36: "ansi_cyan", 37: "ansi_white",
                            }
                            active_tags.append(mapping.get(code, "ansi_default"))
                        elif 90 <= code <= 97:
                            for t in [t for t in active_tags if t.startswith("ansi_") and not t.startswith("ansi_bold") and not t.startswith("ansi_dim")]:
                                try:
                                    active_tags.remove(t)
                                except ValueError:
                                    pass
                            mapping = {
                                90: "ansi_bright_black", 91: "ansi_bright_red", 92: "ansi_bright_green", 93: "ansi_bright_yellow",
                                94: "ansi_bright_blue", 95: "ansi_bright_magenta", 96: "ansi_bright_cyan", 97: "ansi_bright_white",
                            }
                            active_tags.append(mapping.get(code, "ansi_default"))
                        elif code == 39:  # 默认前景
                            for t in [t for t in active_tags if t.startswith("ansi_") and not t.startswith("ansi_bold") and not t.startswith("ansi_dim")]:
                                try:
                                    active_tags.remove(t)
                                except ValueError:
                                    pass
                        else:
                            # 未处理的样式码直接忽略
                            pass
                    i = j + 1
                    continue
            buf.append(s[i])
            i += 1
        flush_buf()
        return segments


if __name__ == "__main__":
    # 测试代码
    root = ctk.CTk()
    root.title("代码输出管理器测试")
    root.geometry("800x600")
    
    output_manager = CodeOutputManager(root)
    output_manager.pack(fill="both", expand=True)
    
    # 测试按钮
    test_frame = ctk.CTkFrame(root)
    test_frame.pack(fill="x", padx=5, pady=5)
    
    def test_python():
        code = """
print("Hello, World!")
import time
for i in range(5):
    print(f"计数: {i}")
    time.sleep(0.5)
print("完成!")
"""
        output_manager.execute_python_code(code)
    
    def test_command():
        output_manager.execute_code("dir" if os.name == 'nt' else "ls -la")
    
    ctk.CTkButton(test_frame, text="测试Python代码", command=test_python).pack(side="left", padx=5)
    ctk.CTkButton(test_frame, text="测试命令", command=test_command).pack(side="left", padx=5)
    
    root.mainloop()

    def _apply_sqlmap_color_rules(self, s: str) -> str:
        """在非TTY场景下按SQLmap原版规则为整行日志着色：
        - 规则来源：sqlmap/thirdparty/ansistrm/ansistrm.py 的 ColorizingStreamHandler.level_map
        - 只为标准日志级别的整行着色（DEBUG/INFO/WARNING/ERROR/CRITICAL），不额外给时间/计数/引号内容上色
        - Banner行做保守高亮，其他保持默认
        """
        try:
            import re as _re
        except Exception:
            return s
        
        # 与 ansistrm.py 一致的级别映射
        level_map = {
            "DEBUG": (None, "blue", False),
            "INFO": (None, "green", False),
            "WARNING": (None, "yellow", False),
            "ERROR": (None, "red", False),
            "CRITICAL": ("red", "white", False),
        }
        fg_code = {"black":30,"red":31,"green":32,"yellow":33,"blue":34,"magenta":35,"cyan":36,"white":37}
        bg_code = {"black":40,"red":41,"green":42,"yellow":43,"blue":44,"magenta":45,"cyan":46,"white":47}
        
        def wrap_line(bg: str | None, fg: str | None, bold: bool, line: str) -> str:
            params: List[str] = []
            if bg is not None:
                params.append(str(bg_code[bg]))
            if fg is not None:
                params.append(str(fg_code[fg]))
            if bold:
                params.append("1")
            if params:
                return "\x1b[" + ";".join(params) + "m" + line + "\x1b[0m"
            else:
                return line
        
        out: List[str] = []
        for line in s.splitlines(True):  # 保留换行符
            m = _re.search(r"\[([A-Z]+)\]")
            if m:
                lvl = m.group(1)
                if lvl in level_map:
                    bg, fg, bold = level_map[lvl]
                    out.append(wrap_line(bg, fg, bold, line))
                else:
                    out.append(line)
            else:
                # banner行的简单启发式：含有典型ASCII图案则整体黄
                if "___" in line or "__H__" in line or "V..." in line:
                    out.append("\x1b[33m" + line + "\x1b[0m")
                else:
                    out.append(line)
        return "".join(out)