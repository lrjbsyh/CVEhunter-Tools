"""
设置管理器模块
负责应用程序的主题、颜色和其他设置管理
"""

import os
import json
from typing import Dict, Any, Optional


class SettingsManager:
    """设置管理器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.settings_file = os.path.join(data_dir, "settings.json")
        self.ensure_data_dir()
        self.settings = self.load_settings()
        # 自动检测并填充内置 SQLmap 路径（若为空或无效）
        self.ensure_sqlmap_default()
    
    def ensure_data_dir(self):
        """确保数据目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def get_default_settings(self) -> Dict[str, Any]:
        """获取默认设置（移除主题与颜色主题相关项）"""
        return {
            "colors": {
                "user_message_color": "#00CC66",
                "ai_message_color": "#00AA44",
                "delete_button_color": "#8B0000",
                "delete_button_hover_color": "#660000",
                "status_enabled_color": "#00AA44",
                "status_disabled_color": "#CC0000"
            },
            "ui": {
                "font_size": 14,
                "window_size": "1200x800",
                "show_hosts_reminder": True
            },
            # 面板比例持久化（左右、报告、SQLmap、中心垂直）
            "panel_ratios": {
                "left": 0.25,
                "right": 0.25,
                "report": 0.20,
                "sqlmap": 0.20,
                "center_vertical": 0.70
            },
            # 工具路径配置
            "tools": {
                "sqlmap_path": ""
            }
        }
    
    def load_settings(self) -> Dict[str, Any]:
        """加载设置"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # 合并默认设置，确保所有必要的键都存在
                    default_settings = self.get_default_settings()
                    self._merge_settings(default_settings, loaded_settings)
                    return default_settings
            except:
                return self.get_default_settings()
        return self.get_default_settings()
    
    def _merge_settings(self, default: Dict, loaded: Dict):
        """递归合并设置"""
        for key, value in loaded.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self._merge_settings(default[key], value)
                else:
                    default[key] = value
    
    def save_settings(self):
        """保存设置"""
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)
    
    def get_setting(self, key_path: str, default=None):
        """获取设置值，支持点分隔的路径"""
        keys = key_path.split('.')
        value = self.settings
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set_setting(self, key_path: str, value):
        """设置值，支持点分隔的路径"""
        keys = key_path.split('.')
        current = self.settings
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        self.save_settings()
    
    
    def get_color(self, color_key: str) -> str:
        """获取颜色值"""
        default_colors = self.get_default_settings()["colors"]
        default_value = default_colors.get(color_key, "#000000")
        return self.get_setting(f"colors.{color_key}", default_value)
    
    
    
    def get_font_size(self) -> int:
        """获取字体大小"""
        return self.get_setting("ui.font_size", 14)
    
    def set_font_size(self, size: int):
        """设置字体大小"""
        # 限制字体大小范围
        if size < 8:
            size = 8
        elif size > 24:
            size = 24
        self.set_setting("ui.font_size", size)
    
    def get_font_sizes(self) -> Dict[str, int]:
        """根据基础字体大小计算各种字体大小"""
        base_size = self.get_font_size()
        return {
            "normal": base_size,
            "heading": base_size + 2,
            "code": base_size - 1,
            "small": base_size - 2
        }

    # 新增：确保 SQLmap 路径默认值
    def ensure_sqlmap_default(self):
        try:
            current = self.get_setting("tools.sqlmap_path", "") or ""
            if current and os.path.exists(current):
                return
            detected = self.detect_sqlmap_path()
            if detected:
                # 仅在当前为空或无效时写入
                self.set_setting("tools.sqlmap_path", detected)
        except Exception:
            pass

    # 新增：检测内置 sqlmap 路径（优先使用应用根目录下的 sqlmap）
    def detect_sqlmap_path(self) -> Optional[str]:
        try:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
            candidates = [
                os.path.join(base_dir, "sqlmap", "sqlmap.py"),
                os.path.join(base_dir, "sqlmap", "sqlmap.bat"),
                os.path.join(base_dir, "sqlmap.py"),
                os.path.join(base_dir, "sqlmap.bat"),
            ]
            for p in candidates:
                if os.path.exists(p):
                    return p
        except Exception:
            return None
        return None