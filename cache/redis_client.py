# redis_client.py
# ========================================
# Redis缓存客户端
# 功能：连接管理、缓存读写、健康检查
# 安全：未配置Redis时自动降级为内存缓存
# ========================================

import os
import json
import logging
import hashlib
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("MetaAgentPaaS.cache")

# Redis配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# 默认缓存过期时间（秒）
DEFAULT_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5分钟


class RedisCache:
    """Redis缓存管理器，支持自动降级为内存缓存"""

    def __init__(self):
        self._client = None
        self._available = False
        self._memory_cache = {}  # 内存缓存降级方案
        self._init_client()

    def _init_client(self):
        """初始化Redis连接"""
        try:
            import redis
            self._client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD if REDIS_PASSWORD else None,
                db=REDIS_DB,
                socket_timeout=3,
                socket_connect_timeout=3,
                decode_responses=True,
            )
            # 测试连接
            self._client.ping()
            self._available = True
            logger.info(f"✅ Redis连接成功：{REDIS_HOST}:{REDIS_PORT}")
        except ImportError:
            logger.warning("⚠️ redis包未安装，使用内存缓存降级方案")
            self._available = False
        except Exception as e:
            logger.warning(f"⚠️ Redis连接失败：{str(e)}，使用内存缓存降级方案")
            self._available = False

    @property
    def is_available(self) -> bool:
        """Redis是否可用"""
        if not self._available:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            self._available = False
            return False

    @staticmethod
    def make_key(prefix: str, *args) -> str:
        """生成缓存键"""
        raw = ":".join(str(a) for a in args)
        if len(raw) > 100:
            # 长键名用hash缩短
            hashed = hashlib.md5(raw.encode()).hexdigest()[:12]
            return f"{prefix}:{hashed}"
        return f"{prefix}:{raw}"

    def get(self, key: str) -> Optional[str]:
        """读取缓存"""
        if self.is_available:
            try:
                return self._client.get(key)
            except Exception as e:
                logger.warning(f"Redis读取失败：{str(e)}")
                return None
        # 内存缓存降级
        entry = self._memory_cache.get(key)
        if entry is None:
            return None
        import time
        if entry["expires"] and time.time() > entry["expires"]:
            del self._memory_cache[key]
            return None
        return entry["value"]

    def get_json(self, key: str) -> Optional[Any]:
        """读取JSON缓存"""
        raw = self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def set(self, key: str, value: str, ttl: int = DEFAULT_TTL) -> bool:
        """写入缓存"""
        if self.is_available:
            try:
                self._client.setex(key, ttl, value)
                return True
            except Exception as e:
                logger.warning(f"Redis写入失败：{str(e)}")
                return False
        # 内存缓存降级
        import time
        self._memory_cache[key] = {
            "value": value,
            "expires": time.time() + ttl if ttl > 0 else None,
        }
        return True

    def set_json(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """写入JSON缓存"""
        return self.set(key, json.dumps(value, ensure_ascii=False), ttl)

    def delete(self, key: str) -> bool:
        """删除缓存"""
        if self.is_available:
            try:
                self._client.delete(key)
                return True
            except Exception as e:
                logger.warning(f"Redis删除失败：{str(e)}")
                return False
        self._memory_cache.pop(key, None)
        return True

    def delete_pattern(self, pattern: str) -> int:
        """按模式删除缓存（如 cache:tourism:*）"""
        if self.is_available:
            try:
                keys = self._client.keys(pattern)
                if keys:
                    return self._client.delete(*keys)
                return 0
            except Exception as e:
                logger.warning(f"Redis模式删除失败：{str(e)}")
                return 0
        # 内存缓存降级
        count = 0
        prefix = pattern.replace("*", "")
        to_delete = [k for k in self._memory_cache if k.startswith(prefix)]
        for k in to_delete:
            del self._memory_cache[k]
            count += 1
        return count

    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        if self.is_available:
            try:
                info = self._client.info("stats")
                return {
                    "backend": "redis",
                    "host": REDIS_HOST,
                    "port": REDIS_PORT,
                    "keys_count": self._client.dbsize(),
                    "hits": info.get("keyspace_hits", 0),
                    "misses": info.get("keyspace_misses", 0),
                    "hit_rate": round(
                        info.get("keyspace_hits", 0)
                        / max(
                            info.get("keyspace_hits", 0)
                            + info.get("keyspace_misses", 1),
                            1,
                        )
                        * 100,
                        2,
                    ),
                    "memory_used": info.get("used_memory_human", "N/A"),
                }
            except Exception as e:
                logger.warning(f"Redis统计获取失败：{str(e)}")

        # 内存缓存统计
        import time
        now = time.time()
        valid_keys = [
            k
            for k, v in self._memory_cache.items()
            if not v["expires"] or now < v["expires"]
        ]
        return {
            "backend": "memory",
            "host": "localhost",
            "port": "-",
            "keys_count": len(valid_keys),
            "hits": 0,
            "misses": 0,
            "hit_rate": 0,
            "memory_used": "N/A",
        }

    def clear_all(self) -> bool:
        """清空所有缓存"""
        if self.is_available:
            try:
                self._client.flushdb()
                return True
            except Exception as e:
                logger.warning(f"Redis清空失败：{str(e)}")
                return False
        self._memory_cache.clear()
        return True


# 全局实例
redis_cache = RedisCache()
