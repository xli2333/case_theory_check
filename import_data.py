#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""数据导入脚本 - 在新机器上恢复CaseCheck数据"""

import os
import shutil
import json
from pathlib import Path


def import_casecheck_data(import_dir: str = "casecheck_export"):
    """
    导入CaseCheck系统数据到当前机器

    Args:
        import_dir: 导入数据目录名称
    """
    print("="*80)
    print("CaseCheck 数据导入工具")
    print("="*80)

    # 获取项目根目录
    project_root = Path(__file__).parent
    import_path = project_root / import_dir

    if not import_path.exists():
        print(f"\n错误: 导入目录不存在: {import_path}")
        print("\n请确保:")
        print("  1. 已将导出的文件夹复制到项目根目录")
        print("  2. 文件夹名称为 'casecheck_export'")
        return

    print(f"\n导入目录: {import_path}")

    # 读取元数据
    metadata_file = import_path / "export_metadata.json"
    if metadata_file.exists():
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        print(f"\n导出信息:")
        print(f"  导出日期: {metadata.get('export_date', 'N/A')}")
        print(f"  版本: {metadata.get('version', 'N/A')}")
        print(f"  数据库大小: {metadata.get('database_size_mb', 0)} MB")
        print(f"  向量库大小: {metadata.get('vector_db_size_mb', 0)} MB")

    # 确认导入
    user_input = input("\n确认导入数据? (y/N): ").strip().lower()

    if user_input != 'y':
        print("导入已取消")
        return

    # 创建数据目录结构
    data_dir = project_root / "data"
    db_dir = data_dir / "database"
    db_dir.mkdir(parents=True, exist_ok=True)

    # 1. 导入SQLite数据库
    print("\n[1/4] 导入SQLite数据库...")
    db_src = import_path / "cases.db"
    db_dst = db_dir / "cases.db"

    if db_src.exists():
        # 备份现有数据库
        if db_dst.exists():
            backup_path = db_dst.with_suffix('.db.backup')
            shutil.copy2(db_dst, backup_path)
            print(f"  已备份现有数据库: {backup_path.name}")

        shutil.copy2(db_src, db_dst)
        print(f"  ✓ cases.db 已导入")
    else:
        print(f"  ✗ 未找到数据库文件")

    # 2. 导入向量数据库
    print("\n[2/4] 导入向量数据库...")
    vector_src = import_path / "vectors"
    vector_dst = db_dir / "vectors"

    if vector_src.exists():
        # 备份现有向量数据库
        if vector_dst.exists():
            backup_vector = db_dir / "vectors_backup"
            if backup_vector.exists():
                shutil.rmtree(backup_vector)
            shutil.copytree(vector_dst, backup_vector)
            print(f"  已备份现有向量库: vectors_backup/")
            shutil.rmtree(vector_dst)

        shutil.copytree(vector_src, vector_dst)
        print(f"  ✓ vectors/ 已导入")
    else:
        print(f"  ✗ 未找到向量数据库")

    # 3. 导入理论标准化映射
    print("\n[3/4] 导入理论标准化映射...")
    mapping_src = import_path / "theory_mapping.yaml"
    mapping_dst = data_dir / "theory_mapping.yaml"

    if mapping_src.exists():
        if mapping_dst.exists():
            backup_mapping = data_dir / "theory_mapping.yaml.backup"
            shutil.copy2(mapping_dst, backup_mapping)
            print(f"  已备份现有映射: theory_mapping.yaml.backup")

        shutil.copy2(mapping_src, mapping_dst)
        print(f"  ✓ theory_mapping.yaml 已导入")
    else:
        print(f"  ✗ 未找到映射文件")

    # 4. 导入BGE-M3模型 (如果存在)
    print("\n[4/4] 导入BGE-M3模型...")
    model_src = import_path / "bge_m3_model"

    if model_src.exists():
        model_cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / "models--BAAI--bge-m3"
        model_cache_dir.parent.mkdir(parents=True, exist_ok=True)

        if model_cache_dir.exists():
            print(f"  模型已存在,跳过导入")
        else:
            print(f"  正在复制模型文件 (4.3GB)...")
            shutil.copytree(model_src, model_cache_dir)
            print(f"  ✓ bge_m3_model/ 已导入")
    else:
        print(f"  ⊘ 无模型文件 (首次运行时会自动下载)")

    # 完成
    print("\n" + "="*80)
    print("数据导入完成!")
    print("="*80)
    print("\n下一步:")
    print("  1. 检查配置文件: src/config.py")
    print("  2. 启动API服务器: python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
    print("  3. 启动Web界面: streamlit run src/web/app.py --server.port 8501")
    print("="*80)


if __name__ == "__main__":
    import_casecheck_data()
