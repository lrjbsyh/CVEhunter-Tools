"""
AI模型管理器模块
负责AI模型的增删改查和配置管理
"""

import os
import json
import uuid
import requests
from datetime import datetime
from typing import List, Dict, Optional


class AIModelManager:
    """AI模型管理器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.models_file = os.path.join(data_dir, "models.json")
        self.ensure_data_dir()
        self.models = self.load_models()
    
    def ensure_data_dir(self):
        """确保数据目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def load_models(self) -> List[Dict]:
        """加载模型配置"""
        if os.path.exists(self.models_file):
            try:
                with open(self.models_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self.get_default_models()
        return self.get_default_models()
    
    def save_models(self):
        """保存模型配置"""
        with open(self.models_file, 'w', encoding='utf-8') as f:
            json.dump(self.models, f, ensure_ascii=False, indent=2)
    
    def get_default_models(self) -> List[Dict]:
        """获取默认模型配置"""
        return [
            {
                "id": str(uuid.uuid4()),
                "name": "DeepSeek-R1-Qwen3-8B",
                "provider": "硅基流动",
                "api_url": "https://api.siliconflow.cn/v1/chat/completions",
                "model_name": "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
                "api_key": "",
                "enabled": False,
                "created_at": datetime.now().isoformat()
            }
        ]
    
    def add_model(self, model_data: Dict) -> str:
        """添加新模型"""
        model_id = str(uuid.uuid4())
        model = {
            "id": model_id,
            "created_at": datetime.now().isoformat(),
            "enabled": True,
            **model_data
        }
        self.models.append(model)
        self.save_models()
        return model_id
    
    def update_model(self, model_id: str, model_data: Dict) -> bool:
        """更新模型信息"""
        for i, model in enumerate(self.models):
            if model["id"] == model_id:
                self.models[i].update(model_data)
                self.models[i]["updated_at"] = datetime.now().isoformat()
                self.save_models()
                return True
        return False
    
    def delete_model(self, model_id: str) -> bool:
        """删除模型"""
        original_count = len(self.models)
        self.models = [m for m in self.models if m["id"] != model_id]
        if len(self.models) < original_count:
            self.save_models()
            return True
        return False
    
    def get_model(self, model_id: str) -> Optional[Dict]:
        """获取指定模型"""
        return next((m for m in self.models if m["id"] == model_id), None)
    
    def get_all_models(self) -> List[Dict]:
        """获取所有模型"""
        return self.models.copy()
    
    def get_enabled_models(self) -> List[Dict]:
        """获取启用的模型"""
        return [m for m in self.models if m.get("enabled", True)]
    
    def toggle_model_status(self, model_id: str) -> bool:
        """切换模型启用状态"""
        model = self.get_model(model_id)
        if model:
            model["enabled"] = not model.get("enabled", True)
            self.save_models()
            return True
        return False
    
    def test_model_connection(self, model: Dict) -> tuple[bool, str]:
        """测试模型连接"""
        try:
            headers = {
                "Authorization": f"Bearer {model['api_key']}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model["model_name"],
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            # 规范化 API URL，确保请求指向 /v1/chat/completions
            api_url = str(model["api_url"]).rstrip("/")
            if not api_url.endswith("/chat/completions"):
                if api_url.endswith("/v1"):
                    api_url = f"{api_url}/chat/completions"
                else:
                    api_url = f"{api_url}/v1/chat/completions"
            
            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "连接成功"
            else:
                # 尝试解析更详细错误
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
                return False, f"连接失败: {response.status_code} - {err_msg}"
                
        except Exception as e:
            return False, f"连接错误: {str(e)}"
    
    def duplicate_model(self, model_id: str) -> Optional[str]:
        """复制模型"""
        original_model = self.get_model(model_id)
        if original_model:
            new_model_data = original_model.copy()
            new_model_data["name"] = f"{original_model['name']} (副本)"
            del new_model_data["id"]
            del new_model_data["created_at"]
            return self.add_model(new_model_data)
        return None
    
    def export_models(self, file_path: str) -> bool:
        """导出模型配置"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.models, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def import_models(self, file_path: str, replace: bool = False) -> bool:
        """导入模型配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_models = json.load(f)
            
            if replace:
                self.models = imported_models
            else:
                # 为导入的模型生成新的ID
                for model in imported_models:
                    model["id"] = str(uuid.uuid4())
                    model["created_at"] = datetime.now().isoformat()
                self.models.extend(imported_models)
            
            self.save_models()
            return True
        except Exception:
            return False

    def _normalize_api_base(self, model: Dict) -> str:
        """从模型配置的 api_url 归一化得到以 /v1 结尾的基础地址"""
        api_url = str(model.get("api_url", "")).strip()
        if not api_url:
            raise Exception("模型配置缺少 api_url")
        url = api_url.rstrip("/")
        v1_pos = url.find("/v1")
        if v1_pos == -1:
            return url + "/v1"
        # 保留到 /v1 为止
        return url[:v1_pos + 3]

    def _get_active_model(self, provided_model: Optional[Dict] = None) -> Dict:
        """返回传入模型或首个启用的模型"""
        if provided_model:
            return provided_model
        enabled = self.get_enabled_models()
        if not enabled:
            raise Exception("没有可用的AI模型")
        return enabled[0]

    def upload_file_content(self, *args, **kwargs) -> Dict:
        """
        上传文件内容到模型提供方（兼容硅基流动 /v1/files）。
        调用兼容两种形式：
        - upload_file_content(content=..., filename=..., purpose="batch", model=...)
        - upload_file_content(model, content, filename, purpose="batch")
        返回值包含文件 id、filename、bytes。
        """
        # 解析参数
        model = kwargs.get("model")
        if len(args) >= 1 and isinstance(args[0], dict) and args[0].get("api_key"):
            model = args[0]
        content = kwargs.get("content")
        filename = kwargs.get("filename")
        if content is None and len(args) >= 2:
            content = args[1]
        if filename is None and len(args) >= 3:
            filename = args[2]
        purpose = kwargs.get("purpose", "batch")

        if not content:
            raise Exception("upload_file_content: 缺少 content")
        if not filename:
            filename = "file.txt"

        active_model = self._get_active_model(model)
        base = self._normalize_api_base(active_model)
        url = f"{base}/files"
        headers = {
            "Authorization": f"Bearer {active_model['api_key']}"
        }

        # 准备 multipart/form-data
        file_bytes = content.encode("utf-8") if isinstance(content, str) else content
        files = {
            "file": (filename, file_bytes)
        }
        data = {
            "purpose": purpose
        }

        resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
        try:
            j = resp.json()
        except Exception:
            j = {"status_code": resp.status_code, "text": resp.text}

        if resp.status_code != 200:
            # 优先取更详细错误信息
            err_msg = None
            if isinstance(j, dict):
                err_msg = (
                    (j.get("error") or {}).get("message")
                    or j.get("message")
                    or j.get("detail")
                )
            if not err_msg:
                err_msg = str(j)
            raise Exception(f"文件上传失败: {resp.status_code} - {err_msg}")

        result = j.get("data", j)
        return {
            "id": result.get("id"),
            "filename": result.get("filename", filename),
            "bytes": result.get("bytes")
        }

    def create_batch(self, file_ids: List[str], endpoint: str = "/v1/chat/completions", completion_window: str = "24h", model: Optional[Dict] = None) -> Dict:
        """
        创建批处理任务（兼容硅基流动 /v1/batches）。
        注意：硅基流动批处理要求 input_file_id 指向 JSONL 文件。
        这里使用传入的第一个 file_id 作为 input_file_id。
        """
        if not file_ids:
            raise Exception("create_batch: file_ids 不能为空")
        active_model = self._get_active_model(model)
        base = self._normalize_api_base(active_model)
        url = f"{base}/batches"
        headers = {
            "Authorization": f"Bearer {active_model['api_key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "input_file_id": file_ids[0],
            "endpoint": endpoint,
            "completion_window": completion_window
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        try:
            j = resp.json()
        except Exception:
            j = {"status_code": resp.status_code, "text": resp.text}

        if resp.status_code != 200:
            err_msg = None
            if isinstance(j, dict):
                err_msg = (
                    (j.get("error") or {}).get("message")
                    or j.get("message")
                    or j.get("detail")
                )
            if not err_msg:
                err_msg = str(j)
            raise Exception(f"创建批处理失败: {resp.status_code} - {err_msg}")

        return j.get("data", j)

    def get_batch(self, batch_id: str, model: Optional[Dict] = None) -> Dict:
        """查询批处理任务状态（兼容硅基流动 /v1/batches/{id}）"""
        if not batch_id:
            raise Exception("get_batch: batch_id 不能为空")
        active_model = self._get_active_model(model)
        base = self._normalize_api_base(active_model)
        url = f"{base}/batches/{batch_id}"
        headers = {
            "Authorization": f"Bearer {active_model['api_key']}"
        }
        resp = requests.get(url, headers=headers, timeout=30)
        try:
            j = resp.json()
        except Exception:
            j = {"status_code": resp.status_code, "text": resp.text}

        if resp.status_code != 200:
            err_msg = None
            if isinstance(j, dict):
                err_msg = (
                    (j.get("error") or {}).get("message")
                    or j.get("message")
                    or j.get("detail")
                )
            if not err_msg:
                err_msg = str(j)
            raise Exception(f"查询批处理失败: {resp.status_code} - {err_msg}")

        return j.get("data", j)
