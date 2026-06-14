# scheduler.py
# ========================================
# 资源调度脚本
# 功能：根据负载自动调整实例数量（dry-run安全模式）
# 策略：CPU利用率 > 80% 扩容，< 20% 缩容
# ========================================

import logging
from typing import Dict, List
from cloud.ecs_manager import ecs_manager

logger = logging.getLogger("MetaAgentPaaS.cloud.scheduler")


class ResourceScheduler:
    """
    简单的资源调度器
    策略：
    - CPU > 80%：建议扩容（+1实例）
    - CPU < 20%：建议缩容（-1实例）
    - 20% <= CPU <= 80%：保持不变
    """

    # 调度阈值
    SCALE_UP_THRESHOLD = 80    # CPU利用率超过此值则扩容
    SCALE_DOWN_THRESHOLD = 20  # CPU利用率低于此值则缩容
    MIN_INSTANCES = 1          # 最少保留实例数
    MAX_INSTANCES = 5          # 最大实例数

    def __init__(self):
        self.ecs = ecs_manager

    def analyze(self) -> Dict:
        """
        分析当前资源状态，生成调度建议
        返回：调度分析报告
        """
        # 1. 获取所有实例
        instances = self.ecs.list_instances()
        running_instances = [i for i in instances if i["status"] == "running"]

        # 2. 获取每个运行实例的监控数据
        monitor_data = []
        for ins in running_instances:
            data = self.ecs.get_monitor_data(ins["instance_id"])
            data["instance_name"] = ins["instance_name"]
            data["instance_type"] = ins["instance_type"]
            monitor_data.append(data)

        # 3. 计算平均CPU利用率
        if monitor_data:
            avg_cpu = sum(m["cpu_usage_avg"] for m in monitor_data) / len(monitor_data)
        else:
            avg_cpu = 0

        # 4. 生成调度建议
        recommendation = self._make_recommendation(
            avg_cpu=avg_cpu,
            current_count=len(running_instances),
        )

        return {
            "current_instances": len(running_instances),
            "running_instances": running_instances,
            "monitor_data": monitor_data,
            "avg_cpu_usage": round(avg_cpu, 2),
            "recommendation": recommendation,
            "thresholds": {
                "scale_up": self.SCALE_UP_THRESHOLD,
                "scale_down": self.SCALE_DOWN_THRESHOLD,
                "min_instances": self.MIN_INSTANCES,
                "max_instances": self.MAX_INSTANCES,
            },
        }

    def _make_recommendation(self, avg_cpu: float, current_count: int) -> Dict:
        """根据CPU利用率生成调度建议"""
        if avg_cpu > self.SCALE_UP_THRESHOLD:
            if current_count >= self.MAX_INSTANCES:
                return {
                    "action": "none",
                    "reason": f"CPU={avg_cpu:.1f}%超过阈值{self.SCALE_UP_THRESHOLD}%，但已达最大实例数{self.MAX_INSTANCES}",
                    "target_count": current_count,
                }
            return {
                "action": "scale_up",
                "reason": f"CPU={avg_cpu:.1f}%超过阈值{self.SCALE_UP_THRESHOLD}%，建议扩容",
                "target_count": current_count + 1,
                "delta": +1,
            }

        elif avg_cpu < self.SCALE_DOWN_THRESHOLD:
            if current_count <= self.MIN_INSTANCES:
                return {
                    "action": "none",
                    "reason": f"CPU={avg_cpu:.1f}%低于阈值{self.SCALE_DOWN_THRESHOLD}%，但已达最小实例数{self.MIN_INSTANCES}",
                    "target_count": current_count,
                }
            return {
                "action": "scale_down",
                "reason": f"CPU={avg_cpu:.1f}%低于阈值{self.SCALE_DOWN_THRESHOLD}%，建议缩容",
                "target_count": current_count - 1,
                "delta": -1,
            }

        else:
            return {
                "action": "none",
                "reason": f"CPU={avg_cpu:.1f}%在正常范围[{self.SCALE_DOWN_THRESHOLD}%, {self.SCALE_UP_THRESHOLD}%]，无需调整",
                "target_count": current_count,
            }

    def execute(self, dry_run: bool = True) -> Dict:
        """
        执行调度策略
        dry_run=True（默认）：仅输出建议，不实际操作
        dry_run=False：实际执行扩缩容（会产生费用！）
        """
        analysis = self.analyze()
        recommendation = analysis["recommendation"]

        if recommendation["action"] == "none":
            return {
                "executed": False,
                "dry_run": dry_run,
                "analysis": analysis,
                "message": recommendation["reason"],
            }

        if dry_run:
            action_text = "扩容" if recommendation["action"] == "scale_up" else "缩容"
            return {
                "executed": False,
                "dry_run": True,
                "analysis": analysis,
                "message": f"[预检] 建议{action_text}至{recommendation['target_count']}台实例。设置 dry_run=False 可实际执行。",
            }

        # 实际执行
        if recommendation["action"] == "scale_up":
            result = self.ecs.create_instance(
                params={
                    "instance_type": "SA2.MEDIUM4",
                    "instance_name": "MetaAgentPaaS-auto",
                    "instance_count": 1,
                },
                dry_run=False,
            )
        elif recommendation["action"] == "scale_down":
            # 找到最后一个运行实例释放
            running = analysis["running_instances"]
            if len(running) > self.MIN_INSTANCES:
                target = running[-1]
                result = self.ecs.release_instance(
                    target["instance_id"], dry_run=False
                )
            else:
                result = {"error": "无法释放，已达最小实例数"}
        else:
            result = {"message": "无需操作"}

        return {
            "executed": True,
            "dry_run": False,
            "analysis": analysis,
            "result": result,
        }


# 全局实例
scheduler = ResourceScheduler()
