"""
文件交互功能 - 显示项目已打开文件选择对话框
"""
import os
import tkinter as tk
from tkinter import filedialog
import threading


def add_show_project_files_selection(ai_code_assistant):
    """为AICodeAssistant类添加show_project_files_selection方法和analyze_selected_files方法"""
    
    def handle_large_project(self, proj_path):
        """处理大型项目，只添加项目文件夹标签而不加载所有文件"""
        # 添加项目文件夹标签
        if hasattr(self, "add_project_folder_tag"):
            # 使用项目文件夹名称作为标签
            folder_name = os.path.basename(proj_path)
            self.add_project_folder_tag(folder_name, proj_path)
            self.show_toast(f"已添加项目 {folder_name}", "success")
        return
    
    def show_project_files_selection(self, upload_to_model=False):
        """显示项目文件选择对话框（仅使用高级 FileSelectionDialog）"""
        # 若尚未设置项目路径，先让用户选择项目根目录
        if not getattr(self, "current_project_path", None):
            try:
                parent_window = self.winfo_toplevel() if hasattr(self, "winfo_toplevel") else None
                start_dir = getattr(self, "current_project_path", None) or os.getcwd()
                folder = filedialog.askdirectory(title="选择项目根目录", parent=parent_window, initialdir=start_dir) if parent_window else filedialog.askdirectory(title="选择项目根目录", initialdir=start_dir)
            except Exception:
                start_dir = getattr(self, "current_project_path", None) or os.getcwd()
                folder = filedialog.askdirectory(title="选择项目根目录", initialdir=start_dir)
            if folder:
                if hasattr(self, "set_project_path"):
                    try:
                        self.set_project_path(folder)
                    except Exception:
                        self.current_project_path = folder
                else:
                    self.current_project_path = folder
            else:
                self.show_toast("请先打开一个项目", "warning")
                return
        
        # 获取项目路径
        proj_path = self.current_project_path
        
        # 检查是否有多选文件（通过文件浏览器右键菜单选择的文件）
        selected_files = getattr(self, "_selected_files_for_analysis", None)
        
        # 如果用户没有从文件浏览器选择文件，则默认使用当前项目文件夹
        if not selected_files:
            # 直接使用当前项目文件夹，并在标签栏中添加项目文件夹标签
            folder_name = os.path.basename(proj_path)
            self.add_project_folder_tag(folder_name, proj_path)
            self.selected_files_for_interaction = [proj_path]
            self.show_toast(f"已添加项目文件夹: {folder_name}", "success")
            return
        
        # 如果有多选文件，直接处理这些文件
        if selected_files and len(selected_files) > 0:
            try:
                # 添加文件标签
                self.add_file_tags(selected_files)
                # 清空多选文件列表，避免影响下次操作
                self._selected_files_for_analysis = []
                # 注释掉重复的项目文件夹标签添加，避免重复显示
                # if hasattr(self, "add_project_folder_tag"):
                #     for file_path in selected_files:
                #         # 获取文件名或文件夹名作为标签
                #         tag_name = os.path.basename(file_path)
                #         self.add_project_folder_tag(tag_name, file_path)
            except Exception as ex:
                self.show_toast(f"添加文件标签失败: {ex}", "error")
            return
        
        # 如果没有多选文件，默认只处理项目文件夹
        try:
            # 直接调用大型项目处理方法
            self.handle_large_project(proj_path)
        except Exception as e:
            self.show_toast(f"上传项目文件失败: {e}", "error")
            
        # 延迟导入以避免循环依赖
        try:
            from ..ui.file_selection_dialog import FileSelectionDialog
        except Exception as e:
            self.show_toast(f"加载文件选择对话框失败: {e}", "error")
            return
        
        def on_files_selected(selected_files):
            if selected_files:
                try:
                    self.add_file_tags(selected_files)
                except Exception as ex:
                    self.show_toast(f"添加文件标签失败: {ex}", "error")
            else:
                self.show_toast("未选择任何文件", "warning")
        
        parent_window = self.winfo_toplevel() if hasattr(self, "winfo_toplevel") else self
        try:
            dialog = FileSelectionDialog(
                parent=parent_window,
                project_path=proj_path,
                on_confirm=on_files_selected
            )
            dialog.show()
        except Exception as e:
            self.show_toast(f"显示文件选择对话框失败: {e}", "error")
    
    # 添加analyze_selected_files方法
    def analyze_selected_files(self, file_paths, upload_to_model=False, question=""):
        """分析选定的文件
        
        Args:
            file_paths: 文件路径列表
            upload_to_model: 是否上传到模型
            question: 用户输入的问题
        """
        if not file_paths:
            self.show_toast("没有选择文件", "warning")
            return
            
        # 显示进度条
        self.update_progress("正在处理选定的文件...", 0.1)
        
        def worker():
            try:
                # 读取文件内容
                loaded_files = []
                uploaded_files = []
                skipped_files = []
                upload_errors = []
                
                total_files = len(file_paths)
                for i, file_path in enumerate(file_paths):
                    try:
                        # 更新进度
                        progress = 0.1 + 0.8 * (i / total_files)
                        self.update_progress(f"正在处理 {os.path.basename(file_path)}...", progress)
                        
                        # 读取文件内容
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                            content = f.read()
                            
                        # 添加到上下文
                        rel_path = os.path.relpath(file_path, self.current_project_path)
                        self.file_contexts[rel_path] = content
                        loaded_files.append(rel_path)
                        
                        # 上传到模型
                        if upload_to_model:
                            # 这里假设有upload_file方法，如果没有可以跳过
                            if hasattr(self, 'upload_file'):
                                file_id = self.upload_file(file_path)
                                if file_id:
                                    uploaded_files.append((rel_path, file_id))
                                else:
                                    upload_errors.append((rel_path, "上传失败"))
                    except Exception as e:
                        skipped_files.append((os.path.basename(file_path), str(e)))
                
                # 更新进度
                self.update_progress("生成摘要...", 0.9)
                
                # 生成摘要消息
                message = {
                    "role": "system",
                    "content": f"## 文件分析摘要\n\n"
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
                
                # 添加用户问题
                if question:
                    # 发送系统消息
                    self.send_message(message["content"], is_system=True)
                    # 发送用户问题
                    self.send_message(question)
                else:
                    # 只发送系统消息
                    self.send_message(message["content"], is_system=True)
                
                # 隐藏进度条
                self.update_progress("", 0)
                
            except Exception as ex:
                self.show_toast(f"分析文件时出错: {str(ex)}", "error")
                self.update_progress("", 0)
        
        # 启动工作线程
        threading.Thread(target=worker, daemon=True).start()
    
    # 为类添加方法（直接赋值，避免错误绑定）
    ai_code_assistant.show_project_files_selection = show_project_files_selection
    ai_code_assistant.analyze_selected_files = analyze_selected_files
    
    # 修改原有的show_file_selection_dialog方法，使其调用新方法
    if hasattr(ai_code_assistant, 'show_file_selection_dialog'):
        original_method = ai_code_assistant.show_file_selection_dialog
    else:
        original_method = None
    
    def show_file_selection_dialog_wrapper(self, upload_to_model=False):
        """显示文件选择对话框（为了兼容性保留，直接调用新方法）"""
        return self.show_project_files_selection(upload_to_model)
    
    ai_code_assistant.show_file_selection_dialog = show_file_selection_dialog_wrapper


    # 添加一个辅助方法来判断文件是否支持
    def is_supported_file(self, file_path):
        """判断文件是否为支持的类型"""
        supported_extensions = {
            '.py', '.js', '.ts', '.html', '.css', '.scss', '.less',
            '.json', '.xml', '.yaml', '.yml', '.md', '.txt', '.rst',
            '.c', '.cpp', '.h', '.hpp', '.java', '.cs', '.php',
            '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
            '.sql', '.sh', '.bat', '.ps1', '.dockerfile', '.gitignore'
        }
        ext = os.path.splitext(file_path)[1].lower()
        return ext in supported_extensions