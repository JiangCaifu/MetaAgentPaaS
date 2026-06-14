# ecs_manager.py
# ========================================
# 腾讯云ECS资源管理器
# 功能：查询实例状态、监控资源、创建/释放实例（dry-run安全模式）
# 依赖：tencentcloud-sdk-python
# ========================================

import os
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("MetaAgentPaaS.cloud")

# 腾讯云配置
TENCENT_SECRET_ID = os.getenv("TENCENT_SECRET_ID", "")
TENCENT_SECRET_KEY = os.getenv("TENCENT_SECRET_KEY", "")
TENCENT_REGION = os.getenv("TENCENT_REGION", "ap-guangzhou")


def _get_client(module: str, action: str):
    """获取腾讯云API客户端（延迟导入，避免未安装时影响主服务）"""
    try:
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile

        cred = credential.Credential(TENCENT_SECRET_ID, TENCENT_SECRET_KEY)
        httpProfile = HttpProfile()
        httpProfile.endpoint = f"{module}.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        if module == "cvm":
            from tencentcloud.cvm.v20170312 import cvm_client
            return cvm_client.CvmClient(cred, TENCENT_REGION, clientProfile)
        elif module == "monitor":
            from tencentcloud.monitor.v20180424 import monitor_client
            return monitor_client.MonitorClient(cred, TENCENT_REGION, clientProfile)
        else:
            raise ValueError(f"不支持的模块: {module}")
    except ImportError:
        logger.warning("tencentcloud-sdk-python 未安装，云资源查询功能不可用")
        return None


class ECSManager:
    """腾讯云ECS资源管理器"""

    def __init__(self):
        self.secret_id = TENCENT_SECRET_ID
        self.secret_key = TENCENT_SECRET_KEY
        self.region = TENCENT_REGION
        self._configured = bool(self.secret_id and self.secret_key)

    @property
    def is_configured(self) -> bool:
        """检查是否已配置腾讯云密钥"""
        return self._configured

    def list_instances(self) -> List[Dict]:
        """
        查询当前账号下所有CVM实例
        返回：实例信息列表
        """
        if not self._configured:
            logger.warning("腾讯云密钥未配置，返回模拟数据")
            return self._mock_instances()

        client = _get_client("cvm", "DescribeInstances")
        if not client:
            return self._mock_instances()

        try:
            from tencentcloud.cvm.v20170312 import models as cvm_models

            req = cvm_models.DescribeInstancesRequest()
            req.Limit = 100
            resp = client.DescribeInstances(req)

            instances = []
            for ins in resp.InstanceSet:
                # 提取公网IP
                public_ips = []
                if ins.PublicIpAddresses:
                    public_ips = list(ins.PublicIpAddresses)

                instances.append({
                    "instance_id": ins.InstanceId,
                    "instance_name": ins.InstanceName,
                    "instance_type": ins.InstanceType,
                    "status": self._parse_status(ins.InstanceState),
                    "cpu": ins.CPU,
                    "memory": ins.Memory,
                    "public_ips": public_ips,
                    "created_time": ins.CreatedTime,
                    "expired_time": ins.ExpiredTime,
                    "os_name": ins.OsName,
                    "region": self.region,
                })

            logger.info(f"查询到 {len(instances)} 个CVM实例")
            return instances

        except Exception as e:
            logger.error(f"查询CVM实例失败: {str(e)}")
            return self._mock_instances()

    def get_instance_detail(self, instance_id: str) -> Optional[Dict]:
        """查询指定实例详情"""
        if not self._configured:
            return self._mock_instance_detail(instance_id)

        client = _get_client("cvm", "DescribeInstances")
        if not client:
            return self._mock_instance_detail(instance_id)

        try:
            from tencentcloud.cvm.v20170312 import models as cvm_models

            req = cvm_models.DescribeInstancesRequest()
            req.InstanceIds = [instance_id]
            resp = client.DescribeInstances(req)

            if resp.InstanceSet:
                ins = resp.InstanceSet[0]
                return {
                    "instance_id": ins.InstanceId,
                    "instance_name": ins.InstanceName,
                    "instance_type": ins.InstanceType,
                    "status": self._parse_status(ins.InstanceState),
                    "cpu": ins.CPU,
                    "memory": ins.Memory,
                    "public_ips": list(ins.PublicIpAddresses or []),
                    "created_time": ins.CreatedTime,
                    "expired_time": ins.ExpiredTime,
                    "os_name": ins.OsName,
                    "region": self.region,
                }
            return None
        except Exception as e:
            logger.error(f"查询实例详情失败: {str(e)}")
            return self._mock_instance_detail(instance_id)

    def get_monitor_data(self, instance_id: str) -> Dict:
        """
        查询实例监控数据（CPU利用率、内存使用率）
        注意：腾讯云监控API需要实例的维度信息
        """
        if not self._configured:
            return self._mock_monitor_data(instance_id)

        client = _get_client("monitor", "GetMonitorData")
        if not client:
            return self._mock_monitor_data(instance_id)

        try:
            from tencentcloud.monitor.v20180424 import models as monitor_models
            import datetime

            # 查询最近5分钟的CPU利用率
            end_time = datetime.datetime.utcnow()
            start_time = end_time - datetime.timedelta(minutes=5)

            req = monitor_models.GetMonitorDataRequest()
            req.Namespace = "QCS/CVM"
            req.MetricName = "CPUUsage"
            req.Period = 60
            req.StartTime = start_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            req.EndTime = end_time.strftime("%Y-%m-%dT%H:%M:%S+00:00")

            from tencentcloud.monitor.v20180424 import models as m
            dimension = m.Dimension()
            dimension.Name = "InstanceId"
            dimension.Value = instance_id
            req.Dimensions = [dimension]

            resp = client.GetMonitorData(req)

            cpu_values = []
            for dp in resp.DataPoints:
                if dp.Values:
                    cpu_values.extend(dp.Values)

            avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0

            return {
                "instance_id": instance_id,
                "cpu_usage_avg": round(avg_cpu, 2),
                "cpu_usage_max": round(max(cpu_values), 2) if cpu_values else 0,
                "cpu_usage_min": round(min(cpu_values), 2) if cpu_values else 0,
                "data_points": len(cpu_values),
                "time_range": f"{req.StartTime} ~ {req.EndTime}",
            }

        except Exception as e:
            logger.error(f"查询监控数据失败: {str(e)}")
            return self._mock_monitor_data(instance_id)

    def create_instance(self, params: Dict, dry_run: bool = True) -> Dict:
        """
        创建CVM实例
        dry_run=True: 仅预检，不实际创建（默认安全模式）
        dry_run=False: 实际创建（会产生费用！）
        """
        if dry_run:
            logger.info(f"[DRY-RUN] 预检创建实例: {params}")
            return {
                "action": "create_instance",
                "dry_run": True,
                "status": "preview",
                "message": "预检模式：未实际创建实例。设置 dry_run=False 可实际创建（会产生费用）",
                "params": params,
                "estimated_cost": "按量付费，约0.1-0.5元/小时（2核4G配置）",
            }

        if not self._configured:
            return {"error": "腾讯云密钥未配置，无法创建实例"}

        client = _get_client("cvm", "RunInstances")
        if not client:
            return {"error": "SDK未安装，无法创建实例"}

        try:
            from tencentcloud.cvm.v20170312 import models as cvm_models

            req = cvm_models.RunInstancesRequest()
            req.InstanceType = params.get("instance_type", "SA2.MEDIUM4")
            req.ImageId = params.get("image_id", "img-8toqc6s3")  # OpenCloudOS
            req.InstanceChargeType = "POSTPAID_BY_HOUR"  # 按量付费
            req.InstanceName = params.get("instance_name", "MetaAgentPaaS-auto")
            req.InstanceCount = params.get("instance_count", 1)

            resp = client.RunInstances(req)
            instance_ids = resp.InstanceIdSet

            logger.info(f"创建实例成功: {instance_ids}")
            return {
                "action": "create_instance",
                "dry_run": False,
                "status": "created",
                "instance_ids": list(instance_ids),
                "message": f"已创建 {len(instance_ids)} 个实例",
            }

        except Exception as e:
            logger.error(f"创建实例失败: {str(e)}")
            return {"error": f"创建实例失败: {str(e)}"}

    def release_instance(self, instance_id: str, dry_run: bool = True) -> Dict:
        """
        释放/销毁CVM实例
        dry_run=True: 仅预检，不实际释放（默认安全模式）
        dry_run=False: 实际释放（实例将被删除！）
        """
        if dry_run:
            logger.info(f"[DRY-RUN] 预检释放实例: {instance_id}")
            return {
                "action": "release_instance",
                "dry_run": True,
                "status": "preview",
                "instance_id": instance_id,
                "message": "预检模式：未实际释放实例。设置 dry_run=False 可实际释放（实例将被删除！）",
            }

        if not self._configured:
            return {"error": "腾讯云密钥未配置，无法释放实例"}

        client = _get_client("cvm", "TerminateInstances")
        if not client:
            return {"error": "SDK未安装，无法释放实例"}

        try:
            from tencentcloud.cvm.v20170312 import models as cvm_models

            req = cvm_models.TerminateInstancesRequest()
            req.InstanceIds = [instance_id]

            client.TerminateInstances(req)

            logger.info(f"释放实例成功: {instance_id}")
            return {
                "action": "release_instance",
                "dry_run": False,
                "status": "released",
                "instance_id": instance_id,
                "message": f"实例 {instance_id} 已释放",
            }

        except Exception as e:
            logger.error(f"释放实例失败: {str(e)}")
            return {"error": f"释放实例失败: {str(e)}"}

    # ==============================
    # 模拟数据（未配置密钥时使用）
    # ==============================
    def _mock_instances(self) -> List[Dict]:
        """模拟实例数据（演示用）"""
        return [
            {
                "instance_id": "ins-mock001",
                "instance_name": "MetaAgentPaaS-Server",
                "instance_type": "SA2.MEDIUM4",
                "status": "running",
                "cpu": 2,
                "memory": 4096,
                "public_ips": ["101.35.251.25"],
                "created_time": "2026-05-31T00:00:00Z",
                "expired_time": "-",
                "os_name": "OpenCloudOS 9",
                "region": self.region,
            }
        ]

    def _mock_instance_detail(self, instance_id: str) -> Dict:
        return {
            "instance_id": instance_id,
            "instance_name": "MetaAgentPaaS-Server",
            "instance_type": "SA2.MEDIUM4",
            "status": "running",
            "cpu": 2,
            "memory": 4096,
            "public_ips": ["101.35.251.25"],
            "created_time": "2026-05-31T00:00:00Z",
            "expired_time": "-",
            "os_name": "OpenCloudOS 9",
            "region": self.region,
        }

    def _mock_monitor_data(self, instance_id: str) -> Dict:
        """模拟监控数据（演示用）"""
        import random
        cpu_avg = round(random.uniform(5, 35), 2)
        return {
            "instance_id": instance_id,
            "cpu_usage_avg": cpu_avg,
            "cpu_usage_max": round(cpu_avg + random.uniform(5, 15), 2),
            "cpu_usage_min": round(max(0, cpu_avg - random.uniform(3, 10)), 2),
            "data_points": 5,
            "time_range": "最近5分钟",
            "note": "模拟数据（未配置腾讯云密钥）",
        }

    @staticmethod
    def _parse_status(state: str) -> str:
        """解析实例状态"""
        status_map = {
            "RUNNING": "running",
            "STOPPED": "stopped",
            "STARTING": "starting",
            "STOPPING": "stopping",
            "REBOOTING": "rebooting",
            "SHUTDOWN": "shutdown",
            "TERMINATING": "terminating",
        }
        return status_map.get(state.upper(), state.lower())


# 全局实例
ecs_manager = ECSManager()
