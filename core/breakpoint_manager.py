"""
断点管理器
处理大文件的分段读取和上下文管理，支持断点续传
"""

import os
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
import time


@dataclass
class FileBreakpoint:
    """文件断点信息"""
    file_path: str
    file_size: int
    file_hash: str
    total_chunks: int
    current_chunk: int
    chunk_size: int
    last_read_time: float
    context_summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileBreakpoint':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class ChunkInfo:
    """文件块信息"""
    chunk_index: int
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    content: str
    line_count: int
    char_count: int


class BreakpointManager:
    """断点管理器"""
    
    def __init__(self, max_chunk_size: int = 8000, max_context_tokens: int = 4000):
        """
        初始化断点管理器
        
        Args:
            max_chunk_size: 每个块的最大字符数
            max_context_tokens: 最大上下文令牌数（估算）
        """
        self.max_chunk_size = max_chunk_size
        self.max_context_tokens = max_context_tokens
        
        # 断点存储文件
        self.breakpoint_file = "data/breakpoints.json"
        self.ensure_data_dir()
        
        # 内存中的断点信息
        self.breakpoints: Dict[str, FileBreakpoint] = {}
        self.file_chunks: Dict[str, List[ChunkInfo]] = {}
        
        # 加载已保存的断点
        self.load_breakpoints()
        
        # 线程锁
        self.lock = threading.Lock()
    
    def ensure_data_dir(self):
        """确保数据目录存在"""
        data_dir = os.path.dirname(self.breakpoint_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
    
    def load_breakpoints(self):
        """加载保存的断点信息"""
        try:
            if os.path.exists(self.breakpoint_file):
                with open(self.breakpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for file_path, bp_data in data.items():
                        self.breakpoints[file_path] = FileBreakpoint.from_dict(bp_data)
        except Exception as e:
            print(f"加载断点信息失败: {e}")
    
    def save_breakpoints(self):
        """保存断点信息"""
        try:
            data = {}
            for file_path, breakpoint in self.breakpoints.items():
                data[file_path] = breakpoint.to_dict()
            
            with open(self.breakpoint_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存断点信息失败: {e}")
    
    def get_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5()
                chunk = f.read(8192)
                while chunk:
                    file_hash.update(chunk)
                    chunk = f.read(8192)
                return file_hash.hexdigest()
        except Exception:
            return ""
    
    def split_file_into_chunks(self, file_path: str) -> List[ChunkInfo]:
        """将文件分割成块"""
        chunks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            total_lines = len(lines)
            
            current_chunk = ""
            current_line_start = 0
            current_byte_start = 0
            chunk_index = 0
            
            for i, line in enumerate(lines):
                line_with_newline = line + '\n' if i < total_lines - 1 else line
                
                # 检查添加这一行是否会超过块大小限制
                if len(current_chunk) + len(line_with_newline) > self.max_chunk_size and current_chunk:
                    # 创建当前块
                    chunk_info = ChunkInfo(
                        chunk_index=chunk_index,
                        start_line=current_line_start + 1,  # 行号从1开始
                        end_line=i,
                        start_byte=current_byte_start,
                        end_byte=current_byte_start + len(current_chunk.encode('utf-8')),
                        content=current_chunk.rstrip('\n'),
                        line_count=i - current_line_start,
                        char_count=len(current_chunk)
                    )
                    chunks.append(chunk_info)
                    
                    # 重置为新块
                    current_chunk = line_with_newline
                    current_line_start = i
                    current_byte_start = chunk_info.end_byte
                    chunk_index += 1
                else:
                    current_chunk += line_with_newline
            
            # 添加最后一个块
            if current_chunk:
                chunk_info = ChunkInfo(
                    chunk_index=chunk_index,
                    start_line=current_line_start + 1,
                    end_line=total_lines,
                    start_byte=current_byte_start,
                    end_byte=current_byte_start + len(current_chunk.encode('utf-8')),
                    content=current_chunk.rstrip('\n'),
                    line_count=total_lines - current_line_start,
                    char_count=len(current_chunk)
                )
                chunks.append(chunk_info)
        
        except Exception as e:
            print(f"分割文件失败: {e}")
            return []
        
        return chunks
    
    def create_or_update_breakpoint(self, file_path: str) -> Optional[FileBreakpoint]:
        """创建或更新文件断点"""
        with self.lock:
            try:
                if not os.path.exists(file_path):
                    return None
                
                file_size = os.path.getsize(file_path)
                file_hash = self.get_file_hash(file_path)
                
                # 检查是否已存在断点且文件未改变
                existing_bp = self.breakpoints.get(file_path)
                if existing_bp and existing_bp.file_hash == file_hash:
                    existing_bp.last_read_time = time.time()
                    return existing_bp
                
                # 分割文件
                chunks = self.split_file_into_chunks(file_path)
                if not chunks:
                    return None
                
                # 创建新断点
                breakpoint = FileBreakpoint(
                    file_path=file_path,
                    file_size=file_size,
                    file_hash=file_hash,
                    total_chunks=len(chunks),
                    current_chunk=0,
                    chunk_size=self.max_chunk_size,
                    last_read_time=time.time()
                )
                
                # 保存断点和块信息
                self.breakpoints[file_path] = breakpoint
                self.file_chunks[file_path] = chunks
                self.save_breakpoints()
                
                return breakpoint
            
            except Exception as e:
                print(f"创建断点失败: {e}")
                return None
    
    def get_next_chunk(self, file_path: str) -> Optional[ChunkInfo]:
        """获取下一个文件块"""
        with self.lock:
            breakpoint = self.breakpoints.get(file_path)
            chunks = self.file_chunks.get(file_path)
            
            if not breakpoint or not chunks:
                return None
            
            if breakpoint.current_chunk >= breakpoint.total_chunks:
                return None
            
            chunk = chunks[breakpoint.current_chunk]
            breakpoint.current_chunk += 1
            breakpoint.last_read_time = time.time()
            
            self.save_breakpoints()
            return chunk
    
    def get_chunk_by_index(self, file_path: str, chunk_index: int) -> Optional[ChunkInfo]:
        """根据索引获取指定的文件块"""
        chunks = self.file_chunks.get(file_path)
        if chunks and 0 <= chunk_index < len(chunks):
            return chunks[chunk_index]
        return None
    
    def reset_breakpoint(self, file_path: str):
        """重置文件断点到开始位置"""
        with self.lock:
            # 完全清除文件的断点记录，强制重新创建
            if file_path in self.breakpoints:
                del self.breakpoints[file_path]
            if file_path in self.file_chunks:
                del self.file_chunks[file_path]
            self.save_breakpoints()
    
    def get_reading_progress(self, file_path: str) -> Tuple[int, int, float]:
        """获取读取进度"""
        breakpoint = self.breakpoints.get(file_path)
        if breakpoint:
            current = breakpoint.current_chunk
            total = breakpoint.total_chunks
            progress = (current / total) * 100 if total > 0 else 0
            return current, total, progress
        return 0, 0, 0.0
    
    def is_file_too_large(self, file_path: str) -> bool:
        """检查文件是否过大需要分块处理"""
        try:
            file_size = os.path.getsize(file_path)
            # 如果文件大于64KB，认为需要分块处理
            return file_size > 65536
        except Exception:
            return False
    
    def read_file_with_breakpoints(self, file_path: str, max_chunks: int = 1) -> Dict[str, Any]:
        """
        使用断点读取文件
        
        Args:
            file_path: 文件路径
            max_chunks: 一次最多读取的块数
            
        Returns:
            包含文件内容、进度信息等的字典
        """
        result = {
            'success': False,
            'content': '',
            'chunks': [],
            'current_chunk': 0,
            'total_chunks': 0,
            'progress': 0.0,
            'is_complete': False,
            'file_info': {},
            'error': None
        }
        
        try:
            # 检查文件是否需要分块处理
            if not self.is_file_too_large(file_path):
                # 小文件直接读取
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                result.update({
                    'success': True,
                    'content': content,
                    'is_complete': True,
                    'progress': 100.0,
                    'file_info': {
                        'size': len(content),
                        'lines': content.count('\n') + 1,
                        'is_large_file': False
                    }
                })
                return result
            
            # 大文件分块处理
            breakpoint = self.create_or_update_breakpoint(file_path)
            if not breakpoint:
                result['error'] = "无法创建文件断点"
                return result
            
            # 读取指定数量的块
            chunks_read = []
            content_parts = []
            
            for _ in range(max_chunks):
                chunk = self.get_next_chunk(file_path)
                if not chunk:
                    break
                
                chunks_read.append({
                    'index': chunk.chunk_index,
                    'start_line': chunk.start_line,
                    'end_line': chunk.end_line,
                    'line_count': chunk.line_count,
                    'char_count': chunk.char_count
                })
                content_parts.append(chunk.content)
            
            if chunks_read:
                current, total, progress = self.get_reading_progress(file_path)
                is_complete = current >= total
                
                result.update({
                    'success': True,
                    'content': '\n'.join(content_parts),
                    'chunks': chunks_read,
                    'current_chunk': current,
                    'total_chunks': total,
                    'progress': progress,
                    'is_complete': is_complete,
                    'file_info': {
                        'size': breakpoint.file_size,
                        'total_chunks': breakpoint.total_chunks,
                        'chunk_size': breakpoint.chunk_size,
                        'is_large_file': True
                    }
                })
            else:
                result['error'] = "没有更多内容可读取"
        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def get_file_summary(self, file_path: str) -> Dict[str, Any]:
        """获取文件摘要信息"""
        summary = {
            'file_path': file_path,
            'exists': False,
            'size': 0,
            'lines': 0,
            'is_large_file': False,
            'needs_chunking': False,
            'breakpoint_exists': False,
            'reading_progress': 0.0
        }
        
        try:
            if os.path.exists(file_path):
                summary['exists'] = True
                summary['size'] = os.path.getsize(file_path)
                summary['is_large_file'] = self.is_file_too_large(file_path)
                summary['needs_chunking'] = summary['is_large_file']
                
                # 计算行数（对于小文件）
                if not summary['is_large_file']:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        summary['lines'] = sum(1 for _ in f)
                
                # 检查断点信息
                breakpoint = self.breakpoints.get(file_path)
                if breakpoint:
                    summary['breakpoint_exists'] = True
                    _, _, progress = self.get_reading_progress(file_path)
                    summary['reading_progress'] = progress
        
        except Exception as e:
            summary['error'] = str(e)
        
        return summary
    
    def cleanup_old_breakpoints(self, max_age_days: int = 7):
        """清理过期的断点信息"""
        with self.lock:
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 3600
            
            expired_files = []
            for file_path, breakpoint in self.breakpoints.items():
                if current_time - breakpoint.last_read_time > max_age_seconds:
                    expired_files.append(file_path)
            
            for file_path in expired_files:
                del self.breakpoints[file_path]
                if file_path in self.file_chunks:
                    del self.file_chunks[file_path]
            
            if expired_files:
                self.save_breakpoints()
                print(f"清理了 {len(expired_files)} 个过期断点")
    
    def get_context_for_ai(self, file_path: str, max_context_size: int = None) -> Dict[str, Any]:
        """
        为AI获取文件上下文
        智能选择重要的代码段，避免超出上下文限制
        """
        if max_context_size is None:
            max_context_size = self.max_context_tokens * 4  # 估算字符数
        
        context = {
            'file_path': file_path,
            'content': '',
            'summary': '',
            'important_sections': [],
            'total_size': 0,
            'is_truncated': False
        }
        
        try:
            # 获取文件摘要
            file_summary = self.get_file_summary(file_path)
            if not file_summary['exists']:
                context['summary'] = "文件不存在"
                return context
            
            # 小文件直接返回全部内容
            if not file_summary['is_large_file']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                context.update({
                    'content': content,
                    'total_size': len(content),
                    'summary': f"完整文件内容 ({file_summary['lines']} 行)"
                })
                return context
            
            # 大文件智能摘要
            chunks = self.file_chunks.get(file_path)
            if not chunks:
                # 重新分析文件
                self.create_or_update_breakpoint(file_path)
                chunks = self.file_chunks.get(file_path, [])
            
            if chunks:
                # 选择重要的代码段
                important_chunks = self.select_important_chunks(chunks, max_context_size)
                
                content_parts = []
                for chunk_info in important_chunks:
                    content_parts.append(f"# 第 {chunk_info['start_line']}-{chunk_info['end_line']} 行\n{chunk_info['content']}")
                
                context.update({
                    'content': '\n\n'.join(content_parts),
                    'summary': f"文件摘要 (显示 {len(important_chunks)}/{len(chunks)} 个重要代码段)",
                    'important_sections': important_chunks,
                    'total_size': sum(len(chunk.content) for chunk in chunks),
                    'is_truncated': len(important_chunks) < len(chunks)
                })
        
        except Exception as e:
            context['summary'] = f"读取文件时出错: {e}"
        
        return context
    
    def select_important_chunks(self, chunks: List[ChunkInfo], max_size: int) -> List[Dict[str, Any]]:
        """选择重要的代码段"""
        important_chunks = []
        current_size = 0
        
        # 优先级规则：
        # 1. 包含类定义的块
        # 2. 包含函数定义的块
        # 3. 包含导入语句的块
        # 4. 其他块
        
        def get_chunk_priority(chunk: ChunkInfo) -> int:
            content = chunk.content.lower()
            priority = 0
            
            if 'class ' in content:
                priority += 100
            if 'def ' in content:
                priority += 50
            if 'import ' in content or 'from ' in content:
                priority += 30
            if 'if __name__' in content:
                priority += 20
            
            # 根据代码密度调整优先级
            lines = content.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            if lines:
                code_density = len(non_empty_lines) / len(lines)
                priority += int(code_density * 10)
            
            return priority
        
        # 按优先级排序
        sorted_chunks = sorted(chunks, key=get_chunk_priority, reverse=True)
        
        for chunk in sorted_chunks:
            chunk_info = {
                'index': chunk.chunk_index,
                'start_line': chunk.start_line,
                'end_line': chunk.end_line,
                'content': chunk.content,
                'priority': get_chunk_priority(chunk)
            }
            
            if current_size + chunk.char_count <= max_size:
                important_chunks.append(chunk_info)
                current_size += chunk.char_count
            else:
                # 如果剩余空间不足，尝试截取部分内容
                remaining_size = max_size - current_size
                if remaining_size > 500:  # 至少保留500字符
                    truncated_content = chunk.content[:remaining_size - 50] + "\n... (内容被截断)"
                    chunk_info['content'] = truncated_content
                    important_chunks.append(chunk_info)
                break
        
        # 按原始顺序重新排序
        important_chunks.sort(key=lambda x: x['index'])
        
        return important_chunks