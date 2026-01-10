#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
请求频率控制模块
提供智能的请求频率限制功能
"""
import time
import threading
from collections import deque, defaultdict
from typing import Optional
import hashlib


class RateLimiter:
    """
    速率限制器
    实现基于时间窗口的请求频率控制
    """
    
    def __init__(self, max_requests: int = 10, time_window: float = 1.0, global_limit: bool = False):
        """
        初始化速率限制器
        
        Args:
            max_requests: 时间窗口内的最大请求数
            time_window: 时间窗口大小（秒）
            global_limit: 是否应用全局限制（而不是每个主机）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.global_limit = global_limit
        self.lock = threading.Lock()
        
        if global_limit:
            self.requests = deque()
        else:
            self.requests = defaultdict(lambda: deque())
    
    def can_make_request(self, host: Optional[str] = None) -> bool:
        """
        检查是否可以发起请求
        
        Args:
            host: 目标主机（如果不使用全局限制）
            
        Returns:
            是否可以发起请求
        """
        with self.lock:
            current_time = time.time()
            
            if self.global_limit:
                # 全局限制
                while self.requests and self.requests[0] <= current_time - self.time_window:
                    self.requests.popleft()
                
                return len(self.requests) < self.max_requests
            else:
                # 每主机限制
                host_requests = self.requests[host or 'default']
                while host_requests and host_requests[0] <= current_time - self.time_window:
                    host_requests.popleft()
                
                return len(host_requests) < self.max_requests
    
    def record_request(self, host: Optional[str] = None):
        """
        记录请求时间
        
        Args:
            host: 目标主机（如果不使用全局限制）
        """
        with self.lock:
            current_time = time.time()
            
            if self.global_limit:
                self.requests.append(current_time)
            else:
                self.requests[host or 'default'].append(current_time)
    
    def wait_if_needed(self, host: Optional[str] = None) -> float:
        """
        如果需要，等待直到可以发起请求
        
        Args:
            host: 目标主机（如果不使用全局限制）
            
        Returns:
            等待的时间（秒）
        """
        if self.can_make_request(host):
            self.record_request(host)
            return 0.0
        
        with self.lock:
            current_time = time.time()
            
            if self.global_limit:
                if self.requests:
                    earliest_time = self.requests[0]
                    sleep_time = max(0, earliest_time + self.time_window - current_time)
                else:
                    sleep_time = 0
            else:
                host_requests = self.requests[host or 'default']
                if host_requests:
                    earliest_time = host_requests[0]
                    sleep_time = max(0, earliest_time + self.time_window - current_time)
                else:
                    sleep_time = 0
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # 记录请求
            if self.global_limit:
                self.requests.append(current_time + sleep_time)
            else:
                self.requests[host or 'default'].append(current_time + sleep_time)
            
            return sleep_time


class AdaptiveRateLimiter:
    """
    自适应速率限制器
    根据响应情况动态调整请求频率
    """
    
    def __init__(self, initial_rate: int = 10, min_rate: int = 1, max_rate: int = 50):
        """
        初始化自适应速率限制器
        
        Args:
            initial_rate: 初始速率
            min_rate: 最小速率
            max_rate: 最大速率
        """
        self.initial_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.current_rate = initial_rate
        
        self.success_count = 0
        self.failure_count = 0
        self.window_start = time.time()
        self.window_size = 10  # 10秒窗口
        
        self.limiters = {}  # 为不同主机创建不同的限速器
        self.lock = threading.Lock()
    
    def get_limiter(self, host: str) -> RateLimiter:
        """
        获取指定主机的速率限制器
        
        Args:
            host: 目标主机
            
        Returns:
            速率限制器实例
        """
        with self.lock:
            if host not in self.limiters:
                self.limiters[host] = RateLimiter(
                    max_requests=self.current_rate,
                    time_window=1.0,
                    global_limit=False
                )
            return self.limiters[host]
    
    def report_result(self, host: str, success: bool):
        """
        报告请求结果，用于调整速率
        
        Args:
            host: 目标主机
            success: 请求是否成功
        """
        with self.lock:
            if success:
                self.success_count += 1
            else:
                self.failure_count += 1
            
            current_time = time.time()
            
            # 如果超过窗口时间，调整速率
            if current_time - self.window_start >= self.window_size:
                success_rate = self.success_count / max(1, self.success_count + self.failure_count)
                
                # 根据成功率调整速率
                if success_rate > 0.9:
                    # 成功率高，可以适当提高速率
                    self.current_rate = min(self.max_rate, int(self.current_rate * 1.1))
                elif success_rate < 0.7:
                    # 成功率低，降低速率
                    self.current_rate = max(self.min_rate, int(self.current_rate * 0.9))
                
                # 更新窗口
                self.window_start = current_time
                self.success_count = 0
                self.failure_count = 0
                
                # 更新所有限制器的速率
                for limiter in self.limiters.values():
                    limiter.max_requests = self.current_rate
    
    def wait_if_needed(self, host: str) -> float:
        """
        等待直到可以发起请求
        
        Args:
            host: 目标主机
            
        Returns:
            等待的时间
        """
        limiter = self.get_limiter(host)
        return limiter.wait_if_needed(host)


class DelayManager:
    """
    延迟管理器
    提供智能延迟功能
    """
    
    def __init__(self, base_delay: float = 0.0, jitter: float = 0.1):
        """
        初始化延迟管理器
        
        Args:
            base_delay: 基础延迟时间
            jitter: 随机抖动范围
        """
        self.base_delay = base_delay
        self.jitter = jitter
        self.host_delays = defaultdict(float)
        self.lock = threading.Lock()
    
    def get_delay(self, host: str) -> float:
        """
        获取指定主机的延迟时间
        
        Args:
            host: 目标主机
            
        Returns:
            延迟时间
        """
        import random
        with self.lock:
            host_base = self.host_delays.get(host, self.base_delay)
            return host_base + random.uniform(-self.jitter, self.jitter)
    
    def set_host_delay(self, host: str, delay: float):
        """
        为特定主机设置延迟
        
        Args:
            host: 目标主机
            delay: 延迟时间
        """
        with self.lock:
            self.host_delays[host] = delay
    
    def apply_delay(self, host: str):
        """
        应用延迟
        
        Args:
            host: 目标主机
        """
        delay = self.get_delay(host)
        if delay > 0:
            time.sleep(delay)


# 全局速率限制器实例
global_rate_limiter = AdaptiveRateLimiter(initial_rate=10, min_rate=1, max_rate=50)
global_delay_manager = DelayManager(base_delay=0.1, jitter=0.05)


def should_delay_request(host: str) -> bool:
    """
    检查是否应该延迟请求
    
    Args:
        host: 目标主机
        
    Returns:
        是否应该延迟请求
    """
    return not global_rate_limiter.get_limiter(host).can_make_request(host)


def wait_before_request(host: str) -> float:
    """
    在发起请求前等待适当时间
    
    Args:
        host: 目标主机
        
    Returns:
        等待的时间
    """
    # 应用基础延迟
    global_delay_manager.apply_delay(host)
    
    # 应用速率限制
    wait_time = global_rate_limiter.wait_if_needed(host)
    
    return wait_time


def report_request_result(host: str, success: bool):
    """
    报告请求结果
    
    Args:
        host: 目标主机
        success: 请求是否成功
    """
    global_rate_limiter.report_result(host, success)


def set_host_rate_limit(host: str, rate: int):
    """
    为特定主机设置速率限制
    
    Args:
        host: 目标主机
        rate: 速率限制
    """
    limiter = global_rate_limiter.get_limiter(host)
    with limiter.lock:
        limiter.max_requests = rate