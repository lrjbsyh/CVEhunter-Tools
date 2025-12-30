"""
通知系统模块
提供右下角自动消失的通知功能，替代传统的弹窗
"""

import customtkinter as ctk
import tkinter as tk
from typing import Literal, Optional
import threading
import time


class NotificationManager:
    """通知管理器 - 单例模式"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.root_window = None
            self.notifications = []
            self.max_notifications = 5
            self._initialized = True
    
    def set_root_window(self, root_window):
        """设置主窗口引用"""
        self.root_window = root_window
    
    def show_notification(self, 
                         title: str, 
                         message: str, 
                         notification_type: Literal["info", "success", "warning", "error"] = "info",
                         duration: int = 3000):
        """显示通知"""
        if not self.root_window:
            print(f"[{notification_type.upper()}] {title}: {message}")
            return
        
        # 在主线程中创建通知
        self.root_window.after(0, lambda: self._create_notification(title, message, notification_type, duration))
    
    def _create_notification(self, title: str, message: str, notification_type: str, duration: int):
        """在主线程中创建通知"""
        # 如果通知过多，移除最旧的
        if len(self.notifications) >= self.max_notifications:
            oldest = self.notifications.pop(0)
            oldest.destroy()
        
        # 创建通知窗口
        notification = NotificationWindow(self.root_window, title, message, notification_type, duration)
        self.notifications.append(notification)
        
        # 重新排列通知位置
        self._arrange_notifications()
        
        # 设置自动移除
        def remove_notification():
            if notification in self.notifications:
                self.notifications.remove(notification)
                notification.destroy()
                self._arrange_notifications()
        
        self.root_window.after(duration, remove_notification)
    
    def _arrange_notifications(self):
        """重新排列通知位置"""
        if not self.root_window:
            return
        
        # 获取主窗口位置和大小
        self.root_window.update_idletasks()
        root_x = self.root_window.winfo_x()
        root_y = self.root_window.winfo_y()
        root_width = self.root_window.winfo_width()
        root_height = self.root_window.winfo_height()
        
        # 从底部开始排列
        y_offset = 20
        for i, notification in enumerate(reversed(self.notifications)):
            if notification.winfo_exists():
                x = root_x + root_width - 320 - 20  # 右边距20px
                y = root_y + root_height - y_offset - 100  # 通知高度约100px
                notification.geometry(f"320x100+{x}+{y}")
                y_offset += 110  # 通知间距10px


class NotificationWindow(ctk.CTkToplevel):
    """单个通知窗口"""
    
    def __init__(self, parent, title: str, message: str, notification_type: str, duration: int):
        super().__init__(parent)
        
        self.title_text = title
        self.message_text = message
        self.notification_type = notification_type
        self.duration = duration
        
        self.setup_window()
        self.create_widgets()
        self.animate_in()
    
    def setup_window(self):
        """设置窗口属性"""
        self.title("")
        self.geometry("320x100")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.overrideredirect(True)  # 无边框窗口
        
        # 设置透明度
        self.attributes("-alpha", 0.0)
    
    def create_widgets(self):
        """创建界面元素"""
        # 根据通知类型设置颜色
        colors = {
            "info": ("#3b82f6", "#2563eb"),
            "success": ("#10b981", "#059669"),
            "warning": ("#f59e0b", "#d97706"),
            "error": ("#ef4444", "#dc2626")
        }
        
        bg_color, border_color = colors.get(self.notification_type, colors["info"])
        
        # 主框架
        main_frame = ctk.CTkFrame(self, 
                                 fg_color=bg_color,
                                 corner_radius=8,
                                 border_width=2,
                                 border_color=border_color)
        main_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # 图标和内容框架
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=8)
        
        # 图标
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        
        icon_label = ctk.CTkLabel(content_frame, 
                                 text=icons.get(self.notification_type, "ℹ️"),
                                 font=ctk.CTkFont(size=16))
        icon_label.pack(side="left", padx=(0, 8))
        
        # 文本内容
        text_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True)
        
        # 标题
        title_label = ctk.CTkLabel(text_frame,
                                  text=self.title_text,
                                  font=ctk.CTkFont(size=12, weight="bold"),
                                  text_color="white")
        title_label.pack(anchor="w")
        
        # 消息
        message_label = ctk.CTkLabel(text_frame,
                                   text=self.message_text,
                                   font=ctk.CTkFont(size=10),
                                   text_color="white",
                                   wraplength=220)
        message_label.pack(anchor="w")
        
        # 关闭按钮
        close_btn = ctk.CTkButton(content_frame,
                                 text="×",
                                 width=20,
                                 height=20,
                                 font=ctk.CTkFont(size=14, weight="bold"),
                                 fg_color="transparent",
                                 text_color="white",
                                 hover_color=("gray70", "gray30"),
                                 command=self.close_notification)
        close_btn.pack(side="right", padx=(8, 0))
    
    def animate_in(self):
        """淡入动画"""
        def fade_in(alpha=0.0):
            if alpha < 0.95:
                alpha += 0.05
                self.attributes("-alpha", alpha)
                self.after(20, lambda: fade_in(alpha))
            else:
                self.attributes("-alpha", 0.95)
        
        fade_in()
    
    def close_notification(self):
        """关闭通知"""
        def fade_out(alpha=0.95):
            if alpha > 0.0:
                alpha -= 0.1
                self.attributes("-alpha", alpha)
                self.after(20, lambda: fade_out(alpha))
            else:
                self.destroy()
        
        fade_out()


# 全局通知管理器实例
notification_manager = NotificationManager()


def show_info(title: str, message: str, duration: int = 3000):
    """显示信息通知"""
    notification_manager.show_notification(title, message, "info", duration)


def show_success(title: str, message: str, duration: int = 3000):
    """显示成功通知"""
    notification_manager.show_notification(title, message, "success", duration)


def show_warning(title: str, message: str = "", duration: int = 4000, confirm: bool = False):
    """显示警告通知"""
    if confirm:
        # 对于需要确认的情况，暂时使用messagebox
        from tkinter import messagebox
        return messagebox.askyesno("确认", title if not message else f"{title}\n{message}")
    else:
        notification_manager.show_notification(title, message, "warning", duration)


def show_error(title: str, message: str = "", duration: int = 5000):
    """显示错误通知"""
    notification_manager.show_notification(title, message, "error", duration)


def show_confirm(title: str, message: str = ""):
    """显示确认对话框"""
    from tkinter import messagebox
    return messagebox.askyesnocancel(title, message)


def ask_yes_no(title: str, message: str, callback=None):
    """询问是否确认（简化版，显示警告通知）"""
    show_warning(title, f"{message}\n请在代码中处理确认逻辑", 4000)
    # 注意：这是简化版本，实际使用时需要根据具体需求实现确认对话框
    if callback:
        callback(True)  # 默认返回True