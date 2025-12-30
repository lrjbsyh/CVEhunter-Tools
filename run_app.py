#!/usr/bin/env python3
"""
CVEhunter 启动脚本
"""

import os
import sys
import traceback
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 添加父目录到Python路径（为了导入原有的模块）
# parent_dir = current_dir.parent
# sys.path.insert(0, str(parent_dir))

def check_dependencies():
    """检查依赖项"""
    # 在打包环境中（PyInstaller frozen）略过依赖检查，避免误报导致退出
    if getattr(sys, 'frozen', False):
        print("ℹ️ 检测到已打包环境，略过依赖检查")
        return True

    required_modules = [
        'customtkinter',
        'tkinter',
        'requests',
        'PIL'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} - 已安装")
        except ImportError:
            missing_modules.append(module)
            print(f"❌ {module} - 未安装")
    
    if missing_modules:
        print(f"\n缺少以下依赖项: {', '.join(missing_modules)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("CVEhunter-新一代集成AI代码审计工具启动中...")
    print("=" * 60)
    
    # 检查依赖项
    print("\n📦 检查依赖项...")
    if not check_dependencies():
        print("\n❌ 依赖项检查失败，请安装缺少的模块")
        return False
    
    print("\n✅ 依赖项检查通过")
    
    try:
        # 导入主应用程序
        print("\n📱 导入应用程序模块...")
        from main_app import AICodeEditorApp
        
        print("✅ 模块导入成功")
        
        # 创建并运行应用程序
        print("\n🎯 启动 CVEhunter-新一代集成AI代码审计工具...")
        app = AICodeEditorApp()
        
        print("✅ 应用程序创建成功")
        print("\n🎉 CVEhunter 已启动！")
        print("=" * 60)
        
        # 运行主循环
        app.run()
        
    except ImportError as e:
        print(f"\n❌ 模块导入失败: {e}")
        print("请确保所有必要的文件都存在")
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"\n❌ 应用程序启动失败: {e}")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n👋 CVEhunter 已关闭")
        else:
            print("\n💥 启动失败")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断，正在退出...")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 未预期的错误: {e}")
        traceback.print_exc()
        sys.exit(1)