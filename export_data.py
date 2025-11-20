#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""数据打包导出脚本 - 支持完整的系统迁移"""

import os
import sys
import shutil
import tarfile
import json
from pathlib import Path
from datetime import datetime

# 设置Windows命令行UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass


def export_casecheck_data(output_dir: str = "casecheck_export"):
    """
    导出CaseCheck系统的所有数据

    包含:
    1. SQLite数据库 (cases.db)
    2. 向量数据库 (ChromaDB)
    3. 理论标准化映射文件 (theory_mapping.yaml)
    4. BGE-M3模型文件 (可选,4.3GB)

    Args:
        output_dir: 输出目录名称
    """
    print("="*80)
    print("CaseCheck 数据打包导出工具")
    print("="*80)

    # 获取项目根目录
    project_root = Path(__file__).parent
    export_path = project_root / output_dir

    # 创建导出目录
    export_path.mkdir(exist_ok=True)
    print(f"\n导出目录: {export_path}")

    # 1. 导出SQLite数据库
    print("\n[1/5] 导出SQLite数据库...")
    db_src = project_root / "data" / "database" / "cases.db"
    db_dst = export_path / "cases.db"

    if db_src.exists():
        shutil.copy2(db_src, db_dst)
        db_size = db_dst.stat().st_size / (1024 * 1024)
        print(f"  ✓ cases.db ({db_size:.2f} MB)")
    else:
        print(f"  ✗ 未找到数据库: {db_src}")

    # 2. 导出向量数据库
    print("\n[2/5] 导出向量数据库 (ChromaDB)...")
    vector_src = project_root / "data" / "database" / "vectors"
    vector_dst = export_path / "vectors"

    if vector_src.exists():
        if vector_dst.exists():
            shutil.rmtree(vector_dst)
        shutil.copytree(vector_src, vector_dst)

        # 计算向量数据库大小
        total_size = sum(f.stat().st_size for f in vector_dst.rglob('*') if f.is_file())
        vector_size = total_size / (1024 * 1024)
        print(f"  ✓ vectors/ ({vector_size:.2f} MB)")
    else:
        print(f"  ✗ 未找到向量数据库: {vector_src}")

    # 3. 导出理论标准化映射
    print("\n[3/5] 导出理论标准化映射...")
    mapping_src = project_root / "data" / "theory_mapping.yaml"
    mapping_dst = export_path / "theory_mapping.yaml"

    if mapping_src.exists():
        shutil.copy2(mapping_src, mapping_dst)
        mapping_size = mapping_dst.stat().st_size / 1024
        print(f"  ✓ theory_mapping.yaml ({mapping_size:.2f} KB)")
    else:
        print(f"  ✗ 未找到映射文件: {mapping_src}")

    # 4. 导出BGE-M3模型 (可选)
    print("\n[4/5] 导出BGE-M3模型...")
    print("  模型文件较大 (4.3GB), 建议在新机器上自动下载")

    user_input = input("  是否导出模型文件? (y/N): ").strip().lower()

    if user_input == 'y':
        model_cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / "models--BAAI--bge-m3"
        model_dst = export_path / "bge_m3_model"

        if model_cache_dir.exists():
            print(f"  正在复制模型 (4.3GB)...")
            shutil.copytree(model_cache_dir, model_dst)
            model_size = sum(f.stat().st_size for f in model_dst.rglob('*') if f.is_file())
            model_size_gb = model_size / (1024 * 1024 * 1024)
            print(f"  ✓ bge_m3_model/ ({model_size_gb:.2f} GB)")
        else:
            print(f"  ✗ 未找到模型缓存: {model_cache_dir}")
    else:
        print("  ⊘ 跳过模型导出 (将在新机器上自动下载)")

    # 5. 生成元数据
    print("\n[5/5] 生成元数据...")
    metadata = {
        "export_date": datetime.now().isoformat(),
        "project_name": "CaseCheck",
        "version": "1.0.0",
        "database_size_mb": round(db_size, 2) if db_src.exists() else 0,
        "vector_db_size_mb": round(vector_size, 2) if vector_src.exists() else 0,
        "theory_mapping_size_kb": round(mapping_size, 2) if mapping_src.exists() else 0,
        "model_exported": user_input == 'y',
        "notes": [
            "数据库包含119个案例和375个理论",
            "向量数据库包含94个案例的语义向量",
            "理论映射包含309个标准化理论名称",
            "如未导出模型,首次运行时会自动下载 (约600MB)"
        ]
    }

    metadata_file = export_path / "export_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"  ✓ export_metadata.json")

    # 6. 创建压缩包 (可选)
    print("\n" + "="*80)
    print("数据导出完成!")
    print("="*80)
    print(f"\n导出位置: {export_path}")

    # 计算总大小
    total_export_size = sum(f.stat().st_size for f in export_path.rglob('*') if f.is_file())
    total_size_mb = total_export_size / (1024 * 1024)
    print(f"总大小: {total_size_mb:.2f} MB")

    # 询问是否压缩
    compress_input = input("\n是否创建压缩包? (y/N): ").strip().lower()

    if compress_input == 'y':
        print("\n正在创建压缩包...")
        archive_name = f"casecheck_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
        archive_path = project_root / archive_name

        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(export_path, arcname=output_dir)

        archive_size = archive_path.stat().st_size / (1024 * 1024)
        print(f"  ✓ 压缩包: {archive_name} ({archive_size:.2f} MB)")
        print(f"  位置: {archive_path}")

    print("\n" + "="*80)
    print("下一步:")
    print("  1. 将导出文件夹复制到新电脑")
    print("  2. 在新电脑上运行 setup.py 或 setup.sh")
    print("  3. 运行 import_data.py 导入数据")
    print("="*80)


if __name__ == "__main__":
    export_casecheck_data()
