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

# 安装 Docker（使用系统仓库，推荐）
sudo dnf install docker docker-compose git curl -y

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker
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

### 6.2 代码更新后重新部署

当本地代码修改并推送到 Git 后，需要在服务器上重新部署。

#### 场景A：仅修改业务代码（不需要重新安装依赖）

```bash
cd /root/MetaAgentPaaS/

# 拉取最新代码
git pull

# 重新构建并启动（利用缓存，速度较快）
docker-compose up -d --build

# 查看状态
docker-compose ps -a
```

#### 场景B：修改了 requirements.txt（需要重新安装依赖）

```bash
cd /root/MetaAgentPaaS/

# 拉取最新代码
git pull

# 停止旧服务
docker-compose down

# 重新构建镜像（不使用缓存，确保依赖更新）
docker-compose build --no-cache

# 启动服务
docker-compose up -d

# 查看状态
docker-compose ps -a

# 查看日志确认启动成功
docker-compose logs app

# 清理旧镜像（释放磁盘空间）
docker system prune -a
```

#### 场景C：git pull 失败（服务器无法访问 GitHub）

国内服务器访问 GitHub 不稳定，如果 `git pull` 失败，使用 Xftp 上传修改的文件：

1. 用 Xftp 连接服务器
2. 将本地修改的文件上传到 `/root/MetaAgentPaaS/` 对应位置
3. 在服务器上重新构建：

```bash
cd /root/MetaAgentPaaS/
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

> **提示**：也可以配置 GitHub 加速镜像：`git remote set-url origin https://ghproxy.com/https://github.com/用户名/项目名.git`

### 6.3 日志查看

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

### 6.4 Docker 磁盘清理

每次 `git pull + build` 会产生旧镜像和构建缓存，长期不清理会占用大量磁盘空间。

```bash
# 查看 Docker 磁盘占用
docker system df

# 一键清理所有未使用资源（旧镜像、停止的容器、构建缓存、未使用网络）
docker system prune -a

# 只清理悬空镜像（没有标签的旧镜像，最安全）
docker image prune

# 只清理构建缓存
docker builder prune

# 只清理停止的容器
docker container prune
```

**建议**：每次更新部署后执行 `docker system prune -a` 清理旧资源，避免磁盘被占满。

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

### 7.5 Docker镜像拉取失败

**问题现象**：`docker pull` 或 `docker-compose up` 时报错 `no such host`、`502 Bad Gateway`、`Connection timed out` 等。

**原因**：国内服务器访问 Docker Hub 网络不稳定，需要配置镜像加速器和 DNS。

**解决方案**：

#### 步骤1：配置 Docker 镜像加速器和 DNS

```bash
# 编辑 Docker 配置文件
cat > /etc/docker/daemon.json << EOF
{
  "dns": ["8.8.8.8", "114.114.114.114"],
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com"
  ]
}
EOF

# 重启 Docker 服务
sudo systemctl restart docker
```

#### 步骤2：选择合适的镜像源

| 云服务商 | 镜像源地址 | 说明 |
|----------|-----------|------|
| **腾讯云** | `https://mirror.ccs.tencentyun.com` | 腾讯云服务器推荐，走内网通道 |
| 网易 | `https://hub-mirror.c.163.com` | 备选 |
| 百度 | `https://mirror.baidubce.com` | 备选 |
| 中国官方 | `https://registry.docker-cn.com` | 备选 |

> **提示**：腾讯云服务器优先使用腾讯云镜像源，内网传输速度最快最稳定。

#### 步骤3：修复 DNS 解析问题

如果镜像源域名无法解析（`no such host`），需要配置系统 DNS：

```bash
# 修改系统 DNS 配置
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 114.114.114.114" >> /etc/resolv.conf

# 重启网络服务（OpenCloudOS）
sudo systemctl restart NetworkManager

# 验证 DNS 解析
ping www.baidu.com -c 3
```

#### 步骤4：手动拉取镜像

如果 `docker-compose up` 仍然失败，可以逐个拉取镜像：

```bash
# 逐个拉取镜像
docker pull qdrant/qdrant:latest
docker pull neo4j:5.23.0

# 拉取完成后再启动服务
docker-compose up -d
```

#### 步骤5：不使用镜像源直接拉取

如果所有镜像源都不可用，可以清空镜像配置，直接访问 Docker Hub：

```bash
cat > /etc/docker/daemon.json << EOF
{
  "dns": ["8.8.8.8", "114.114.114.114"]
}
EOF

sudo systemctl restart docker
docker-compose up -d
```

### 7.6 docker-compose Bus Error

**问题现象**：执行 `docker-compose up -d` 时报 `Bus error (core dumped)`。

**原因**：系统安装的 docker-compose 二进制文件与系统不兼容。

**解决方案**：手动安装 Docker Compose：

```bash
# 卸载旧版本
sudo dnf remove docker-compose -y

# 手动下载 Docker Compose 二进制文件
curl -SL https://github.com/docker/compose/releases/download/v2.24.6/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose

# 添加执行权限
chmod +x /usr/local/bin/docker-compose

# 验证安装
docker-compose --version

# 启动服务
docker-compose up -d
```

> **提示**：也可以使用 `docker compose`（Docker Compose v2 插件）替代 `docker-compose`，两者功能相同。

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
