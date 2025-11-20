#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CaseCheck 一键安装脚本 - 支持Windows和Mac"""

import sys
import os
import subprocess
import platform
from pathlib import Path


def check_python_version():
    """检查Python版本"""
    print("="*80)
    print("CaseCheck 系统安装向导")
    print("="*80)

    version = sys.version_info
    print(f"\nPython 版本: {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("错误: 需要 Python 3.8 或更高版本")
        sys.exit(1)

    print("✓ Python 版本检查通过")


def check_pip():
    """检查pip是否可用"""
    print("\n检查 pip...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"],
                      check=True, capture_output=True)
        print("✓ pip 可用")
        return True
    except subprocess.CalledProcessError:
        print("✗ pip 不可用")
        return False


def create_virtual_env():
    """创建虚拟环境(可选)"""
    print("\n" + "="*80)
    print("虚拟环境配置")
    print("="*80)

    use_venv = input("\n是否创建虚拟环境? (推荐) (y/N): ").strip().lower()

    if use_venv == 'y':
        venv_path = Path("venv")

        if venv_path.exists():
            print(f"虚拟环境已存在: {venv_path}")
        else:
            print(f"正在创建虚拟环境...")
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print(f"✓ 虚拟环境创建成功")

        # 提示激活命令
        system = platform.system()
        if system == "Windows":
            activate_cmd = "venv\\Scripts\\activate"
        else:
            activate_cmd = "source venv/bin/activate"

        print(f"\n请先激活虚拟环境:")
        print(f"  {activate_cmd}")
        print(f"\n然后重新运行此脚本:")
        print(f"  python setup.py")
        sys.exit(0)


def install_dependencies():
    """安装依赖包"""
    print("\n" + "="*80)
    print("安装依赖包")
    print("="*80)

    requirements_file = Path("requirements.txt")

    if not requirements_file.exists():
        print(f"错误: 未找到 requirements.txt")
        return False

    print("\n正在安装依赖包 (可能需要几分钟)...")

    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)

        print("\n✓ 依赖包安装完成")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n✗ 依赖包安装失败: {e}")
        return False


def create_directories():
    """创建必要的目录结构"""
    print("\n" + "="*80)
    print("创建目录结构")
    print("="*80)

    directories = [
        "data/database",
        "data/models",
        "data/logs",
        "data/cases"
    ]

    for dir_path in directories:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {dir_path}/")

    print("\n✓ 目录结构创建完成")


def create_env_file():
    """创建.env配置文件"""
    print("\n" + "="*80)
    print("配置环境变量")
    print("="*80)

    env_file = Path(".env")

    if env_file.exists():
        print("\n.env 文件已存在")
        overwrite = input("是否覆盖? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("保留现有配置")
            return

    print("\n请输入配置信息 (直接回车使用默认值):")

    # 获取OpenAI API Key
    openai_key = input("\nOpenAI API Key (可选,用于理论聚类): ").strip()

    # 设备配置
    print("\n计算设备:")
    print("  1. auto (自动检测)")
    print("  2. cpu  (仅CPU)")
    print("  3. cuda (NVIDIA GPU)")
    device_choice = input("选择 (默认: cpu): ").strip()

    device_map = {"1": "auto", "2": "cpu", "3": "cuda"}
    device = device_map.get(device_choice, "cpu")

    # 生成.env文件
    env_content = f"""# CaseCheck 配置文件

# OpenAI API配置 (用于理论聚类)
OPENAI_API_KEY={openai_key}

# 计算设备配置
DEVICE={device}

# 数据库配置
DATABASE_PATH=data/database/cases.db
VECTOR_DB_PATH=data/database/vectors

# 模型配置
MODEL_CACHE_DIR=data/models
BGE_MODEL_NAME=BAAI/bge-m3

# API配置
API_HOST=0.0.0.0
API_PORT=8000

# Web配置
WEB_HOST=0.0.0.0
WEB_PORT=8501

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=data/logs/app.log
"""

    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)

    print(f"\n✓ .env 文件已创建")


def download_model():
    """下载BGE-M3模型"""
    print("\n" + "="*80)
    print("模型下载")
    print("="*80)

    print("\nBGE-M3 模型大小约 4.3GB")
    download = input("是否现在下载? (y/N): ").strip().lower()

    if download == 'y':
        print("\n正在下载模型 (首次下载约600MB压缩包,解压后4.3GB)...")

        try:
            # 使用huggingface_hub下载
            from huggingface_hub import snapshot_download

            model_path = snapshot_download(
                repo_id="BAAI/bge-m3",
                cache_dir=str(Path.home() / ".cache" / "huggingface")
            )

            print(f"✓ 模型下载完成: {model_path}")

        except Exception as e:
            print(f"✗ 模型下载失败: {e}")
            print("\n模型将在首次运行时自动下载")
    else:
        print("\n⊘ 跳过模型下载 (首次运行时会自动下载)")


def check_import_data():
    """检查是否有导入的数据"""
    print("\n" + "="*80)
    print("数据导入")
    print("="*80)

    import_dir = Path("casecheck_export")

    if import_dir.exists():
        print(f"\n检测到导出数据: {import_dir}")
        do_import = input("是否导入数据? (y/N): ").strip().lower()

        if do_import == 'y':
            print("\n运行导入脚本...")
            subprocess.run([sys.executable, "import_data.py"], check=True)
        else:
            print("\n可以稍后运行 'python import_data.py' 导入数据")
    else:
        print("\n未检测到导出数据")
        print("如需导入数据:")
        print("  1. 将 'casecheck_export' 文件夹复制到项目根目录")
        print("  2. 运行: python import_data.py")


def print_completion():
    """打印完成信息"""
    print("\n" + "="*80)
    print("安装完成!")
    print("="*80)

    system = platform.system()

    print("\n启动服务:")
    print("  1. 启动API服务器:")
    print("     python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
    print("\n  2. 启动Web界面 (新终端):")
    print("     streamlit run src/web/app.py --server.port 8501")

    print("\n快速启动脚本:")
    if system == "Windows":
        print("  start_windows.bat")
    else:
        print("  ./start.sh")

    print("\n访问地址:")
    print("  Web界面: http://localhost:8501")
    print("  API文档: http://localhost:8000/docs")

    print("\n" + "="*80)


def main():
    """主函数"""
    try:
        check_python_version()
        check_pip()
        create_virtual_env()
        install_dependencies()
        create_directories()
        create_env_file()
        download_model()
        check_import_data()
        print_completion()

    except KeyboardInterrupt:
        print("\n\n安装已取消")
        sys.exit(1)

    except Exception as e:
        print(f"\n\n安装失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
