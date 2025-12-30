"""
聊天管理器模块
负责对话历史的管理和消息处理
"""

import os
import json
import uuid
import requests
from datetime import datetime
from typing import List, Dict, Optional


class ChatManager:
    """对话管理器"""
    
    def __init__(self, data_dir: str = "data", model_manager=None):
        self.data_dir = data_dir
        self.chats_file = os.path.join(data_dir, "chats.json")
        self.model_manager = model_manager
        self.ensure_data_dir()
        self.chats = self.load_chats()
        # 新增：保存当前选中的模型ID
        self.current_model_id = None
    
    def ensure_data_dir(self):
        """确保数据目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def load_chats(self) -> List[Dict]:
        """加载对话历史"""
        if os.path.exists(self.chats_file):
            try:
                with open(self.chats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_chats(self):
        """保存对话历史"""
        with open(self.chats_file, 'w', encoding='utf-8') as f:
            json.dump(self.chats, f, ensure_ascii=False, indent=2)
    
    def create_chat(self, title: str = "新建对话") -> str:
        """创建新对话"""
        chat_id = str(uuid.uuid4())
        chat = {
            "id": chat_id,
            "title": title,
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.chats.insert(0, chat)  # 新对话插入到最前面
        self.save_chats()
        return chat_id
    
    def add_message(self, chat_id: str, role: str, content: str):
        """添加消息到对话"""
        chat = self.get_chat(chat_id)
        if chat:
            message = {
                "id": str(uuid.uuid4()),  # 为消息添加唯一ID
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            chat["messages"].append(message)
            chat["updated_at"] = datetime.now().isoformat()
            
            # 如果是第一条用户消息，更新对话标题
            if len(chat["messages"]) == 1 and role == "user":
                chat["title"] = content[:30] + "..." if len(content) > 30 else content
            
            # 将更新的对话移到最前面
            self.move_chat_to_top(chat_id)
            self.save_chats()
    
    def get_chat(self, chat_id: str) -> Optional[Dict]:
        """获取指定对话"""
        return next((c for c in self.chats if c["id"] == chat_id), None)
    
    def get_all_chats(self) -> List[Dict]:
        """获取所有对话"""
        return self.chats.copy()
    
    def delete_chat(self, chat_id: str) -> bool:
        """删除对话"""
        original_count = len(self.chats)
        self.chats = [c for c in self.chats if c["id"] != chat_id]
        if len(self.chats) < original_count:
            self.save_chats()
            return True
        return False
    
    def update_chat_title(self, chat_id: str, new_title: str) -> bool:
        """更新对话标题"""
        chat = self.get_chat(chat_id)
        if chat:
            chat["title"] = new_title
            chat["updated_at"] = datetime.now().isoformat()
            self.save_chats()
            return True
        return False
    
    def clear_chat_messages(self, chat_id: str) -> bool:
        """清空对话消息"""
        chat = self.get_chat(chat_id)
        if chat:
            chat["messages"] = []
            chat["updated_at"] = datetime.now().isoformat()
            self.save_chats()
            return True
        return False
    
    def delete_message(self, chat_id: str, message_id: str) -> bool:
        """删除指定消息"""
        chat = self.get_chat(chat_id)
        if chat:
            original_count = len(chat["messages"])
            chat["messages"] = [msg for msg in chat["messages"] if msg.get("id") != message_id]
            if len(chat["messages"]) < original_count:
                chat["updated_at"] = datetime.now().isoformat()
                self.save_chats()
                return True
        return False
    
    def delete_messages(self, chat_id: str, message_ids: List[str]) -> bool:
        """批量删除消息"""
        chat = self.get_chat(chat_id)
        if chat:
            original_count = len(chat["messages"])
            chat["messages"] = [msg for msg in chat["messages"] if msg.get("id") not in message_ids]
            if len(chat["messages"]) < original_count:
                chat["updated_at"] = datetime.now().isoformat()
                self.save_chats()
                return True
        return False
    
    def get_message(self, chat_id: str, message_id: str) -> Optional[Dict]:
        """获取指定消息"""
        chat = self.get_chat(chat_id)
        if chat:
            return next((msg for msg in chat["messages"] if msg.get("id") == message_id), None)
        return None
    
    def move_chat_to_top(self, chat_id: str):
        """将对话移到列表顶部"""
        chat = self.get_chat(chat_id)
        if chat:
            self.chats = [c for c in self.chats if c["id"] != chat_id]
            self.chats.insert(0, chat)
    
    def duplicate_chat(self, chat_id: str) -> Optional[str]:
        """复制对话"""
        original_chat = self.get_chat(chat_id)
        if original_chat:
            new_chat_id = str(uuid.uuid4())
            new_chat = {
                "id": new_chat_id,
                "title": f"{original_chat['title']} (副本)",
                "messages": original_chat["messages"].copy(),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.chats.insert(0, new_chat)
            self.save_chats()
            return new_chat_id
        return None
    
    def search_chats(self, keyword: str) -> List[Dict]:
        """搜索对话"""
        keyword = keyword.lower()
        results = []
        
        for chat in self.chats:
            # 搜索标题
            if keyword in chat["title"].lower():
                results.append(chat)
                continue
            
            # 搜索消息内容
            for message in chat["messages"]:
                if keyword in message["content"].lower():
                    results.append(chat)
                    break
        
        return results
    
    def get_chat_statistics(self) -> Dict:
        """获取对话统计信息"""
        total_chats = len(self.chats)
        total_messages = sum(len(chat["messages"]) for chat in self.chats)
        
        if self.chats:
            latest_chat = max(self.chats, key=lambda x: x["updated_at"])
            oldest_chat = min(self.chats, key=lambda x: x["created_at"])
        else:
            latest_chat = oldest_chat = None
        
        return {
            "total_chats": total_chats,
            "total_messages": total_messages,
            "latest_chat": latest_chat,
            "oldest_chat": oldest_chat
        }
    
    def export_chat(self, chat_id: str, file_path: str) -> bool:
        """导出单个对话"""
        chat = self.get_chat(chat_id)
        if chat:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(chat, f, ensure_ascii=False, indent=2)
                return True
            except Exception:
                return False
        return False
    
    def export_all_chats(self, file_path: str) -> bool:
        """导出所有对话"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.chats, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def import_chats(self, file_path: str, replace: bool = False) -> bool:
        """导入对话列表"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            if isinstance(imported_data, dict):
                # 兼容旧格式
                imported_chats = imported_data.get("chats", [])
            elif isinstance(imported_data, list):
                # 对话列表
                imported_chats = imported_data
            else:
                return False
            
            if replace:
                self.chats = imported_chats
            else:
                # 为导入的对话生成新的ID
                for chat in imported_chats:
                    chat["id"] = str(uuid.uuid4())
                    chat["created_at"] = datetime.now().isoformat()
                    chat["updated_at"] = datetime.now().isoformat()
                self.chats.extend(imported_chats)
            
            self.save_chats()
            return True
        except Exception:
            return False
    
    # 新增：设置当前模型ID
    def set_current_model_id(self, model_id: Optional[str]):
        """设置当前使用的模型ID"""
        self.current_model_id = model_id
    
    def send_message(self, message: str, chat_id: str = None) -> str:
        """发送消息给AI模型并返回响应"""
        if not self.model_manager:
            raise Exception("模型管理器未初始化")
        
        # 获取启用的模型
        enabled_models = self.model_manager.get_enabled_models()
        if not enabled_models:
            raise Exception("没有可用的AI模型")
        
        # 优先使用当前选择的模型ID（如果存在且已启用）
        model = None
        if self.current_model_id:
            model = next((m for m in enabled_models if m["id"] == self.current_model_id), None)
        if not model:
            model = enabled_models[0]
        
        # 基础配置校验，提前失败并给出明确提示
        required_keys = ["api_url", "model_name", "api_key"]
        missing = [k for k in required_keys if not str(model.get(k, "")).strip()]
        if missing:
            raise Exception(f"模型配置不完整，缺少: {', '.join(missing)}")
        
        try:
            headers = {
                "Authorization": f"Bearer {model['api_key']}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # 构建消息历史
            messages = [{"role": "user", "content": message}]
            
            # 如果指定了chat_id，获取对话历史
            if chat_id:
                chat = self.get_chat(chat_id)
                if chat and chat["messages"]:
                    messages = []
                    for msg in chat["messages"]:
                        if msg["role"] in ["user", "assistant"]:
                            messages.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })
                    messages.append({"role": "user", "content": message})
            
            data = {
                "model": model["model_name"],
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.7
            }
            
            # 规范化 API URL，确保请求指向 /v1/chat/completions
            api_url = str(model["api_url"]).rstrip("/")
            if not api_url.endswith("/chat/completions"):
                if api_url.endswith("/v1"):
                    api_url = f"{api_url}/chat/completions"
                else:
                    # 如果用户只填了域名或其他路径，优先追加 /v1/chat/completions
                    api_url = f"{api_url}/v1/chat/completions"
            
            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=300  # 延长到5分钟
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0 and result["choices"][0].get("message"):
                    return result["choices"][0]["message"]["content"]
                else:
                    raise Exception("AI响应格式错误：缺少choices.message.content")
            else:
                # 提取更友好的错误信息
                err_msg = None
                try:
                    err_json = response.json()
                    err_msg = (
                        (err_json.get("error") or {}).get("message")
                        or err_json.get("message")
                        or err_json.get("detail")
                    )
                except Exception:
                    pass
                if not err_msg:
                    err_msg = response.text.strip()
                raise Exception(f"AI请求失败: {response.status_code} - {err_msg}")
                
        except Exception as e:
            raise Exception(f"发送消息失败: {str(e)}")