#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文件交互客户端模块
移植自silicon_flow_cli.py，用于在AI代码编辑器中实现文件分析功能
"""

import os
import sys
import json
import requests
from typing import List, Dict, Any, Optional
import base64
import mimetypes


class FileInteractionClient:
    """文件交互客户端，用于向大模型发送文件和问题"""
    
    def __init__(self, model_manager=None, chat_manager=None):
        """初始化客户端
        
        Args:
            model_manager: 模型管理器实例
            chat_manager: 聊天管理器实例
        """
        self.model_manager = model_manager
        self.chat_manager = chat_manager
    
    def _is_image_file(self, file_path: str) -> bool:
        """判断是否为图片文件"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg'}
        return os.path.splitext(file_path.lower())[1] in image_extensions
    
    def _is_supported_file_type(self, file_path: str) -> bool:
        """判断是否为支持的文件类型"""
        supported_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss', '.less',
            '.json', '.xml', '.yaml', '.yml', '.md', '.txt', '.rst', '.log',
            '.c', '.cpp', '.h', '.hpp', '.java', '.cs', '.php', '.rb', '.go', 
            '.rs', '.swift', '.kt', '.scala', '.sql', '.sh', '.bat', '.ps1',
            '.dockerfile', '.gitignore', '.env', '.ini', '.cfg', '.conf', '.toml',
            '.csv', '.tsv', '.properties', '.gradle', '.maven', '.sbt'
        }
        return os.path.splitext(file_path.lower())[1] in supported_extensions
    
    def _read_file_content(self, file_path: str) -> Dict[str, Any]:
        """读取文件内容，根据文件类型返回不同格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            包含文件内容的字典，格式适用于AI模型
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 如果是目录，返回目录信息
        if os.path.isdir(file_path):
            try:
                # 递归扫描目录中的所有支持的文件
                all_files = []
                max_files_per_dir = 30  # 减少到30个文件，避免token超限
                max_content_per_file = 1400  # 每个文件最多读取1400字符
                
                for root, dirs, files in os.walk(file_path):
                    # 跳过常见的忽略目录
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                        '__pycache__', 'node_modules', 'venv', 'env', '.git', '.svn', 
                        'dist', 'build', 'out', '.next', 'target', 'bin', 'obj'
                    }]
                    
                    for file in files:
                        # 跳过隐藏文件和临时文件
                        if file.startswith('.') or file.endswith('~'):
                            continue
                        # 跳过二进制和媒体文件，但不跳过.sql文件
                        if file.lower().endswith(('.exe', '.dll', '.so', '.pyc', '.pyd', '.mp3', '.mp4', '.avi', '.mov', '.jpg', '.png', '.gif', '.zip', '.rar', '.7z')):
                            continue
                        # 只处理支持的文件类型
                        full_file_path = os.path.join(root, file)
                        if self._is_supported_file_type(full_file_path):
                            all_files.append(full_file_path)
                            if len(all_files) >= max_files_per_dir:
                                break
                    if len(all_files) >= max_files_per_dir:
                        break
                
                # 统计目录信息
                total_files = 0
                file_types = {}
                for root, dirs, files in os.walk(file_path):
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                        '__pycache__', 'node_modules', 'venv', 'env', '.git', '.svn', 
                        'dist', 'build', 'out', '.next', 'target', 'bin', 'obj'
                    }]
                    for file in files:
                        if not file.startswith('.') and not file.endswith('~'):
                            total_files += 1
                            ext = os.path.splitext(file)[1].lower()
                            file_types[ext] = file_types.get(ext, 0) + 1
                
                if not all_files:
                    # 如果没有找到合适的文件，则列出目录结构概览
                    files = os.listdir(file_path)
                    file_list = "\n".join(files[:50])  # 只显示前50个文件
                    if len(files) > 50:
                        file_list += f"\n... 共{len(files)}个文件，仅显示前50个"
                    
                    # 目录读取完成
                    return {
                        "type": "text",
                        "text": f"文件夹: {os.path.basename(file_path)}\n总文件数: {total_files}\n文件夹内容:\n```\n{file_list}\n```"
                    }
                
                # 分块并发处理文件内容（限制每个文件的内容长度）
                import concurrent.futures
                import threading
                import psutil
                
                contents = []
                file_summaries = []
                
                # 智能批次大小调整
                total_files = len(all_files)
                if total_files <= 10:
                    batch_size = total_files  # 小于10个文件直接处理
                    max_workers = 2
                elif total_files <= 30:
                    batch_size = 5  # 中等数量文件，小批次处理
                    max_workers = 3
                else:
                    batch_size = 8  # 大量文件，平衡批次大小
                    max_workers = 4
                
                # 根据系统内存调整并发数
                available_memory_gb = psutil.virtual_memory().available / (1024**3)
                if available_memory_gb < 2:
                    max_workers = min(max_workers, 2)
                    batch_size = min(batch_size, 5)
                
                # 批处理配置完成
                
                def read_file_content(file_path_item):
                    """读取单个文件内容的函数"""
                    try:
                        with open(file_path_item, 'r', encoding='utf-8') as file_handle:
                            content = file_handle.read()
                            # 限制文件内容长度
                            if len(content) > max_content_per_file:
                                content = content[:max_content_per_file] + "\n... [文件内容已截断]"
                            return {
                                'success': True,
                                'content': f"文件: {os.path.relpath(file_path_item, file_path)}\n```\n{content}\n```",
                                'summary': os.path.relpath(file_path_item, file_path)
                            }
                    except UnicodeDecodeError:
                        try:
                            with open(file_path_item, 'r', encoding='gbk') as file_handle:
                                content = file_handle.read()
                                # 限制文件内容长度
                                if len(content) > max_content_per_file:
                                    content = content[:max_content_per_file] + "\n... [文件内容已截断]"
                                return {
                                    'success': True,
                                    'content': f"文件: {os.path.relpath(file_path_item, file_path)}\n```\n{content}\n```",
                                    'summary': os.path.relpath(file_path_item, file_path)
                                }
                        except Exception:
                            return {'success': False}
                    except Exception:
                        return {'success': False}
                
                # 分批处理文件
                total_batches = (len(all_files) + batch_size - 1) // batch_size
                processed_files = 0
                failed_files = 0
                
                for i in range(0, len(all_files), batch_size):
                    batch_files = all_files[i:i + batch_size]
                    current_batch = i // batch_size + 1
                    
                    # 使用线程池并发处理当前批次
                    batch_results = []
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_file = {executor.submit(read_file_content, f): f for f in batch_files}
                        
                        for future in concurrent.futures.as_completed(future_to_file):
                            try:
                                result = future.result(timeout=30)  # 单个文件30秒超时
                                if result['success']:
                                    batch_results.append(result)
                                    processed_files += 1
                                else:
                                    failed_files += 1
                            except concurrent.futures.TimeoutError:
                                failed_files += 1
                                print(f"文件处理超时: {future_to_file[future]}", file=sys.stderr)
                            except Exception as e:
                                failed_files += 1
                                print(f"文件处理错误: {e}", file=sys.stderr)
                    
                    # 批量添加结果，减少内存碎片
                    for result in batch_results:
                        contents.append(result['content'])
                        file_summaries.append(result['summary'])
                    
                    # 清理批次结果，释放内存
                    del batch_results
                
                if not contents:
                    print(f"无法读取目录 {file_path} 中的任何文件")
                    return {
                        "type": "text",
                        "text": f"文件夹: {os.path.basename(file_path)}\n总文件数: {total_files}\n[无法读取文件夹中的任何文件]"
                    }
                
                # 构建目录摘要
                type_summary = ", ".join([f"{ext}({count}个)" for ext, count in sorted(file_types.items()) if count > 0][:10])
                
                combined_content = f"""文件夹: {os.path.basename(file_path)}
总文件数: {total_files}
文件类型分布: {type_summary}
已读取文件: {len(contents)}/{len(all_files)} (每个文件最多{max_content_per_file}字符)

{chr(10).join(contents)}"""
                
                print(f"成功读取目录: {file_path}, 读取了{len(contents)}个文件")
                return {
                    "type": "text",
                    "text": combined_content
                }
            except PermissionError:
                # 处理权限错误
                print(f"权限不足，无法读取目录: {file_path}", file=sys.stderr)
                return {
                    "type": "text",
                    "text": f"文件夹: {os.path.basename(file_path)}\n[权限不足，无法读取文件夹内容]"
                }
            except Exception as e:
                # 处理其他错误
                print(f"读取目录失败: {file_path}, 错误: {str(e)}", file=sys.stderr)
                return {
                    "type": "text",
                    "text": f"文件夹: {os.path.basename(file_path)}\n[读取文件夹失败: {str(e)}]"
                }
        
        if self._is_image_file(file_path):
            # 图片文件：转换为base64
            try:
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                    
                    # 获取MIME类型
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if not mime_type:
                        mime_type = 'image/jpeg'  # 默认类型
                    
                    print(f"成功读取图片文件: {file_path}, 大小: {len(image_data)}字节")
                    return {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                            "detail": "high"
                        }
                    }
            except PermissionError:
                print(f"权限不足，无法读取图片文件: {file_path}", file=sys.stderr)
                return {
                    "type": "text",
                    "text": f"文件名: {os.path.basename(file_path)}\n[权限不足，无法读取文件内容]"
                }
            except Exception as e:
                print(f"读取图片文件失败: {file_path}, 错误: {str(e)}", file=sys.stderr)
                return {
                    "type": "text",
                    "text": f"文件名: {os.path.basename(file_path)}\n[读取文件失败: {str(e)}]"
                }
        else:
            # 文本文件：直接读取内容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"成功读取文本文件(UTF-8): {file_path}, 内容长度: {len(content)}")
                return {
                    "type": "text",
                    "text": f"文件名: {os.path.basename(file_path)}\n文件内容:\n```\n{content}\n```"
                }
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试其他编码
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                    print(f"成功读取文本文件(GBK): {file_path}, 内容长度: {len(content)}")
                    return {
                        "type": "text", 
                        "text": f"文件名: {os.path.basename(file_path)}\n文件内容:\n```\n{content}\n```"
                    }
                except UnicodeDecodeError:
                    # 如果仍然失败，作为二进制文件处理
                    print(f"无法解码文件: {file_path}, 可能是二进制文件", file=sys.stderr)
                    return {
                        "type": "text",
                        "text": f"文件名: {os.path.basename(file_path)}\n[二进制文件，无法显示内容]"
                    }
                except PermissionError:
                    print(f"权限不足，无法读取文件: {file_path}", file=sys.stderr)
                    return {
                        "type": "text",
                        "text": f"文件名: {os.path.basename(file_path)}\n[权限不足，无法读取文件内容]"
                    }
                except Exception as e:
                    print(f"读取文件失败: {file_path}, 错误: {str(e)}", file=sys.stderr)
                    return {
                        "type": "text",
                        "text": f"文件名: {os.path.basename(file_path)}\n[读取文件失败: {str(e)}]"
                    }
            except PermissionError:
                print(f"权限不足，无法读取文件: {file_path}", file=sys.stderr)
                return {
                    "type": "text",
                    "text": f"文件名: {os.path.basename(file_path)}\n[权限不足，无法读取文件内容]"
                }
            except Exception as e:
                print(f"读取文件失败: {file_path}, 错误: {str(e)}", file=sys.stderr)
                return {
                    "type": "text",
                    "text": f"文件名: {os.path.basename(file_path)}\n[读取文件失败: {str(e)}]"
                }
    
    def send_files_with_question(self, files: List[str], question: str, model_id: str = None) -> Dict[str, Any]:
        """向AI模型发送文件和问题
        
        Args:
            files: 文件路径列表
            question: 问题内容
            model_id: 指定的模型ID，如果为None则使用默认模型
            
        Returns:
            AI模型的响应
        """
        if not self.model_manager:
            raise Exception("模型管理器未初始化")
        
        # 获取可用模型
        enabled_models = self.model_manager.get_enabled_models()
        if not enabled_models:
            raise Exception("没有可用的AI模型")
        
        # 选择模型
        model = None
        if model_id:
            model = next((m for m in enabled_models if m["id"] == model_id), None)
        if not model:
            model = enabled_models[0]
        
        # 验证模型配置
        required_keys = ["api_url", "model_name", "api_key"]
        missing = [k for k in required_keys if not str(model.get(k, "")).strip()]
        if missing:
            raise Exception(f"模型配置不完整，缺少: {', '.join(missing)}")
        
        # 读取所有文件内容
        file_contents = []
        error_messages = []
        
        print(f"准备读取{len(files)}个文件...")
        for file_path in files:
            print(f"正在读取文件: {file_path}")
            try:
                content = self._read_file_content(file_path)
                file_contents.append(content)
            except Exception as e:
                error_msg = f"读取文件失败 {file_path}: {str(e)}"
                print(error_msg, file=sys.stderr)
                error_messages.append(error_msg)
        
        # 即使没有成功读取任何文件，也不抛出异常，而是将错误信息作为内容发送
        if not file_contents and error_messages:
            file_contents.append({
                "type": "text",
                "text": f"文件读取失败:\n```\n{chr(10).join(error_messages)}\n```"
            })
        # 即使没有成功读取任何文件，也继续处理，但添加错误信息
        elif not file_contents:
            print("警告: 没有成功读取任何文件")
            file_contents = [{
                "type": "text",
                "text": "无法读取任何文件，请检查文件路径和权限。"
            }]
        
        # 构建聊天请求数据
        headers = {
            "Authorization": f"Bearer {model['api_key']}",
            "Content-Type": "application/json"
        }
        
        # 构建消息内容
        user_message_content = []
        
        # 添加问题文本
        user_message_content.append({
            "type": "text",
            "text": question
        })
        
        # 添加文件内容
        user_message_content.extend(file_contents)
        
        # 计算实际文件数量（不包括问题文本，区分文件和目录）
        file_count = 0
        dir_count = 0
        
        for content in file_contents:
            if content.get("type") == "text" and content.get("text", "").startswith("文件夹:"):
                dir_count += 1
            else:
                file_count += 1
                
        print(f"已准备好发送{len(user_message_content)}个内容项到模型，其中包含{file_count}个文件和{dir_count}个目录")
        
        # 检测是否是环境搭建指南请求
        is_env_setup_guide = any("PHPStudy测试环境搭建详细步骤" in str(content.get("text", "")) for content in user_message_content if content.get("type") == "text")
        
        # 根据请求类型选择合适的系统提示词
        if is_env_setup_guide:
            system_content = """你是一个专业的代码分析和环境搭建助手。当用户提供环境搭建指导模板时，你必须：

1. **完全按照模板执行**：严格按照用户提供的详细步骤模板进行回复，不能省略任何步骤
2. **包含所有必要步骤**：特别是数据库创建、SQL文件导入、配置文件修改等关键步骤
3. **保持模板结构**：保持原有的步骤编号、标题格式和详细说明
4. **基于文件内容分析**：结合提供的项目文件内容，给出具体的配置建议
5. **使用中文回复**：所有输出内容必须是中文

重要：如果模板中包含数据库配置步骤，你必须完整输出所有数据库相关的操作步骤，包括创建数据库、创建用户、导入SQL文件等。"""
        else:
            system_content = "你是一个专业的代码分析助手，请基于用户提供的文件回答问题。请使用中文回复，所有输出内容必须是中文。"

        wants_python_poc = ("===PY_PoC_START===" in question) or ("PoC.py" in question) or ("PoC" in question and "Python" in question)
        max_tokens = 4096 if wants_python_poc else 1024
        
        payload = {
            "model": model["model_name"],
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_message_content}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        # 规范化 API URL - 使用聊天API而不是文件上传API
        api_url = str(model["api_url"]).rstrip("/")
        
        # 确保使用聊天API端点
        if not api_url.endswith("/chat/completions"):
            if api_url.endswith("/v1"):
                api_url += "/chat/completions"
            else:
                api_url += "/v1/chat/completions"
            
        print(f"使用聊天API: {api_url}")
        
        # 发送请求到聊天API
        try:
            print(f"正在发送请求到: {api_url}")
            
            # 强制保持连接：文件交互请求统一允许最长15分钟
            dynamic_timeout = 900
            print(f"动态超时设置: {dynamic_timeout}秒 (基于{file_count}个文件, {dir_count}个目录)")
            response = requests.post(api_url, headers=headers, json=payload, timeout=dynamic_timeout)
            
            # 打印响应状态和内容
            print(f"响应状态码: {response.status_code}")
            
            response.raise_for_status()
            response_data = response.json()
            
            return response_data
            
        except requests.exceptions.Timeout as e:
            error_msg = f"API请求超时: 请求超过了{dynamic_timeout}秒的时间限制"
            print(f"请求超时: {str(e)}")
            print("建议: 1) 检查网络连接 2) 减少选择的文件数量 3) 稍后重试")
            raise Exception(error_msg)
            
        except requests.exceptions.ConnectionError as e:
            error_msg = "网络连接错误: 无法连接到API服务器"
            print(f"连接错误: {str(e)}")
            print("建议: 1) 检查网络连接 2) 确认API服务器地址正确 3) 检查防火墙设置")
            raise Exception(error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API请求失败: {str(e)}"
            print(f"请求异常: {str(e)}")
            
            if hasattr(e, "response") and e.response:
                try:
                    print(f"错误响应状态码: {e.response.status_code}")
                    print(f"错误响应内容: {e.response.text}")
                    
                    error_detail = e.response.json()
                    if "error" in error_detail:
                        error_msg += f" - {error_detail['error'].get('message', e.response.text)}"
                    else:
                        error_msg += f" - {e.response.text}"
                except Exception as json_error:
                    print(f"解析错误响应失败: {str(json_error)}")
                    error_msg += f" - {e.response.text}"
            else:
                print("请求没有收到响应")
                
            raise Exception(error_msg)
    
    def extract_response_content(self, response: Dict[str, Any]) -> str:
        """从API响应中提取内容
        
        - 兼容部分模型（如 DeepSeek-R1）返回的 `reasoning_content`
        - 优先使用 `message.content`；若为空或为占位（如“无漏洞输出”），则尝试拼接/回退到 `reasoning_content`
        """
        try:
            choices = response.get("choices") or []
            if not choices:
                raise Exception("API响应格式错误：缺少choices")
            message = choices[0].get("message") or {}
            content = (message.get("content") or "").strip()
            reasoning = (message.get("reasoning_content") or "").strip()

            # 简单占位判断：空、中文或英文“无漏洞输出”
            is_placeholder = (not content) or (content in {"无漏洞输出", "（无漏洞输出）", "(无漏洞输出)"})

            # 如果 content 非占位，直接返回
            if content and not is_placeholder:
                return content

            # 如果 content 是占位或为空，但存在 reasoning，则拼接返回，便于查看模型思路/中间产出
            if reasoning:
                return content + ("\n\n" if content else "") + reasoning

            # 两者都没有，则返回原始JSON，便于调试
            return json.dumps(response, ensure_ascii=False)
        except Exception:
            # 保底兜底
            return json.dumps(response, ensure_ascii=False)
    
    def analyze_files(self, files: List[str], question: str, model_id: str = None) -> str:
        """分析文件并返回AI回答
        
        Args:
            files: 文件路径列表
            question: 问题内容
            model_id: 指定的模型ID
            
        Returns:
            AI的回答文本
        """
        response = self.send_files_with_question(files, question, model_id)
        return self.extract_response_content(response)
        
    def interact_with_model(self, question: str, files: List[str] = None, model_id: str = None) -> str:
        """与模型交互，发送问题和文件内容"""
        try:
            # 如果没有提供文件，直接发送问题
            if not files:
                return self.send_question(question, model_id)
            
            # 发送文件和问题
            response = self.send_files_with_question(files, question, model_id)
            
            # 使用统一的解析方法，兼容 reasoning_content
            content = self.extract_response_content(response)
            return content
        except Exception as e:
            return f"与模型交互失败: {str(e)}"
    
    def get_file_summary(self, files: List[str]) -> Dict[str, Any]:
        """获取文件摘要信息
        
        Args:
            files: 文件路径列表
            
        Returns:
            文件摘要信息
        """
        summary = {
            "total_files": len(files),
            "file_types": {},
            "total_size": 0,
            "files": []
        }
        
        for file_path in files:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                file_ext = os.path.splitext(file_path)[1].lower()
                
                summary["total_size"] += file_size
                summary["file_types"][file_ext] = summary["file_types"].get(file_ext, 0) + 1
                summary["files"].append({
                    "path": file_path,
                    "name": os.path.basename(file_path),
                    "size": file_size,
                    "extension": file_ext,
                    "is_image": self._is_image_file(file_path)
                })
        
        return summary
