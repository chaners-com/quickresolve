"""
Util for retrieving resource utilization metrics.
"""

import os
import threading
import time
from typing import Callable

from opentelemetry import context as otel_context
from opentelemetry.metrics import Meter

from .resource_metrics import build_resource_recorder


class SamplerHandle:
    def __init__(self, thread: threading.Thread, stop_event: threading.Event):
        self.thread = thread
        self.stop_event = stop_event


def start_resource_sampler(
    callback: Callable[[dict], None],
    on_peaks: Callable[[dict], None],
    hz: float = 1.0,
    enable_gpu: bool = False,
) -> SamplerHandle:
    import psutil

    p = psutil.Process(os.getpid())

    gpu_enabled = False
    gpu_handles = []
    nvml = None
    if enable_gpu:
        try:
            import pynvml as nvml_mod  # type: ignore

            nvml = nvml_mod
            nvml.nvmlInit()
            for i in range(nvml.nvmlDeviceGetCount()):
                gpu_handles.append(nvml.nvmlDeviceGetHandleByIndex(i))
            gpu_enabled = True
        except Exception:
            gpu_enabled = False
            nvml = None

    stop_event = threading.Event()
    prev_time = time.time()
    try:
        io_prev = p.io_counters()
        rd_prev, wr_prev = io_prev.read_bytes, io_prev.write_bytes
    except Exception:
        rd_prev, wr_prev = 0, 0

    peaks = {"cpu": 0.0, "rss": 0, "rd_bps": 0.0, "wr_bps": 0.0, "gpus": {}}
    interval = max(0.05, 1.0 / max(0.1, hz))

    def run():
        nonlocal prev_time, rd_prev, wr_prev
        try:
            p.cpu_percent(None)
        except Exception:
            pass
        while not stop_event.is_set():
            t1 = time.time()
            dt = max(1e-6, t1 - prev_time)
            try:
                cpu = float(p.cpu_percent(None))
            except Exception:
                cpu = 0.0
            try:
                rss = int(p.memory_info().rss)
            except Exception:
                rss = 0
            try:
                io_now = p.io_counters()
                rd, wr = int(io_now.read_bytes), int(io_now.write_bytes)
                rd_bps = max(0.0, (rd - rd_prev) / dt)
                wr_bps = max(0.0, (wr - wr_prev) / dt)
                rd_prev, wr_prev = rd, wr
            except Exception:
                rd_bps, wr_bps = 0.0, 0.0

            gpus = []
            if gpu_enabled and nvml is not None:
                try:
                    for idx, h in enumerate(gpu_handles):
                        util = float(nvml.nvmlDeviceGetUtilizationRates(h).gpu)
                        mem_used = int(nvml.nvmlDeviceGetMemoryInfo(h).used)
                        gpus.append(
                            {"device": idx, "util": util, "mem_used": mem_used}
                        )
                        dpeaks = peaks["gpus"].setdefault(
                            idx, {"util": 0.0, "mem_used": 0}
                        )
                        dpeaks["util"] = max(dpeaks["util"], util)
                        dpeaks["mem_used"] = max(dpeaks["mem_used"], mem_used)
                except Exception:
                    pass

            peaks["cpu"] = max(peaks["cpu"], cpu)
            peaks["rss"] = max(peaks["rss"], rss)
            peaks["rd_bps"] = max(peaks["rd_bps"], rd_bps)
            peaks["wr_bps"] = max(peaks["wr_bps"], wr_bps)

            try:
                callback(
                    {
                        "cpu": cpu,
                        "rss": rss,
                        "rd_bps": rd_bps,
                        "wr_bps": wr_bps,
                        "gpus": gpus,
                    }
                )
            except Exception:
                pass

            stop_event.wait(max(0.0, interval - (time.time() - t1)))
            prev_time = t1

        try:
            on_peaks(peaks)
        except Exception:
            pass

        if gpu_enabled and nvml is not None:
            try:
                nvml.nvmlShutdown()
            except Exception:
                pass

    th = threading.Thread(target=run, daemon=True)
    th.start()
    return SamplerHandle(th, stop_event)


def start_process_resource_metrics(
    meter: Meter,
    base_attributes: dict,
    stage: str,
    hz: float = 1.0,
    enable_gpu: bool = False,
) -> SamplerHandle:
    # Kill switch: if SDK disabled or metrics disabled, do nothing
    try:
        if (
            os.getenv("OTEL_SDK_DISABLED", "true").lower() == "true"
            or os.getenv("OTEL_METRICS_ENABLED", "false").lower() != "true"
        ):
            return SamplerHandle(thread=None, stop_event=None)
    except Exception:
        pass

    ctx = otel_context.get_current()
    recorder = build_resource_recorder(meter)
    attrs = {"stage": stage, **(base_attributes or {})}

    def _tick(sample: dict) -> None:
        try:
            recorder.record_sample(sample, attributes=attrs, context=ctx)
        except Exception:
            pass

    def _peaks(peaks: dict) -> None:
        try:
            recorder.record_peaks(peaks, attributes=attrs, context=ctx)
        except Exception:
            pass

    return start_resource_sampler(_tick, _peaks, hz=hz, enable_gpu=enable_gpu)


def stop_resource_sampler(handle: SamplerHandle) -> None:
    try:
        if (
            not handle
            or not getattr(handle, "stop_event", None)
            or not getattr(handle, "thread", None)
        ):
            return
        handle.stop_event.set()
        handle.thread.join(timeout=2.0)
    except Exception:
        pass
