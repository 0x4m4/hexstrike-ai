from prometheus_client import Counter, Gauge, Histogram, generate_latest
import psutil
import time

# Define metrics
commands_executed = Counter('hexstrike_commands_executed_total', 'Total commands executed')
command_duration = Histogram('hexstrike_command_duration_seconds', 'Command execution time')
active_processes = Gauge('hexstrike_active_processes', 'Number of active processes')
cpu_usage = Gauge('hexstrike_cpu_percent', 'CPU usage percentage')
memory_usage = Gauge('hexstrike_memory_percent', 'Memory usage percentage')
cache_hits = Counter('hexstrike_cache_hits_total', 'Cache hit count')
cache_misses = Counter('hexstrike_cache_misses_total', 'Cache miss count')
success_rate = Gauge('hexstrike_success_rate', 'Success rate percentage')
cache_hit_rate = Gauge('hexstrike_cache_hit_rate', 'Cache hit rate percentage')

def update_system_metrics():
    """Update system metrics"""
    cpu_usage.set(psutil.cpu_percent(interval=1))
    memory_usage.set(psutil.virtual_memory().percent)

def get_metrics():
    """Return prometheus metrics"""
    update_system_metrics()
    return generate_latest()