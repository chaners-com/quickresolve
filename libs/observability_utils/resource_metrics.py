"""
Class for building resource utilization metrics
for the OpenTelemetry API.


"""

from dataclasses import dataclass
from typing import Any

# Delay importing heavy modules until used to avoid cost when disabled
try:
    from opentelemetry.metrics import Meter  # type: ignore
except Exception:
    Meter = object  # type: ignore


@dataclass
class ResourceInstruments:
    cpu_pct: any
    mem_rss: any
    io_rd_bps: any
    io_wr_bps: any
    cpu_pct_peak: any
    mem_rss_peak: any
    io_rd_bps_peak: any
    io_wr_bps_peak: any
    gpu_util: any
    gpu_mem: any
    gpu_util_peak: any
    gpu_mem_peak: any


def build_resource_instruments(meter: Meter) -> ResourceInstruments:
    cpu_pct = meter.create_histogram(
        "process_cpu_percent", unit="%", description="Process CPU percent"
    )
    mem_rss = meter.create_histogram(
        "process_memory_rss_bytes", unit="By", description="Process RSS bytes"
    )
    io_rd_bps = meter.create_histogram(
        "process_io_read_bytes_per_second",
        unit="By/s",
        description="Process read B/s",
    )
    io_wr_bps = meter.create_histogram(
        "process_io_write_bytes_per_second",
        unit="By/s",
        description="Process write B/s",
    )
    cpu_pct_peak = meter.create_histogram(
        "process_cpu_percent_peak", unit="%", description="Peak CPU percent"
    )
    mem_rss_peak = meter.create_histogram(
        "process_memory_rss_peak_bytes",
        unit="By",
        description="Peak RSS bytes",
    )
    io_rd_bps_peak = meter.create_histogram(
        "process_io_read_bps_peak", unit="By/s", description="Peak read B/s"
    )
    io_wr_bps_peak = meter.create_histogram(
        "process_io_write_bps_peak", unit="By/s", description="Peak write B/s"
    )
    gpu_util = meter.create_histogram(
        "gpu_util_percent", unit="%", description="GPU util percent"
    )
    gpu_mem = meter.create_histogram(
        "gpu_memory_bytes", unit="By", description="GPU memory bytes"
    )
    gpu_util_peak = meter.create_histogram(
        "gpu_util_percent_peak", unit="%", description="Peak GPU util"
    )
    gpu_mem_peak = meter.create_histogram(
        "gpu_memory_peak_bytes", unit="By", description="Peak GPU memory"
    )
    return ResourceInstruments(
        cpu_pct=cpu_pct,
        mem_rss=mem_rss,
        io_rd_bps=io_rd_bps,
        io_wr_bps=io_wr_bps,
        cpu_pct_peak=cpu_pct_peak,
        mem_rss_peak=mem_rss_peak,
        io_rd_bps_peak=io_rd_bps_peak,
        io_wr_bps_peak=io_wr_bps_peak,
        gpu_util=gpu_util,
        gpu_mem=gpu_mem,
        gpu_util_peak=gpu_util_peak,
        gpu_mem_peak=gpu_mem_peak,
    )


class _ResourceRecorder:
    def __init__(self, instruments: ResourceInstruments):
        self.i = instruments

    def record_sample(
        self, sample: dict, attributes: dict, context: Any
    ) -> None:
        self.i.cpu_pct.record(
            float(sample.get("cpu", 0.0)),
            attributes=attributes,
            context=context,
        )
        self.i.mem_rss.record(
            int(sample.get("rss", 0)), attributes=attributes, context=context
        )
        self.i.io_rd_bps.record(
            float(sample.get("rd_bps", 0.0)),
            attributes=attributes,
            context=context,
        )
        self.i.io_wr_bps.record(
            float(sample.get("wr_bps", 0.0)),
            attributes=attributes,
            context=context,
        )
        for g in sample.get("gpus", []):
            dev_attrs = {**attributes, "device": str(g.get("device"))}
            self.i.gpu_util.record(
                float(g.get("util", 0.0)),
                attributes=dev_attrs,
                context=context,
            )
            self.i.gpu_mem.record(
                int(g.get("mem_used", 0)),
                attributes=dev_attrs,
                context=context,
            )

    def record_peaks(
        self, peaks: dict, attributes: dict, context: Any
    ) -> None:
        self.i.cpu_pct_peak.record(
            float(peaks.get("cpu", 0.0)),
            attributes=attributes,
            context=context,
        )
        self.i.mem_rss_peak.record(
            int(peaks.get("rss", 0)), attributes=attributes, context=context
        )
        self.i.io_rd_bps_peak.record(
            float(peaks.get("rd_bps", 0.0)),
            attributes=attributes,
            context=context,
        )
        self.i.io_wr_bps_peak.record(
            float(peaks.get("wr_bps", 0.0)),
            attributes=attributes,
            context=context,
        )
        for dev, d in (peaks.get("gpus", {}) or {}).items():
            dev_attrs = {**attributes, "device": str(dev)}
            self.i.gpu_util_peak.record(
                float(d.get("util", 0.0)),
                attributes=dev_attrs,
                context=context,
            )
            self.i.gpu_mem_peak.record(
                int(d.get("mem_used", 0)),
                attributes=dev_attrs,
                context=context,
            )


def build_resource_recorder(meter: Meter) -> _ResourceRecorder:
    return _ResourceRecorder(build_resource_instruments(meter))
