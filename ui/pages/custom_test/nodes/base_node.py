"""节点抽象基类与注册机制"""

from __future__ import annotations

import uuid
import copy
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

NODE_REGISTRY: Dict[str, Type["BaseNode"]] = {}


def register_node(cls: Type["BaseNode"]) -> Type["BaseNode"]:
    """装饰器：将节点类注册到全局注册表"""
    NODE_REGISTRY[cls.node_type] = cls
    return cls


def get_node_class(node_type: str) -> Optional[Type["BaseNode"]]:
    """根据 node_type 获取节点类"""
    return NODE_REGISTRY.get(node_type)


def get_all_node_types() -> List[str]:
    """获取所有已注册的节点类型名"""
    return list(NODE_REGISTRY.keys())


def get_nodes_by_category(category: str) -> List[Type["BaseNode"]]:
    """按类别获取节点类列表"""
    return [cls for cls in NODE_REGISTRY.values() if cls.category == category]


class BaseNode(ABC):
    """所有节点的抽象基类"""

    node_type: str = ""
    display_name: str = ""
    category: str = ""
    icon: str = ""
    color: str = "#5b5cf6"

    PARAM_SCHEMA: List[Dict[str, Any]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.uid: str = kwargs.pop("uid", str(uuid.uuid4()))
        self.params: Dict[str, Any] = {}
        self.children: List["BaseNode"] = []
        for schema in self.PARAM_SCHEMA:
            key = schema["key"]
            self.params[key] = kwargs.get(key, schema.get("default"))

    @abstractmethod
    def execute(self, context: Any) -> None:
        """在执行引擎中运行该节点"""
        ...

    @property
    def accepts_children(self) -> bool:
        """是否接受子节点（循环、分支等容器节点返回 True）"""
        return False

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        data: Dict[str, Any] = {
            "node_type": self.node_type,
            "uid": self.uid,
            "params": copy.deepcopy(self.params),
        }
        if self.children:
            data["children"] = [c.to_dict() for c in self.children]
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "BaseNode":
        """从字典反序列化为节点树"""
        cls = get_node_class(data["node_type"])
        if cls is None:
            raise ValueError(f"未知节点类型: {data['node_type']}")
        node = cls(uid=data.get("uid", str(uuid.uuid4())), **data.get("params", {}))
        for child_data in data.get("children", []):
            node.children.append(BaseNode.from_dict(child_data))
        return node

    def clone(self) -> "BaseNode":
        """深拷贝节点及子节点"""
        return BaseNode.from_dict(self.to_dict())

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} uid={self.uid[:8]}>"
