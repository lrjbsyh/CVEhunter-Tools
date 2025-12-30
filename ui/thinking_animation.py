"""
改进的AI思考动画组件
提供更美观的动画效果和样式
"""

import customtkinter as ctk
import tkinter as tk
import math
import time
import os
from typing import Optional, Callable


class ThinkingAnimation:
    """改进的AI思考动画组件"""
    
    def __init__(self, parent, on_stop: Optional[Callable] = None):
        self.parent = parent
        self.on_stop = on_stop
        self.animation_job = None
        self.frame = None
        self.canvas = None
        self.text_label = None
        self.progress_bar = None
        self.stop_button = None
        
        # 动画参数
        self.animation_step = 0
        self.start_time = time.time()
        self.thinking_texts = [
            "🤔 正在思考",
            "💭 分析问题中",
            "⚡ 生成回答中", 
            "🧠 处理信息中",
            "✨ 优化回答中",
            "🔍 深度分析中",
            "💡 构思回答中",
            "🎯 精准定位中"
        ]
        
        # 跳动点动画参数
        self.dot_positions = [0, 0, 0]  # 三个点的垂直位置
        self.dot_speeds = [0.3, 0.4, 0.5]  # 不同的跳动速度
        
    def show(self):
        """显示思考动画"""
        if self.frame:
            return  # 已经在显示
            
        # 创建主框架
        self.frame = ctk.CTkFrame(self.parent)
        self.frame.pack(fill="x", pady=5, padx=10)
        
        # 内容框架
        content_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=15, pady=10)
        
        # 左侧动画区域
        animation_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        animation_frame.pack(side="left", fill="y")
        
        # 创建圆形进度动画
        self.canvas = tk.Canvas(
            animation_frame, 
            width=40, 
            height=40, 
            bg=self._get_bg_color(),
            highlightthickness=0
        )
        self.canvas.pack(side="left", padx=(0, 10))
        
        # 中间文本区域
        text_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True)
        
        # AI标签
        ai_label = ctk.CTkLabel(
            text_frame, 
            text="AI助手:", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#1f538d", "#4a9eff")
        )
        ai_label.pack(anchor="w")
        
        # 思考文本
        self.text_label = ctk.CTkLabel(
            text_frame,
            text="🤔 正在思考...",
            font=ctk.CTkFont(size=14),
            text_color=("#2b2b2b", "#ffffff")
        )
        self.text_label.pack(anchor="w", pady=(2, 0))
        
        # 进度条
        self.progress_bar = ctk.CTkProgressBar(
            text_frame,
            width=200,
            height=4,
            progress_color=("#1f538d", "#4a9eff")
        )
        self.progress_bar.pack(anchor="w", pady=(5, 0), fill="x")
        self.progress_bar.set(0)
        
        # 右侧停止按钮
        if self.on_stop:
            self.stop_button = ctk.CTkButton(
                content_frame,
                text="停止",
                width=60,
                height=28,
                font=ctk.CTkFont(size=12),
                fg_color=("#dc3545", "#dc3545"),
                hover_color=("#c82333", "#c82333"),
                command=self._on_stop_clicked
            )
            self.stop_button.pack(side="right", padx=(10, 0))
        
        # 开始动画
        self.start_animation()
        
        # 滚动到底部
        self.parent.update_idletasks()
        if hasattr(self.parent, '_parent_canvas'):
            self.parent._parent_canvas.yview_moveto(1.0)
    
    def hide(self):
        """隐藏思考动画"""
        if self.animation_job:
            self.parent.after_cancel(self.animation_job)
            self.animation_job = None
            
        if self.frame:
            self.frame.destroy()
            self.frame = None
            
        self.canvas = None
        self.text_label = None
        self.progress_bar = None
        self.stop_button = None
    
    def start_animation(self):
        """开始动画"""
        def animate():
            if not self.frame:
                return
                
            self.animation_step += 1
            elapsed_time = time.time() - self.start_time
            
            # 更新圆形进度动画
            self._update_circle_animation()
            
            # 更新文本（每3秒切换一次）
            text_index = int(elapsed_time / 3) % len(self.thinking_texts)
            
            # 创建跳动的点效果
            animated_dots = self._create_animated_dots()
            current_text = f"{self.thinking_texts[text_index]}{animated_dots}"
            
            if self.text_label:
                self.text_label.configure(text=current_text)
            
            # 更新进度条（模拟进度）
            if self.progress_bar:
                # 使用复合波形模拟更自然的进度
                base_progress = (elapsed_time * 0.1) % 1.0  # 基础递增
                wave1 = math.sin(elapsed_time * 0.8) * 0.1  # 主波浪
                wave2 = math.sin(elapsed_time * 1.5) * 0.05  # 次波浪
                progress = min(0.95, base_progress + wave1 + wave2 + 0.05)
                self.progress_bar.set(progress)
            
            # 继续动画
            self.animation_job = self.parent.after(100, animate)
        
        animate()
    
    def _create_animated_dots(self):
        """创建跳动的点动画效果"""
        elapsed_time = time.time() - self.start_time
        dots = []
        
        for i in range(3):
            # 计算每个点的跳动位置
            phase = elapsed_time * self.dot_speeds[i] * 2 * math.pi
            bounce = abs(math.sin(phase))
            
            # 根据跳动高度选择不同的点符号
            if bounce > 0.7:
                dots.append("●")  # 高位置 - 实心圆
            elif bounce > 0.4:
                dots.append("◐")  # 中位置 - 半圆
            else:
                dots.append("○")  # 低位置 - 空心圆
        
        return "".join(dots)
    
    def _update_circle_animation(self):
        """更新圆形进度动画"""
        if not self.canvas:
            return
            
        self.canvas.delete("all")
        
        # 获取画布尺寸
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1 or height <= 1:
            width = height = 40
            
        center_x = width // 2
        center_y = height // 2
        radius = min(width, height) // 2 - 4
        
        # 绘制背景圆
        self.canvas.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            outline=self._get_circle_bg_color(),
            width=2
        )
        
        # 绘制多层旋转的进度弧
        elapsed_time = time.time() - self.start_time
        
        # 主旋转弧
        angle1 = (self.animation_step * 8) % 360
        extent1 = 120
        self.canvas.create_arc(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            start=angle1,
            extent=extent1,
            outline=self._get_circle_color(),
            width=3,
            style="arc"
        )
        
        # 反向旋转弧（更细）
        angle2 = (-self.animation_step * 12) % 360
        extent2 = 60
        inner_radius = radius - 6
        self.canvas.create_arc(
            center_x - inner_radius, center_y - inner_radius,
            center_x + inner_radius, center_y + inner_radius,
            start=angle2,
            extent=extent2,
            outline=self._get_circle_color(),
            width=2,
            style="arc"
        )
        
        # 脉冲中心点
        pulse = abs(math.sin(elapsed_time * 3)) * 3 + 2
        dot_radius = int(pulse)
        self.canvas.create_oval(
            center_x - dot_radius, center_y - dot_radius,
            center_x + dot_radius, center_y + dot_radius,
            fill=self._get_circle_color(),
            outline=""
        )
        
        # 添加小装饰点
        for i in range(4):
            angle_rad = math.radians(angle1 + i * 90)
            point_x = center_x + (radius - 2) * math.cos(angle_rad)
            point_y = center_y + (radius - 2) * math.sin(angle_rad)
            self.canvas.create_oval(
                point_x - 1, point_y - 1,
                point_x + 1, point_y + 1,
                fill=self._get_circle_color(),
                outline=""
            )
    
    def _get_bg_color(self):
        """获取背景颜色"""
        appearance_mode = ctk.get_appearance_mode()
        return "#212121" if appearance_mode == "Dark" else "#ffffff"
    
    def _get_circle_bg_color(self):
        """获取圆形背景颜色"""
        appearance_mode = ctk.get_appearance_mode()
        return "#404040" if appearance_mode == "Dark" else "#e0e0e0"
    
    def _get_circle_color(self):
        """获取圆形颜色"""
        appearance_mode = ctk.get_appearance_mode()
        return "#4a9eff" if appearance_mode == "Dark" else "#1f538d"
    
    def _on_stop_clicked(self):
        """停止按钮点击事件"""
        if self.on_stop:
            self.on_stop()
        self.hide()


class FileInteractionTag:
    """文件交互标签组件"""
    
    def __init__(self, parent, files: list, tag_number: int = 1, on_remove: Optional[Callable] = None):
        self.parent = parent
        self.files = files
        self.tag_number = tag_number
        self.on_remove = on_remove
        self.frame = None
        
    def show(self):
        """显示文件交互标签"""
        if self.frame:
            return
            
        # 创建标签框架
        self.frame = ctk.CTkFrame(self.parent)
        self.frame.pack(fill="x", pady=(5, 0), padx=10)
        
        # 内容框架
        content_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=10, pady=5)
        
        # 文件交互图标和文本
        icon_label = ctk.CTkLabel(
            content_frame,
            text="📁",
            font=ctk.CTkFont(size=16)
        )
        icon_label.pack(side="left")
        
        # 标签文本
        file_count = len(self.files)
        tag_text = f"文件交互-{self.tag_number}"
        
        tag_label = ctk.CTkLabel(
            content_frame,
            text=tag_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#ffffff", "#ffffff"),
            fg_color=("#28a745", "#28a745"),
            corner_radius=12
        )
        tag_label.pack(side="left", padx=(5, 0), pady=2, ipadx=8, ipady=2)
        
        # 文件列表（简化显示）
        if file_count <= 3:
            file_names = [os.path.basename(f) for f in self.files]
            files_text = ", ".join(file_names)
        else:
            file_names = [os.path.basename(f) for f in self.files[:2]]
            files_text = f"{', '.join(file_names)} 等 {file_count} 个文件"
        
        files_label = ctk.CTkLabel(
            content_frame,
            text=files_text,
            font=ctk.CTkFont(size=11),
            text_color=("#666666", "#cccccc")
        )
        files_label.pack(side="left", padx=(10, 0))
        
        # 删除按钮
        if self.on_remove:
            remove_button = ctk.CTkButton(
                content_frame,
                text="✕",
                width=24,
                height=24,
                font=ctk.CTkFont(size=12),
                fg_color=("#dc3545", "#dc3545"),
                hover_color=("#c82333", "#c82333"),
                command=self._on_remove_clicked
            )
            remove_button.pack(side="right")
    
    def hide(self):
        """隐藏标签"""
        if self.frame:
            self.frame.destroy()
            self.frame = None
    
    def destroy(self):
        """销毁标签（与hide方法功能相同）"""
        self.hide()
    
    def _on_remove_clicked(self):
        """删除按钮点击事件"""
        if self.on_remove:
            self.on_remove()
        self.hide()