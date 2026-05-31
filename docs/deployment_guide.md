# MetaAgentsPaaS 部署指南

---

## 1. 环境准备

### 1.1 本地开发环境

**系统要求**：
- Windows 10/11 或 macOS/Linux
- Docker Desktop 20.10+
- Docker Compose 2.0+
- Git

**安装步骤**：
```bash
# 安装 Docker Desktop
# 下载地址：https://www.docker.com/products/docker-desktop/

# 验证安装
docker --version
docker compose version
```

### 1.2 云服务器配置

**推荐配置**：
- CPU：2核以上
- 内存：4GB以上
- 存储：40GB以上 SSD
- 带宽：1-5M

**支持的操作系统**：
- Ubuntu Server 22.04 LTS（推荐）
- CentOS 7/8 / OpenCloudOS

---

## 2. 配置文件说明

### 2.1 .env 文件配置

创建 `.env` 文件，配置必要的环境变量：

```env
# 百炼API配置（必需）
DASHSCOPE_API_KEY=your-api-key-here
DASHSCOPE_MODEL=qwen-turbo

# Qdrant向量数据库配置
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Neo4j知识图谱配置
NEO4J_HOST=neo4j
NEO4J_PORT=7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# 应用配置
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

### 2.2 docker-compose.yml 说明

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - qdrant
      - neo4j
    environment:
      - QDRANT_HOST=qdrant
      - NEO4J_HOST=neo4j

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  neo4j:
    image: neo4j:5.23.0
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
```

### 2.3 环境变量清单

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| DASHSCOPE_API_KEY | 百炼API密钥 | 必需配置 |
| DASHSCOPE_MODEL | 大模型名称 | qwen-turbo |
| QDRANT_HOST | Qdrant服务地址 | qdrant |
| QDRANT_PORT | Qdrant端口 | 6333 |
| NEO4J_HOST | Neo4j服务地址 | neo4j |
| NEO4J_PORT | Neo4j端口 | 7687 |
| NEO4J_USER | Neo4j用户名 | neo4j |
| NEO4J_PASSWORD | Neo4j密码 | password |
| LOG_LEVEL | 日志级别 | INFO |

---

## 3. 本地部署步骤

### 3.1 启动服务

```bash
# 进入项目目录
cd MetaAgentsPaaS

# 启动所有服务（后台运行）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app
```

### 3.2 验证测试

```bash
# 健康检查
curl http://localhost:8000/health

# 测试问答接口
curl -X POST http://localhost:8000/api/qa \
  -H "Content-Type: application/json" \
  -d '{"query": "北京有什么好玩的地方？"}'
```

### 3.3 停止服务

```bash
# 停止服务（保留数据）
docker-compose down

# 停止服务并删除数据卷
docker-compose down -v
```

---

## 4. 远程服务器部署

### 4.1 服务器环境配置

#### Ubuntu/Debian 系统：
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
sudo apt install docker-compose-plugin -y

# 安装 Git 和 curl
sudo apt install git curl -y
```

#### CentOS/OpenCloudOS 系统：
```bash
# 更新系统
sudo yum update -y

# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
sudo yum install docker-compose-plugin -y

# 安装 Git 和 curl
sudo yum install git curl -y
```

### 4.2 代码部署

```bash
# 克隆项目
git clone https://github.com/your-username/MetaAgentsPaaS.git
cd MetaAgentsPaaS

# 配置 .env 文件（上传本地配置好的文件）
# 使用 Xftp 上传本地的 .env 文件到服务器
```

### 4.3 服务启动

```bash
# 启动服务
docker-compose up -d

# 验证服务状态
docker-compose ps

# 测试健康检查
curl http://localhost:8000/health
```

### 4.4 安全组配置

确保服务器安全组开放以下端口：

| 端口 | 服务 | 用途 |
|------|------|------|
| 8000 | FastAPI | API服务 |
| 6333 | Qdrant | 向量数据库 |
| 7474 | Neo4j | 管理界面（可选） |
| 22 | SSH | 远程连接 |

#### Ubuntu/Debian 防火墙配置：
```bash
sudo ufw allow 8000/tcp
sudo ufw allow 6333/tcp
sudo ufw enable
```

#### CentOS/OpenCloudOS 防火墙配置：
```bash
sudo firewall-cmd --zone=public --add-port=8000/tcp --permanent
sudo firewall-cmd --zone=public --add-port=6333/tcp --permanent
sudo firewall-cmd --reload
```

---

## 5. 服务验证

### 5.1 健康检查

```bash
curl http://localhost:8000/health
# 预期响应：{"status": "healthy"}
```

### 5.2 API测试

```bash
# 测试问答接口
curl -X POST http://localhost:8000/api/qa \
  -H "Content-Type: application/json" \
  -d '{"query": "上海有什么著名景点？"}'
```

### 5.3 文档访问

| 服务 | 地址 |
|------|------|
| API服务 | http://<服务器IP>:8000 |
| API文档 | http://<服务器IP>:8000/docs |
| Qdrant控制台 | http://<服务器IP>:6333/dashboard |
| Neo4j管理界面 | http://<服务器IP>:7474 |

---

## 6. 常用命令

### 6.1 Docker Compose命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs
docker-compose logs -f app  # 实时查看app日志

# 构建镜像
docker-compose build

# 更新代码后重新部署
git pull
docker-compose up -d --build
```

### 6.2 日志查看

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs app
docker-compose logs qdrant
docker-compose logs neo4j

# 实时日志
docker-compose logs -f app
```

### 6.3 系统监控

```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
df -h

# 查看内存使用
free -h
```

---

## 7. 常见问题排查

### 7.1 端口占用

```bash
# 查看端口占用
netstat -tlnp | grep 8000

# 杀死占用进程
kill -9 <进程ID>
```

### 7.2 配置错误

```bash
# 检查.env文件配置
cat .env

# 检查容器日志
docker-compose logs app
```

### 7.3 网络问题

```bash
# 检查网络连通性
ping <服务器IP>

# 检查端口是否可访问
telnet <服务器IP> 8000

# 检查防火墙状态
sudo ufw status  # Ubuntu/Debian
sudo firewall-cmd --list-all  # CentOS
```

### 7.4 Docker服务问题

```bash
# 重启Docker服务
sudo systemctl restart docker

# 查看Docker状态
sudo systemctl status docker
```

---

## 8. 安全建议

### 8.1 禁止root直接登录（推荐）

```bash
# 修改SSH配置
sed -i 's/^PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart sshd

# 创建普通用户
useradd -m deploy
passwd deploy
usermod -aG sudo deploy
```

### 8.2 修改SSH端口（可选）

```bash
# 修改SSH端口为2222
sed -i 's/^#Port 22/Port 2222/' /etc/ssh/sshd_config
systemctl restart sshd
```

### 8.3 定期更新系统

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/OpenCloudOS
sudo yum update -y
```

---

## 附录：获取百炼API密钥

1. 访问 [阿里云百炼平台](https://dashscope.aliyun.com/)
2. 注册/登录账号
3. 进入控制台 → API密钥管理
4. 创建新的API密钥
5. 将密钥复制到 `.env` 文件的 `DASHSCOPE_API_KEY` 字段

---

**文档版本**: v1.0  
**创建时间**: 2026年5月  
**适用项目**: MetaAgentsPaaS
