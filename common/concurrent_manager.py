#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的并发控制模块
提供动态线程池管理和资源监控功能
"""
import threading
import time
import psutil
import queue
from typing import Callable, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import logging


@dataclass
class ResourceMetrics:
    """资源指标数据类"""
    cpu_percent: float
    memory_percent: float
    active_threads: int
    queue_size: int
    timestamp: float


class DynamicThreadPool:
    """
    动态线程池
    根据系统资源使用情况动态调整线程数量
    """
    
    def __init__(self, min_workers: int = 2, max_workers: int = 20, 
                 cpu_threshold: float = 80.0, memory_threshold: float = 80.0):
        """
        初始化动态线程池
        
        Args:
            min_workers: 最小工作线程数
            max_workers: 最大工作线程数
            cpu_threshold: CPU使用率阈值（百分比）
            memory_threshold: 内存使用率阈值（百分比）
        """
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        
        self._executor: Optional[ThreadPoolExecutor] = None
        self._current_workers = min_workers
        self._lock = threading.Lock()
        self._task_queue = queue.Queue()
        self._metrics_history: List[ResourceMetrics] = []
        self._stop_event = threading.Event()
        
        # 启动资源监控线程
        self._monitor_thread = threading.Thread(target=self._resource_monitor, daemon=True)
        self._monitor_thread.start()
        
        # 初始化执行器
        self._update_executor()
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
    
    def _update_executor(self):
        """更新执行器实例"""
        with self._lock:
            if self._executor:
                self._executor.shutdown(wait=True)
            self._executor = ThreadPoolExecutor(max_workers=self._current_workers)
    
    def _resource_monitor(self):
        """资源监控线程"""
        while not self._stop_event.is_set():
            try:
                # 获取系统资源使用情况
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                active_threads = threading.active_count()
                
                # 获取队列大小
                queue_size = self._task_queue.qsize()
                
                # 记录指标
                metrics = ResourceMetrics(
                    cpu_percent=cpu_percent,
                    memory_percent=memory_percent,
                    active_threads=active_threads,
                    queue_size=queue_size,
                    timestamp=time.time()
                )
                
                self._metrics_history.append(metrics)
                
                # 保持历史记录在合理范围内
                if len(self._metrics_history) > 100:
                    self._metrics_history = self._metrics_history[-50:]
                
                # 根据资源使用情况调整线程数
                self._adjust_workers(cpu_percent, memory_percent)
                
            except Exception as e:
                self.logger.error(f"Resource monitor error: {e}")
            
            # 等待一段时间再进行下一次监控
            self._stop_event.wait(timeout=2)
    
    def _adjust_workers(self, cpu_percent: float, memory_percent: float):
        """根据资源使用情况调整工作线程数"""
        with self._lock:
            # 如果资源使用率过高，减少线程数
            if cpu_percent > self.cpu_threshold or memory_percent > self.memory_threshold:
                if self._current_workers > self.min_workers:
                    self._current_workers = max(self.min_workers, self._current_workers - 2)
                    self.logger.info(f"Reducing workers to {self._current_workers} due to high resource usage")
                    self._update_executor()
            # 如果资源使用率较低且队列中有任务，增加线程数
            elif (cpu_percent < self.cpu_threshold * 0.6 and 
                  memory_percent < self.memory_threshold * 0.6 and
                  self._task_queue.qsize() > self._current_workers):
                if self._current_workers < self.max_workers:
                    self._current_workers = min(self.max_workers, self._current_workers + 2)
                    self.logger.info(f"Increasing workers to {self._current_workers} due to low resource usage")
                    self._update_executor()
    
    def submit(self, func: Callable, *args, **kwargs) -> Any:
        """
        提交任务到线程池
        
        Args:
            func: 要执行的函数
            *args: 函数的位置参数
            **kwargs: 函数的关键字参数
            
        Returns:
            Future对象
        """
        if self._executor is None:
            self._update_executor()
        
        return self._executor.submit(func, *args, **kwargs)
    
    def map(self, func: Callable, iterable) -> List[Any]:
        """
        并行映射函数到可迭代对象
        
        Args:
            func: 要执行的函数
            iterable: 可迭代对象
            
        Returns:
            结果列表
        """
        if self._executor is None:
            self._update_executor()
        
        futures = [self._executor.submit(func, item) for item in iterable]
        results = []
        
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                self.logger.error(f"Task error: {e}")
                results.append(None)
        
        return results
    
    def get_current_metrics(self) -> ResourceMetrics:
        """获取当前资源指标"""
        if self._metrics_history:
            return self._metrics_history[-1]
        else:
            return ResourceMetrics(
                cpu_percent=psutil.cpu_percent(),
                memory_percent=psutil.virtual_memory().percent,
                active_threads=threading.active_count(),
                queue_size=0,
                timestamp=time.time()
            )
    
    def get_worker_count(self) -> int:
        """获取当前工作线程数"""
        return self._current_workers
    
    def shutdown(self, wait: bool = True):
        """关闭线程池"""
        self._stop_event.set()
        if self._executor:
            self._executor.shutdown(wait=wait)


class TaskScheduler:
    """
    任务调度器
    提供高级任务调度功能
    """
    
    def __init__(self, thread_pool: DynamicThreadPool):
        """
        初始化任务调度器
        
        Args:
            thread_pool: 动态线程池实例
        """
        self.thread_pool = thread_pool
        self._scheduled_tasks = []
        self._scheduler_lock = threading.Lock()
    
    def schedule_with_backoff(self, func: Callable, *args, max_retries: int = 3, 
                             backoff_factor: float = 1.0, **kwargs):
        """
        使用指数退避策略调度任务
        
        Args:
            func: 要执行的函数
            *args: 函数的位置参数
            max_retries: 最大重试次数
            backoff_factor: 退避因子
            **kwargs: 函数的关键字参数
        """
        for attempt in range(max_retries + 1):
            try:
                result = self.thread_pool.submit(func, *args, **kwargs).result()
                return result
            except Exception as e:
                if attempt == max_retries:
                    raise e
                
                # 指数退避等待
                wait_time = backoff_factor * (2 ** attempt)
                time.sleep(wait_time)
    
    def schedule_batch(self, tasks: List[tuple], max_concurrent: int = None) -> List[Any]:
        """
        批量调度任务
        
        Args:
            tasks: 任务列表，每个元素为(func, args, kwargs)的元组
            max_concurrent: 最大并发数
            
        Returns:
            结果列表
        """
        if max_concurrent is None:
            max_concurrent = self.thread_pool.get_worker_count()
        
        results = []
        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i:i + max_concurrent]
            batch_futures = []
            
            for func, args, kwargs in batch:
                future = self.thread_pool.submit(func, *args, **kwargs)
                batch_futures.append(future)
            
            # 等待当前批次完成
            for future in batch_futures:
                try:
                    results.append(future.result())
                except Exception as e:
                    self.thread_pool.logger.error(f"Batch task error: {e}")
                    results.append(None)
        
        return results


# 全局线程池实例
global_thread_pool = DynamicThreadPool(min_workers=2, max_workers=15, 
                                      cpu_threshold=85.0, memory_threshold=85.0)
global_scheduler = TaskScheduler(global_thread_pool)


def get_optimal_thread_count(base_count: int = 10) -> int:
    """
    获取最优线程数
    
    Args:
        base_count: 基础线程数
        
    Returns:
        优化后的线程数
    """
    metrics = global_thread_pool.get_current_metrics()
    
    # 根据CPU和内存使用率调整线程数
    if metrics.cpu_percent > 80 or metrics.memory_percent > 80:
        return max(1, base_count // 2)
    elif metrics.cpu_percent < 30 and metrics.memory_percent < 50:
        return min(50, base_count * 2)
    else:
        return base_count


def submit_task(func: Callable, *args, **kwargs):
    """
    提交任务到全局线程池
    
    Args:
        func: 要执行的函数
        *args: 函数的位置参数
        **kwargs: 函数的关键字参数
    """
    return global_scheduler.schedule_with_backoff(func, *args, **kwargs)


def shutdown_global_pool():
    """关闭全局线程池"""
    global_thread_pool.shutdown()