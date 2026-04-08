# 备份与恢复指南

## 数据库备份

### 手动备份

```bash
cd backend
./scripts/backup_db.sh
```

备份文件保存在 `backend/backups/` 目录，格式：`backup_tomato_fiction_YYYYMMDD_HHMMSS.sql.gz`

### 自动备份（Cron）

添加到 crontab：

```bash
# 每天凌晨 3 点自动备份
0 3 * * * cd /path/to/fqxs/backend && ./scripts/backup_db.sh >> logs/backup.log 2>&1
```

### 环境变量配置

```bash
export BACKUP_DIR="./backups"
export DB_HOST="localhost"
export DB_PORT="3306"
export DB_NAME="tomato_fiction"
export DB_USER="root"
export DB_PASSWORD="rootpassword"
export RETENTION_DAYS="7"  # 保留最近 7 天的备份
```

## 数据库恢复

### 查看可用备份

```bash
cd backend
./scripts/restore_db.sh
```

### 恢复指定备份

```bash
cd backend
./scripts/restore_db.sh backups/backup_tomato_fiction_20260408_030000.sql.gz
```

恢复前会要求确认，输入 `yes` 继续。

## Redis 备份

Redis 使用 RDB 持久化，数据文件位于 `/var/lib/redis/dump.rdb`（Docker 容器内）。

### 手动触发 Redis 备份

```bash
docker exec -it redis redis-cli BGSAVE
```

### 复制 Redis 数据文件

```bash
docker cp redis:/data/dump.rdb ./backups/redis_dump_$(date +%Y%m%d_%H%M%S).rdb
```

## 完整系统备份

### 备份清单

1. MySQL 数据库（使用 `backup_db.sh`）
2. Redis 数据文件
3. 上传的文件（如果有）
4. 配置文件（`.env`）

### 备份脚本示例

```bash
#!/bin/bash
BACKUP_ROOT="./full_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_ROOT"

# 1. 备份数据库
./scripts/backup_db.sh
cp backups/backup_tomato_fiction_*.sql.gz "$BACKUP_ROOT/"

# 2. 备份 Redis
docker cp redis:/data/dump.rdb "$BACKUP_ROOT/redis_dump.rdb"

# 3. 备份配置
cp .env "$BACKUP_ROOT/.env.backup"

# 4. 打包
tar -czf "${BACKUP_ROOT}.tar.gz" "$BACKUP_ROOT"
rm -rf "$BACKUP_ROOT"

echo "Full backup completed: ${BACKUP_ROOT}.tar.gz"
```

## 灾难恢复流程

### 1. 恢复数据库

```bash
cd backend
./scripts/restore_db.sh backups/backup_tomato_fiction_YYYYMMDD_HHMMSS.sql.gz
```

### 2. 恢复 Redis

```bash
docker cp backups/redis_dump.rdb redis:/data/dump.rdb
docker restart redis
```

### 3. 重启服务

```bash
docker-compose restart
```

### 4. 验证数据

- 登录系统检查用户数据
- 检查项目和章节数据
- 验证统计数据

## 备份策略建议

- **每日备份**: 凌晨 3 点自动备份数据库
- **保留周期**: 保留最近 7 天的每日备份
- **每周备份**: 每周日进行完整系统备份，保留 4 周
- **异地备份**: 定期将备份文件上传到云存储（S3/OSS）

## 监控备份状态

检查最近的备份：

```bash
ls -lh backend/backups/ | tail -10
```

验证备份完整性：

```bash
gunzip -t backend/backups/backup_tomato_fiction_YYYYMMDD_HHMMSS.sql.gz
```
