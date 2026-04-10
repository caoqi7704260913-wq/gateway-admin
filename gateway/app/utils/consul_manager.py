import consul
import threading
from typing import Optional, List, Dict, Any
from loguru import logger

from config import settings

_instance: Optional['ConsulManager'] = None
_lock: threading.Lock = threading.Lock()
_init_lock: threading.Lock = threading.Lock()


class ConsulManager:
    def __new__(cls) -> 'ConsulManager':
        global _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = super().__new__(cls)
        return _instance

    def __init__(self) -> None:
        with _init_lock:
            if hasattr(self, '_initialized') and self._initialized:
                return
            self._initialized = True
            self._cluster_enabled = settings.CONSUL_CLUSTER_ENABLED
            self._cluster_nodes: List[Dict[str, Any]] = []

            if self._cluster_enabled:
                self._init_cluster()
            else:
                self._init_standalone()

    def _init_standalone(self):
        """初始化单机模式"""
        self.client = consul.Consul(
            host=settings.CONSUL_HOST,
            port=settings.CONSUL_PORT,
            token=settings.CONSUL_TOKEN,
            scheme=settings.CONSUL_SCHEME,
            verify=settings.CONSUL_VERIFY
        )
        logger.info(f"Consul 单机模式: {settings.CONSUL_HOST}:{settings.CONSUL_PORT}")

    def _init_cluster(self):
        """初始化集群模式"""
        nodes = self._parse_cluster_nodes()
        if not nodes:
            logger.warning("Consul 集群节点为空，降级为单机模式")
            self._cluster_enabled = False
            self._init_standalone()
            return

        self._cluster_nodes = nodes
        # 使用第一个节点作为入口
        primary = nodes[0]
        self.client = consul.Consul(
            host=primary['host'],
            port=primary['port'],
            token=settings.CONSUL_TOKEN,
            scheme=settings.CONSUL_SCHEME,
            verify=settings.CONSUL_VERIFY
        )
        logger.info(f"Consul 集群模式已启用，入口节点: {primary['host']}:{primary['port']}")
        logger.info(f"Consul 集群节点: {[f'{n['host']}:{n['port']}' for n in nodes]}")

    def _parse_cluster_nodes(self) -> List[Dict[str, Any]]:
        """解析集群节点配置"""
        nodes_str = settings.CONSUL_CLUSTER_NODES or ""
        if not nodes_str.strip():
            return []

        nodes = []
        for node in nodes_str.split(','):
            node = node.strip()
            if ':' in node:
                host, port = node.rsplit(':', 1)
                try:
                    nodes.append({
                        'host': host.strip(),
                        'port': int(port.strip())
                    })
                except ValueError:
                    logger.warning(f"无效的集群节点格式: {node}")
        return nodes

    def is_cluster_mode(self) -> bool:
        """是否集群模式"""
        return self._cluster_enabled

    def get_cluster_nodes(self) -> List[Dict[str, Any]]:
        """获取集群节点列表"""
        return self._cluster_nodes.copy()

    def switch_node(self, index: int) -> bool:
        """切换到指定节点（故障转移）"""
        if not self._cluster_enabled or index >= len(self._cluster_nodes):
            return False

        node = self._cluster_nodes[index]
        self.client = consul.Consul(
            host=node['host'],
            port=node['port'],
            token=settings.CONSUL_TOKEN,
            scheme=settings.CONSUL_SCHEME,
            verify=settings.CONSUL_VERIFY
        )
        logger.info(f"已切换到 Consul 节点: {node['host']}:{node['port']}")
        return True

    def register_service(
        self,
        name: str,
        service_id: Optional[str] = None,
        address: Optional[str] = None,
        port: Optional[int] = None,
        tags: Optional[List[str]] = None,
        check: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not settings.CONSUL_ENABLED:
            logger.warning("Consul 未启用，无法注册服务")
            return False

        if service_id is None:
            if address is None or port is None:
                logger.error("注册服务时 address 和 port 不能为空")
                return False
            service_id = f"{name}-{address}:{port}"

        try:
            self.client.agent.service.register(
                name=name,
                service_id=service_id,
                address=address,
                port=port,
                tags=tags,
                check=check
            )
            logger.info(f"服务注册成功: {name} (ID: {service_id})")
            return True
        except consul.ConsulException as e:
            logger.error(f"Consul 服务注册失败: {e}")
            return False
        except Exception as e:
            logger.exception(f"服务注册时发生未知错误: {e}")
            return False

    def deregister_service(self, service_id: str) -> bool:
        if not settings.CONSUL_ENABLED:
            logger.warning("Consul 未启用，无法注销服务")
            return False

        try:
            self.client.agent.service.deregister(service_id)
            logger.info(f"服务注销成功: {service_id}")
            return True
        except consul.ConsulException as e:
            logger.error(f"Consul 服务注销失败: {e}")
            return False
        except Exception as e:
            logger.exception(f"服务注销时发生未知错误: {e}")
            return False
        
    def get_services(self) -> Dict[str, Any]:
        if not settings.CONSUL_ENABLED:
            logger.warning("Consul 未启用，无法获取服务列表")
            return {}

        try:
            services = self.client.agent.services()
            logger.info(f"获取服务列表成功，共 {len(services)} 个服务")
            return services
        except consul.ConsulException as e:
            logger.error(f"Consul 获取服务列表失败: {e}")
            return {}
        except Exception as e:
            logger.exception(f"获取服务列表时发生未知错误: {e}")
            return {}

    def update_ttl(self, service_id: str, check_type: str = "service") -> bool:
        """
        更新服务心跳 TTL（用于主动心跳机制）
        
        Args:
            service_id: 服务ID
            check_type: 检查类型，"service" 或 "serfHealth"
            
        Returns:
            是否更新成功
        """
        if not settings.CONSUL_ENABLED:
            return False
            
        try:
            check_id = f"service:{service_id}" if check_type == "service" else service_id
            # 调用 consul check ttl_pass API
            self.client.agent.check.ttl_pass(check_id)
            logger.debug(f"TTL 更新成功: {service_id}")
            return True
        except consul.ConsulException as e:
            logger.error(f"Consul TTL 更新失败: {e}")
            return False
        except Exception as e:
            logger.exception(f"TTL 更新时发生未知错误: {e}")
            return False
        
    def fail_ttl(self, service_id: str, reason: str = "") -> bool:
        """
        标记服务为不健康
        
        Args:
            service_id: 服务ID
            reason: 失败原因
            
        Returns:
            是否标记成功
        """
        if not settings.CONSUL_ENABLED:
            return False
            
        try:
            check_id = f"service:{service_id}"
            # 通过 PUT /agent/check/fail/:check_id 标记失败
            self.client.agent.check.fail(check_id, reason)  # type: ignore[attr-defined]
            logger.warning(f"服务标记为不健康: {service_id}, 原因: {reason}")
            return True
        except consul.ConsulException as e:
            logger.error(f"Consul 标记服务失败: {e}")
            return False
        except Exception as e:
            logger.exception(f"标记服务时发生未知错误: {e}")
            return False

    async def close(self) -> None:
        """关闭 Consul 连接"""
        logger.info("Consul 连接已关闭")

    def is_healthy(self) -> bool:
        """检查 Consul 健康状态"""
        if not settings.CONSUL_ENABLED:
            return False
        try:
            return self.client.agent.self() is not None
        except Exception:
            return False

def get_consul_manager() -> ConsulManager:
    return ConsulManager()


consul_manager = get_consul_manager()
