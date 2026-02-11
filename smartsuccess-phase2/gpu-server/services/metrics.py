"""
GPU Server Metrics Service
Tracks request counts, latencies, errors, and GPU resource usage.

Provides data for /health and /metrics endpoints.
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Any

import torch


@dataclass
class EndpointStats:
    """Per-endpoint statistics."""
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0
    last_request_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_error_time: Optional[float] = None
    last_error_message: Optional[str] = None

    @property
    def avg_latency_ms(self) -> float:
        if self.success_count == 0:
            return 0.0
        return self.total_latency_ms / self.success_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_count": self.request_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "min_latency_ms": round(self.min_latency_ms, 2) if self.min_latency_ms != float("inf") else None,
            "max_latency_ms": round(self.max_latency_ms, 2) if self.max_latency_ms > 0 else None,
            "last_request_time": self.last_request_time,
            "last_success_time": self.last_success_time,
            "last_error_time": self.last_error_time,
            "last_error_message": self.last_error_message,
        }


class MetricsCollector:
    """
    Thread-safe metrics collector for the GPU server.

    Usage:
        metrics = MetricsCollector()
        metrics.record_request("/api/stt/transcribe", latency_ms=320.5, success=True)
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._endpoints: Dict[str, EndpointStats] = defaultdict(EndpointStats)
        self._server_start_time: float = time.time()

    # ---- Recording ----

    def record_request(
        self,
        endpoint: str,
        latency_ms: float,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """Record a completed request."""
        now = time.time()
        with self._lock:
            stats = self._endpoints[endpoint]
            stats.request_count += 1
            stats.last_request_time = now

            if success:
                stats.success_count += 1
                stats.total_latency_ms += latency_ms
                stats.min_latency_ms = min(stats.min_latency_ms, latency_ms)
                stats.max_latency_ms = max(stats.max_latency_ms, latency_ms)
                stats.last_success_time = now
            else:
                stats.error_count += 1
                stats.last_error_time = now
                stats.last_error_message = error_message

    # ---- GPU Metrics ----

    @staticmethod
    def get_gpu_metrics() -> Dict[str, Any]:
        """Collect real-time GPU metrics via PyTorch CUDA APIs."""
        if not torch.cuda.is_available():
            return {"available": False}

        try:
            device = torch.cuda.current_device()
            props = torch.cuda.get_device_properties(device)
            total_mem = props.total_mem if hasattr(props, "total_mem") else props.total_memory
            allocated = torch.cuda.memory_allocated(device)
            reserved = torch.cuda.memory_reserved(device)

            # GPU utilization via nvidia-smi (best-effort)
            utilization = MetricsCollector._get_gpu_utilization()

            return {
                "available": True,
                "device_name": props.name,
                "cuda_version": torch.version.cuda or "unknown",
                "driver_version": MetricsCollector._get_driver_version(),
                "memory": {
                    "total_gb": round(total_mem / (1024 ** 3), 2),
                    "allocated_gb": round(allocated / (1024 ** 3), 2),
                    "reserved_gb": round(reserved / (1024 ** 3), 2),
                    "free_gb": round((total_mem - allocated) / (1024 ** 3), 2),
                    "utilization_pct": round(allocated / total_mem * 100, 1) if total_mem > 0 else 0,
                },
                "gpu_utilization_pct": utilization,
                "temperature_c": MetricsCollector._get_gpu_temperature(),
            }
        except Exception as e:
            return {"available": True, "error": str(e)}

    @staticmethod
    def _get_gpu_utilization() -> Optional[float]:
        """Get GPU compute utilization percentage via nvidia-smi."""
        try:
            import subprocess

            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return float(result.stdout.strip().split("\n")[0])
        except Exception:
            pass
        return None

    @staticmethod
    def _get_gpu_temperature() -> Optional[float]:
        """Get GPU temperature via nvidia-smi."""
        try:
            import subprocess

            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return float(result.stdout.strip().split("\n")[0])
        except Exception:
            pass
        return None

    @staticmethod
    def _get_driver_version() -> str:
        """Get NVIDIA driver version."""
        try:
            import subprocess

            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return "unknown"

    # ---- Aggregation ----

    def get_uptime_seconds(self) -> float:
        return round(time.time() - self._server_start_time, 1)

    def get_endpoint_stats(self) -> Dict[str, Dict[str, Any]]:
        """Return per-endpoint stats."""
        with self._lock:
            return {ep: stats.to_dict() for ep, stats in self._endpoints.items()}

    def get_summary(self) -> Dict[str, Any]:
        """Return aggregated summary across all endpoints."""
        with self._lock:
            total_requests = sum(s.request_count for s in self._endpoints.values())
            total_success = sum(s.success_count for s in self._endpoints.values())
            total_errors = sum(s.error_count for s in self._endpoints.values())

            # Last success across any endpoint
            success_times = [
                s.last_success_time
                for s in self._endpoints.values()
                if s.last_success_time is not None
            ]
            last_success = max(success_times) if success_times else None

            # Service-level aggregation
            service_stats = {}
            for ep, stats in self._endpoints.items():
                if ep.startswith("/api/stt"):
                    svc = "stt"
                elif ep.startswith("/api/tts"):
                    svc = "tts"
                elif ep.startswith("/api/rag"):
                    svc = "rag"
                else:
                    svc = "other"

                if svc not in service_stats:
                    service_stats[svc] = {
                        "request_count": 0,
                        "success_count": 0,
                        "error_count": 0,
                        "avg_latency_ms": 0,
                        "last_success_time": None,
                    }

                ss = service_stats[svc]
                ss["request_count"] += stats.request_count
                ss["success_count"] += stats.success_count
                ss["error_count"] += stats.error_count
                if stats.last_success_time:
                    if ss["last_success_time"] is None or stats.last_success_time > ss["last_success_time"]:
                        ss["last_success_time"] = stats.last_success_time
                if stats.success_count > 0:
                    ss["avg_latency_ms"] = round(
                        (ss["avg_latency_ms"] * (ss["success_count"] - stats.success_count) + stats.total_latency_ms)
                        / ss["success_count"],
                        2,
                    )

            return {
                "total_requests": total_requests,
                "total_success": total_success,
                "total_errors": total_errors,
                "error_rate_pct": round(total_errors / total_requests * 100, 2) if total_requests > 0 else 0,
                "last_success_time": last_success,
                "uptime_seconds": self.get_uptime_seconds(),
                "services": service_stats,
            }

    def reset(self):
        """Reset all metrics (for testing)."""
        with self._lock:
            self._endpoints.clear()


# Singleton instance
metrics = MetricsCollector()
