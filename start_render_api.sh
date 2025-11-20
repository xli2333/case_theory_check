#!/bin/bash

# Render 部署启动脚本 - Backend API
# 用于初始化持久化存储中的数据

# 持久化磁盘挂载路径
DATA_DIR="/var/data"

# 代码库中的原始数据路径
SRC_DATA_DIR="./data"

echo "=== Starting Render Deployment Setup ==="
echo "Data Persistence Directory: $DATA_DIR"

# 1. 创建必要的目录结构
echo "Ensure directories exist..."
mkdir -p "$DATA_DIR/database"
mkdir -p "$DATA_DIR/logs"
mkdir -p "$DATA_DIR/models"

# 2. 检查并初始化 SQLite 数据库
if [ ! -f "$DATA_DIR/database/cases.db" ]; then
    echo "Initializing database from source..."
    if [ -f "$SRC_DATA_DIR/database/cases.db" ]; then
        cp "$SRC_DATA_DIR/database/cases.db" "$DATA_DIR/database/cases.db"
        echo "Database initialized."
    else
        echo "WARNING: Source database not found at $SRC_DATA_DIR/database/cases.db"
    fi
else
    echo "Database already exists in persistence storage."
fi

# 3. 检查并初始化向量数据库 (目录)
if [ ! -d "$DATA_DIR/database/vectors" ]; then
    echo "Initializing vector database from source..."
    if [ -d "$SRC_DATA_DIR/database/vectors" ]; then
        cp -r "$SRC_DATA_DIR/database/vectors" "$DATA_DIR/database/"
        echo "Vector database initialized."
    else
        echo "WARNING: Source vectors not found at $SRC_DATA_DIR/database/vectors"
    fi
else
    echo "Vector database already exists in persistence storage."
fi

# 4. 检查并初始化理论映射文件
if [ ! -f "$DATA_DIR/theory_mapping.yaml" ]; then
    echo "Initializing theory mapping from source..."
    if [ -f "$SRC_DATA_DIR/theory_mapping.yaml" ]; then
        cp "$SRC_DATA_DIR/theory_mapping.yaml" "$DATA_DIR/theory_mapping.yaml"
        echo "Theory mapping initialized."
    else
        echo "WARNING: Source theory mapping not found at $SRC_DATA_DIR/theory_mapping.yaml"
    fi
else
    echo "Theory mapping already exists in persistence storage."
fi

echo "=== Setup Complete. Starting Uvicorn... ==="

# 启动 FastAPI 服务
# 注意: Render 会自动注入 $PORT 环境变量
exec uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
