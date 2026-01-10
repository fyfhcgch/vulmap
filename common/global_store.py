#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的全局变量管理模块
提供线程安全和类型安全的全局变量管理
"""
import threading
from typing import Any, Optional, TypeVar
from dataclasses import dataclass, field
import json
import os


T = TypeVar('T')


@dataclass
class GlobalConfig:
    """
    全局配置类
    定义所有全局配置项及其默认值
    """
    UA: str = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    TIMEOUT: int = 10
    THREADNUM: int = 10
    DELAY: float = 0.0
    VULMAP: str = '0.9'
    O_TEXT: Optional[str] = None
    O_JSON: Optional[str] = None
    CHECK: str = 'on'
    DEBUG: bool = False
    DNSLOG: str = 'auto'
    VUL: Optional[str] = None
    EXP: Optional[str] = None
    DISMAP: str = 'false'
    ceye_domain: str = ''
    ceye_token: str = ''
    hyuga_domain: str = ''
    hyuga_token: str = ''
    fofa_email: str = ''
    fofa_key: str = ''
    shodan_key: str = ''
    MD5: str = ''
    RUNALLPOC: bool = False
    HEADERS: dict = field(default_factory=dict)


class ThreadSafeGlobalStore:
    """
    线程安全的全局变量存储
    """
    
    def __init__(self):
        self._lock = threading.RLock()  # 可重入锁
        self._data = {}
        self._initialized = False
        self._default_config = GlobalConfig()
        
    def init(self):
        """初始化全局变量存储"""
        with self._lock:
            if not self._initialized:
                # 使用默认配置初始化
                config_dict = self._default_config.__dict__
                for key, value in config_dict.items():
                    self._data[key] = value
                self._initialized = True
    
    def set_value(self, key: str, value: Any):
        """
        设置全局变量值
        
        Args:
            key: 变量名
            value: 变量值
        """
        with self._lock:
            if not self._initialized:
                self.init()
            self._data[key] = value
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """
        获取全局变量值
        
        Args:
            key: 变量名
            default: 默认值
            
        Returns:
            变量值
        """
        with self._lock:
            if not self._initialized:
                self.init()
            return self._data.get(key, default)
    
    def update_values(self, values_dict: dict):
        """
        批量更新全局变量值
        
        Args:
            values_dict: 包含键值对的字典
        """
        with self._lock:
            if not self._initialized:
                self.init()
            self._data.update(values_dict)
    
    def get_all_values(self) -> dict:
        """
        获取所有全局变量值
        
        Returns:
            包含所有变量的字典
        """
        with self._lock:
            if not self._initialized:
                self.init()
            return self._data.copy()
    
    def reset(self):
        """重置所有全局变量为默认值"""
        with self._lock:
            self._data.clear()
            self._initialized = False


# 全局实例
_global_store = ThreadSafeGlobalStore()


def init():
    """初始化全局变量存储"""
    _global_store.init()


def set_value(key: str, value: Any):
    """设置全局变量值"""
    _global_store.set_value(key, value)


def get_value(key: str, def_value: Any = None) -> Any:
    """获取全局变量值"""
    return _global_store.get_value(key, def_value)


def update_values(values_dict: dict):
    """批量更新全局变量值"""
    _global_store.update_values(values_dict)


def get_all_values() -> dict:
    """获取所有全局变量值"""
    return _global_store.get_all_values()


def reset():
    """重置全局变量"""
    _global_store.reset()


class TypedGlobalStore:
    """
    类型安全的全局变量存储
    提供特定类型的变量访问方法
    """
    
    def get_string(self, key: str, default: str = '') -> str:
        """获取字符串类型的全局变量"""
        value = get_value(key, default)
        return str(value) if value is not None else default
    
    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数类型的全局变量"""
        value = get_value(key, default)
        try:
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数类型的全局变量"""
        value = get_value(key, default)
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔类型的全局变量"""
        value = get_value(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        if isinstance(value, int):
            return bool(value)
        return default
    
    def get_dict(self, key: str, default: dict = None) -> dict:
        """获取字典类型的全局变量"""
        if default is None:
            default = {}
        value = get_value(key, default)
        return value if isinstance(value, dict) else default
    
    def get_list(self, key: str, default: list = None) -> list:
        """获取列表类型的全局变量"""
        if default is None:
            default = []
        value = get_value(key, default)
        return value if isinstance(value, list) else default


# 类型安全的全局存储实例
typed_store = TypedGlobalStore()