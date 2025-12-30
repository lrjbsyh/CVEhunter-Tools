"""
模型管理窗口模块
提供完整的AI模型管理界面，包括增删改查功能
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
from typing import Dict, Optional
from pathlib import Path
from managers.model_manager import AIModelManager
from managers.settings_manager import SettingsManager
from utils.notification_system import show_info, show_success, show_warning, show_error, show_confirm


class ModelDialog(ctk.CTkToplevel):
    """模型添加/编辑对话框"""
    
    def __init__(self, parent, model_manager: AIModelManager, model_data=None):
        super().__init__(parent)
        self.model_manager = model_manager
        self.model_data = model_data
        self.result = None
        
        self.setup_window()
        self.create_widgets()
        
        if model_data:
            self.load_model_data()
        
        # 设置模态
        self.transient(parent)
        self.grab_set()
        
        # 居中显示
        self.geometry("520x700")
        self.center_window()
    
    def setup_window(self):
        """设置窗口"""
        title = "编辑模型" if self.model_data else "添加AI模型"
        self.title(title)
        self.resizable(True, True)
        self.minsize(500, 650)
        # 同步应用图标
        try:
            icon_path = Path(__file__).parent.parent / 'assets' / 'icon.ico'
            if icon_path.exists():
                self.iconbitmap(default=str(icon_path))
            else:
                png_path = Path(__file__).parent.parent / 'assets' / 'icon.png'
                if png_path.exists():
                    img = tk.PhotoImage(file=str(png_path))
                    self.iconphoto(False, img)
                    self._icon_img_ref = img
        except Exception:
            pass
    
    def center_window(self):
        """窗口居中"""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (520 // 2)
        y = (self.winfo_screenheight() // 2) - (700 // 2)
        self.geometry(f"520x700+{x}+{y}")
    
    def create_widgets(self):
        """创建界面元素"""
        # 主框架
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 标题
        title_text = "编辑模型" if self.model_data else "添加AI模型"
        title_label = ctk.CTkLabel(main_frame, text=title_text, font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=(20, 30))
        
        # 滚动框架
        self.scroll_frame = ctk.CTkScrollableFrame(main_frame)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # 供应商
        ctk.CTkLabel(self.scroll_frame, text="供应商:", font=ctk.CTkFont(size=14)).pack(anchor="w", pady=(10, 5))
        self.provider_entry = ctk.CTkEntry(self.scroll_frame, height=35, placeholder_text="如：硅基流动、OpenAI等")
        self.provider_entry.pack(fill="x", pady=(0, 15))
        
        # API文档
        ctk.CTkLabel(self.scroll_frame, text="API文档:", font=ctk.CTkFont(size=14)).pack(anchor="w", pady=(0, 5))
        self.api_url_entry = ctk.CTkEntry(self.scroll_frame, height=35, placeholder_text="如：https://api.siliconflow.cn/v1")
        self.api_url_entry.pack(fill="x", pady=(0, 15))
        
        # 模型名称
        ctk.CTkLabel(self.scroll_frame, text="模型名称:", font=ctk.CTkFont(size=14)).pack(anchor="w", pady=(0, 5))
        self.model_name_entry = ctk.CTkEntry(self.scroll_frame, height=35, placeholder_text="如：deepseek-ai/DeepSeek-R1-0528-Qwen3-8B")
        self.model_name_entry.pack(fill="x", pady=(0, 15))
        
        # API Key
        ctk.CTkLabel(self.scroll_frame, text="API Key:", font=ctk.CTkFont(size=14)).pack(anchor="w", pady=(0, 5))
        self.api_key_entry = ctk.CTkEntry(self.scroll_frame, height=35, placeholder_text="输入您的API密钥", show="*")
        self.api_key_entry.pack(fill="x", pady=(0, 15))
        
        # 显示/隐藏API Key按钮
        self.show_key_var = ctk.BooleanVar()
        self.show_key_checkbox = ctk.CTkCheckBox(self.scroll_frame, text="显示API Key", variable=self.show_key_var, command=self.toggle_api_key_visibility)
        self.show_key_checkbox.pack(anchor="w", pady=(0, 20))
        
        # 按钮框架
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # 测试连接按钮
        self.test_button = ctk.CTkButton(button_frame, text="测试连接", command=self.test_connection)
        self.test_button.pack(side="left", padx=(10, 5), pady=10)
        
        # 取消按钮
        cancel_button = ctk.CTkButton(button_frame, text="取消", command=self.cancel)
        cancel_button.pack(side="right", padx=(5, 10), pady=10)
        
        # 确定按钮
        ok_button = ctk.CTkButton(button_frame, text="确定", command=self.ok)
        ok_button.pack(side="right", padx=(5, 5), pady=10)
    
    def toggle_api_key_visibility(self):
        """切换API Key显示/隐藏"""
        if self.show_key_var.get():
            self.api_key_entry.configure(show="")
        else:
            self.api_key_entry.configure(show="*")
    
    def load_model_data(self):
        """加载模型数据到表单"""
        if self.model_data:
            self.provider_entry.insert(0, self.model_data.get("provider", ""))
            
            # 处理API URL显示（兼容是否带尾部斜杠）
            api_url = self.model_data.get("api_url", "")
            if api_url.endswith("/chat/completions") or api_url.endswith("/chat/completions/"):
                # 去掉末尾的"/chat/completions"（以及可能的尾部斜杠）
                api_url = api_url[: api_url.rfind("/chat/completions")]
            self.api_url_entry.insert(0, api_url)
            
            self.model_name_entry.insert(0, self.model_data.get("model_name", ""))
            self.api_key_entry.insert(0, self.model_data.get("api_key", ""))
    
    def get_form_data(self) -> Dict:
        """获取表单数据"""
        provider = self.provider_entry.get().strip()
        api_url = self.api_url_entry.get().strip()
        model_name = self.model_name_entry.get().strip()
        api_key = self.api_key_entry.get().strip()
        
        # 自动补全API URL，规范化，优先确保 /v1/chat/completions
        if api_url:
            api_url = api_url.rstrip("/")
            has_v1 = "/v1" in api_url
            has_cc = "/chat/completions" in api_url
            if not has_cc:
                if not has_v1:
                    api_url = f"{api_url}/v1/chat/completions"
                else:
                    api_url = f"{api_url}/chat/completions"
        
        # 自动生成显示名称（不再在名称后附加供应商括号）
        if model_name:
            # 提取模型名称的最后部分
            model_display_name = model_name.split("/")[-1] if "/" in model_name else model_name
            name = model_display_name
        else:
            name = "未命名模型"
        
        return {
            "name": name,
            "provider": provider,
            "api_url": api_url,
            "model_name": model_name,
            "api_key": api_key
        }
    
    def validate_form(self) -> bool:
        """验证表单"""
        data = self.get_form_data()
        
        if not data["provider"]:
            show_error("错误", "请输入供应商")
            return False
        
        if not data["api_url"]:
            show_error("错误", "请输入API文档地址")
            return False
        
        if not data["model_name"]:
            show_error("错误", "请输入模型名称")
            return False
        
        if not data["api_key"]:
            show_error("错误", "请输入API Key")
            return False
        
        return True
    
    def test_connection(self):
        """测试连接"""
        if not self.validate_form():
            return
        
        self.test_button.configure(text="测试中...", state="disabled")
        
        def test_thread():
            try:
                data = self.get_form_data()
                success, message = self.model_manager.test_model_connection(data)
                
                # 在主线程中更新UI
                self.after(0, lambda: self.show_test_result(success, message))
            except Exception as e:
                self.after(0, lambda: self.show_test_result(False, f"测试失败: {str(e)}"))
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def show_test_result(self, success: bool, message: str):
        """显示测试结果"""
        self.test_button.configure(text="测试连接", state="normal")
        
        if success:
            show_success("测试成功", message)
        else:
            show_error("测试失败", message)
    
    def ok(self):
        """确定按钮"""
        if self.validate_form():
            self.result = self.get_form_data()
            self.destroy()
    
    def cancel(self):
        """取消按钮"""
        self.result = None
        self.destroy()


class ModelManagementWindow(ctk.CTkToplevel):
    """模型管理主窗口"""
    
    def __init__(self, parent, model_manager: AIModelManager, settings_manager: SettingsManager = None):
        super().__init__(parent)
        self.model_manager = model_manager
        self.settings_manager = settings_manager or SettingsManager()
        self.parent = parent
        
        self.setup_window()
        self.create_widgets()
        self.load_models()
        
        # 设置模态
        self.transient(parent)
        self.grab_set()
    
    def setup_window(self):
        """设置窗口"""
        self.title("模型管理")
        self.geometry("900x600")
        self.resizable(True, True)
        self.minsize(800, 500)
        # 同步应用图标
        try:
            icon_path = Path(__file__).parent.parent / 'assets' / 'icon.ico'
            if icon_path.exists():
                self.iconbitmap(default=str(icon_path))
            else:
                png_path = Path(__file__).parent.parent / 'assets' / 'icon.png'
                if png_path.exists():
                    img = tk.PhotoImage(file=str(png_path))
                    self.iconphoto(False, img)
                    self._icon_img_ref = img
        except Exception:
            pass
        
        # 居中显示
        self.center_window()
    
    def center_window(self):
        """窗口居中"""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.winfo_screenheight() // 2) - (600 // 2)
        self.geometry(f"900x600+{x}+{y}")
    
    def create_widgets(self):
        """创建界面元素"""
        # 主框架
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 标题和工具栏
        header_frame = ctk.CTkFrame(main_frame)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title_label = ctk.CTkLabel(header_frame, text="AI模型管理", font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(side="left", padx=20, pady=15)
        
        # 工具按钮
        tools_frame = ctk.CTkFrame(header_frame)
        tools_frame.pack(side="right", padx=20, pady=10)
        
        ctk.CTkButton(tools_frame, text="添加模型", command=self.add_model, width=100).pack(side="left", padx=5)
        ctk.CTkButton(tools_frame, text="导入", command=self.import_models, width=80).pack(side="left", padx=5)
        ctk.CTkButton(tools_frame, text="导出", command=self.export_models, width=80).pack(side="left", padx=5)
        ctk.CTkButton(tools_frame, text="刷新", command=self.load_models, width=80).pack(side="left", padx=5)
        
        # 模型列表框架
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 列表标题
        list_header = ctk.CTkFrame(list_frame)
        list_header.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(list_header, text="模型名称", font=ctk.CTkFont(weight="bold"), width=200).pack(side="left", padx=10)
        ctk.CTkLabel(list_header, text="供应商", font=ctk.CTkFont(weight="bold"), width=120).pack(side="left", padx=10)
        ctk.CTkLabel(list_header, text="状态", font=ctk.CTkFont(weight="bold"), width=80).pack(side="left", padx=10)
        ctk.CTkLabel(list_header, text="操作", font=ctk.CTkFont(weight="bold")).pack(side="right", padx=10)
        
        # 滚动列表
        self.models_frame = ctk.CTkScrollableFrame(list_frame)
        self.models_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # 底部按钮
        bottom_frame = ctk.CTkFrame(main_frame)
        bottom_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        ctk.CTkButton(bottom_frame, text="关闭", command=self.destroy).pack(side="right", padx=20, pady=10)
    
    def load_models(self):
        """加载模型列表"""
        # 清空现有列表
        for widget in self.models_frame.winfo_children():
            widget.destroy()
        
        models = self.model_manager.get_all_models()
        
        if not models:
            no_models_label = ctk.CTkLabel(self.models_frame, text="暂无模型，点击\"添加模型\"开始添加", 
                                         font=ctk.CTkFont(size=14), text_color="gray")
            no_models_label.pack(pady=50)
            return
        
        for model in models:
            self.create_model_item(model)
    
    def create_model_item(self, model: Dict):
        """创建模型列表项"""
        item_frame = ctk.CTkFrame(self.models_frame)
        item_frame.pack(fill="x", pady=5, padx=5)
        
        # 模型信息
        info_frame = ctk.CTkFrame(item_frame)
        info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        
        # 模型名称
        name_label = ctk.CTkLabel(info_frame, text=model.get("name", "未命名"), 
                                font=ctk.CTkFont(size=14, weight="bold"), width=200)
        name_label.pack(side="left", padx=10)
        
        # 供应商
        provider_label = ctk.CTkLabel(info_frame, text=model.get("provider", "未知"), width=120)
        provider_label.pack(side="left", padx=10)
        
        # 状态
        status_text = "启用" if model.get("enabled", True) else "禁用"
        status_color = "green" if model.get("enabled", True) else "red"
        status_label = ctk.CTkLabel(info_frame, text=status_text, text_color=status_color, width=80)
        status_label.pack(side="left", padx=10)
        
        # 操作按钮
        actions_frame = ctk.CTkFrame(item_frame)
        actions_frame.pack(side="right", padx=10, pady=10)
        
        # 启用/禁用按钮
        toggle_text = "禁用" if model.get("enabled", True) else "启用"
        toggle_btn = ctk.CTkButton(actions_frame, text=toggle_text, width=60,
                                 command=lambda m=model: self.toggle_model(m))
        toggle_btn.pack(side="left", padx=2)
        
        # 编辑按钮
        edit_btn = ctk.CTkButton(actions_frame, text="编辑", width=60,
                               command=lambda m=model: self.edit_model(m))
        edit_btn.pack(side="left", padx=2)
        
        # 复制按钮
        copy_btn = ctk.CTkButton(actions_frame, text="复制", width=60,
                               command=lambda m=model: self.duplicate_model(m))
        copy_btn.pack(side="left", padx=2)
        
        # 测试按钮
        test_btn = ctk.CTkButton(actions_frame, text="测试", width=60,
                               command=lambda m=model: self.test_model(m))
        test_btn.pack(side="left", padx=2)
        
        # 删除按钮
        delete_color = self.settings_manager.get_color("delete_button_color")
        delete_hover_color = self.settings_manager.get_color("delete_button_hover_color")
        delete_btn = ctk.CTkButton(actions_frame, text="删除", width=60, 
                                 fg_color=delete_color, hover_color=delete_hover_color,
                                 command=lambda m=model: self.delete_model(m))
        delete_btn.pack(side="left", padx=2)
    
    def add_model(self):
        """添加模型"""
        dialog = ModelDialog(self, self.model_manager)
        self.wait_window(dialog)
        
        if dialog.result:
            try:
                self.model_manager.add_model(dialog.result)
                self.load_models()
                show_success("成功", "模型添加成功！")
                # 通知主窗口刷新模型列表，使新添加的模型出现在顶部下拉框
                if hasattr(self.parent, 'load_models'):
                    self.parent.load_models()
            except Exception as e:
                show_error(f"更新模型失败: {str(e)}")
    
    def edit_model(self, model: Dict):
        """编辑模型"""
        dialog = ModelDialog(self, self.model_manager, model)
        self.wait_window(dialog)
        
        if dialog.result:
            try:
                self.model_manager.update_model(model["id"], dialog.result)
                self.load_models()
                show_success("成功", "模型更新成功！")
                # 通知主窗口刷新模型列表
                if hasattr(self.parent, 'load_models'):
                    self.parent.load_models()
            except Exception as e:
                show_error(f"更新模型失败: {str(e)}")
    
    def delete_model(self, model: Dict):
        """删除模型"""
        if show_confirm(f"确定要删除模型 \"{model.get('name', '未命名')}\" 吗？"):
            try:
                self.model_manager.delete_model(model["id"])
                self.load_models()
                show_success("成功", "模型删除成功！")
                # 通知主窗口刷新模型列表
                if hasattr(self.parent, 'load_models'):
                    self.parent.load_models()
            except Exception as e:
                show_error(f"删除模型失败: {str(e)}")
    
    def toggle_model(self, model: Dict):
        """切换模型启用状态"""
        try:
            self.model_manager.toggle_model_status(model["id"])
            self.load_models()
            status = "启用" if not model.get("enabled", True) else "禁用"
            show_success("成功", f"模型已{status}！")
            # 通知主窗口刷新模型列表
            if hasattr(self.parent, 'load_models'):
                self.parent.load_models()
        except Exception as e:
            show_error(f"操作失败: {str(e)}")
    
    def duplicate_model(self, model: Dict):
        """复制模型"""
        try:
            new_model_id = self.model_manager.duplicate_model(model["id"])
            if new_model_id:
                self.load_models()
                show_success("成功", "模型复制成功！")
                # 通知主窗口刷新模型列表
                if hasattr(self.parent, 'load_models'):
                    self.parent.load_models()
            else:
                show_error("模型复制失败！")
        except Exception as e:
            show_error(f"复制模型失败: {str(e)}")
    
    def test_model(self, model: Dict):
        """测试模型连接"""
        def test_thread():
            try:
                success, message = self.model_manager.test_model_connection(model)
                self.after(0, lambda: self.show_test_result(success, message, model.get("name", "未命名")))
            except Exception as e:
                self.after(0, lambda: self.show_test_result(False, f"测试失败: {str(e)}", model.get("name", "未命名")))
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def show_test_result(self, success: bool, message: str, model_name: str):
        """显示测试结果"""
        if success:
            show_success("测试成功", f"{model_name}: {message}")
        else:
            show_error("测试失败", f"{model_name}: {message}")
    
    def import_models(self):
        """导入模型"""
        file_path = filedialog.askopenfilename(
            title="选择模型配置文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if file_path:
            replace = show_confirm("是否替换现有模型？\n选择\"是\"将替换所有现有模型\n选择\"否\"将添加到现有模型中")
            
            try:
                success = self.model_manager.import_models(file_path, replace)
                if success:
                    self.load_models()
                    show_success("成功", "模型导入成功！")
                    # 通知主窗口刷新模型列表
                    if hasattr(self.parent, 'load_models'):
                        self.parent.load_models()
                else:
                    show_error("模型导入失败！")
            except Exception as e:
                show_error(f"导入失败: {str(e)}")
    
    def export_models(self):
        """导出模型"""
        file_path = filedialog.asksaveasfilename(
            title="保存模型配置",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                success = self.model_manager.export_models(file_path)
                if success:
                    show_success("成功", "模型导出成功！")
                else:
                    show_error("模型导出失败！")
            except Exception as e:
                show_error(f"导出失败: {str(e)}")