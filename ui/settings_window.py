"""
设置窗口模块
提供主题、颜色和其他设置的用户界面
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from typing import Dict, Callable
from pathlib import Path
from managers.settings_manager import SettingsManager
from utils.notification_system import show_info, show_success, show_warning, show_error


class SettingsWindow(ctk.CTkToplevel):
    """设置窗口"""
    
    def __init__(self, parent, settings_manager: SettingsManager, on_settings_changed: Callable = None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.on_settings_changed = on_settings_changed
        
        self.setup_window()
        self.create_widgets()
        self.load_current_settings()
        
        # 设置模态
        self.transient(parent)
        self.grab_set()
        
        # 居中显示
        self.geometry("600x700")
        self.center_window()
    
    def setup_window(self):
        """设置窗口"""
        self.title("设置")
        self.resizable(True, True)
        self.minsize(500, 600)
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
        x = (self.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.winfo_screenheight() // 2) - (700 // 2)
        self.geometry(f"600x700+{x}+{y}")
    
    def create_widgets(self):
        """创建界面元素"""
        # 主框架
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 标题
        title_label = ctk.CTkLabel(main_frame, text="设置", font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=(20, 30))
        
        # 滚动框架
        self.scroll_frame = ctk.CTkScrollableFrame(main_frame)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # 外观设置
        self.create_appearance_section()
        
        # 提醒与提示设置
        self.create_reminder_section()
        
        # 工具路径设置（SQLmap）
        self.create_tools_section()
        
        # 按钮框架
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # 重置按钮
        reset_button = ctk.CTkButton(button_frame, text="重置为默认", command=self.reset_to_defaults)
        reset_button.pack(side="left", padx=(10, 5), pady=10)
        
        # 取消按钮
        cancel_button = ctk.CTkButton(button_frame, text="取消", command=self.cancel)
        cancel_button.pack(side="right", padx=(5, 10), pady=10)
        
        # 应用按钮
        apply_button = ctk.CTkButton(button_frame, text="应用", command=self.apply_settings)
        apply_button.pack(side="right", padx=(5, 5), pady=10)
    
    def create_appearance_section(self):
        """创建外观设置区域（仅保留字体大小设置）"""
        # 外观标题
        appearance_label = ctk.CTkLabel(self.scroll_frame, text="外观设置", 
                                      font=ctk.CTkFont(size=16, weight="bold"))
        appearance_label.pack(anchor="w", pady=(20, 10))

        # 字体大小设置
        font_size_frame = ctk.CTkFrame(self.scroll_frame)
        font_size_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(font_size_frame, text="字体大小:", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=15, pady=(15, 5))
        
        # 字体大小控制框架
        font_control_frame = ctk.CTkFrame(font_size_frame)
        font_control_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        # 字体大小滑块
        self.font_size_var = ctk.IntVar()
        self.font_size_slider = ctk.CTkSlider(font_control_frame, from_=8, to=24, number_of_steps=16,
                                            variable=self.font_size_var, command=self.on_font_size_change)
        self.font_size_slider.pack(side="left", fill="x", expand=True, padx=(10, 10), pady=10)
        
        # 字体大小显示标签
        self.font_size_label = ctk.CTkLabel(font_control_frame, text="14", font=ctk.CTkFont(size=12))
        self.font_size_label.pack(side="right", padx=(0, 10), pady=10)
        
        # 字体大小预览
        self.font_preview_label = ctk.CTkLabel(font_size_frame, text="预览文本 Preview Text", 
                                             font=ctk.CTkFont(size=14))
        self.font_preview_label.pack(pady=(0, 15))
    

    def create_reminder_section(self):
        """创建提醒与提示设置区域"""
        # 区域标题
        reminder_label = ctk.CTkLabel(self.scroll_frame, text="提醒与提示", 
                                    font=ctk.CTkFont(size=16, weight="bold"))
        reminder_label.pack(anchor="w", pady=(20, 10))

        reminder_frame = ctk.CTkFrame(self.scroll_frame)
        reminder_frame.pack(fill="x", pady=(0, 15))

        # 启动显示hosts环境配置提醒
        self.show_hosts_reminder_var = ctk.BooleanVar()
        show_hosts_switch = ctk.CTkSwitch(
            reminder_frame,
            text="启动时显示环境配置提醒",
            variable=self.show_hosts_reminder_var,
            onvalue=True,
            offvalue=False
        )
        show_hosts_switch.pack(anchor="w", padx=15, pady=(15, 5))
    
    def create_tools_section(self):
        """创建工具路径设置区域（SQLmap）"""
        tools_label = ctk.CTkLabel(self.scroll_frame, text="工具路径", 
                                  font=ctk.CTkFont(size=16, weight="bold"))
        tools_label.pack(anchor="w", pady=(20, 10))
        
        sqlmap_frame = ctk.CTkFrame(self.scroll_frame)
        sqlmap_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(sqlmap_frame, text="SQLmap路径:", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=15, pady=(15, 5))
        
        path_row = ctk.CTkFrame(sqlmap_frame)
        path_row.pack(fill="x", padx=15, pady=(0, 10))
        
        self.sqlmap_path_var = ctk.StringVar()
        self.sqlmap_path_entry = ctk.CTkEntry(path_row, textvariable=self.sqlmap_path_var)
        self.sqlmap_path_entry.pack(side="left", fill="x", expand=True)
        
        def browse_sqlmap():
            file_path = filedialog.askopenfilename(title="选择SQLmap可执行文件或脚本",
                                                   filetypes=[("可执行/脚本", "*.exe *.py"), ("所有文件", "*.*")])
            if file_path:
                self.sqlmap_path_var.set(file_path)
        
        browse_btn = ctk.CTkButton(path_row, text="浏览", width=80, command=browse_sqlmap)
        browse_btn.pack(side="left", padx=(10, 0))
    
    
    def on_font_size_change(self, value):
        """字体大小变化回调"""
        font_size = int(value)
        self.font_size_label.configure(text=str(font_size))
        self.font_preview_label.configure(font=ctk.CTkFont(size=font_size))
    
    def load_current_settings(self):
        """加载当前设置"""
        # 加载字体大小
        current_font_size = self.settings_manager.get_font_size()
        self.font_size_var.set(current_font_size)
        self.font_size_label.configure(text=str(current_font_size))
        self.font_preview_label.configure(font=ctk.CTkFont(size=current_font_size))
        

        # 加载提醒设置
        try:
            current_hosts_reminder = bool(self.settings_manager.get_setting("ui.show_hosts_reminder", True))
        except Exception:
            current_hosts_reminder = True
        self.show_hosts_reminder_var.set(current_hosts_reminder)
        
        # 加载SQLmap路径
        try:
            current_sqlmap_path = self.settings_manager.get_setting("tools.sqlmap_path", "") or ""
        except Exception:
            current_sqlmap_path = ""
        if hasattr(self, "sqlmap_path_var"):
            self.sqlmap_path_var.set(current_sqlmap_path)
    
    
    
    def apply_settings(self):
        """应用设置"""
        # 保存字体大小设置
        self.settings_manager.set_font_size(self.font_size_var.get())

        # 保存提醒设置
        try:
            self.settings_manager.set_setting("ui.show_hosts_reminder", bool(self.show_hosts_reminder_var.get()))
        except Exception as e:
            show_error("错误", f"保存提醒设置失败: {e}")
        
        # 保存SQLmap路径
        try:
            self.settings_manager.set_setting("tools.sqlmap_path", self.sqlmap_path_var.get().strip())
        except Exception as e:
            show_error("错误", f"保存SQLmap路径失败: {e}")
        
        # 通知主应用程序设置已更改
        if self.on_settings_changed:
            self.on_settings_changed()
        
        show_success("成功", "设置已保存！重启应用程序以查看所有更改。")
        self.destroy()
    
    def reset_to_defaults(self):
        """重置为默认设置"""
        if show_warning("确定要重置所有设置为默认值吗？", confirm=True):
            # 重置设置
            self.settings_manager.settings = self.settings_manager.get_default_settings()
            self.settings_manager.save_settings()
            
            # 重新加载界面
            self.load_current_settings()
            
            show_success("成功", "设置已重置为默认值！")
    
    def cancel(self):
        """取消"""
        self.destroy()