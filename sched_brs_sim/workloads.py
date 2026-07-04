"""Representative workload classes (Section V-B).

Each task carries a sleep propensity and an I/O-wait fraction; the simulator
*measures* the interactivity score B_i from the resulting behaviour rather than
reading these as static labels. Five classes span latency- and fairness-
sensitive behaviour: Interactive, Gaming/Graphics, AI Inference, Data
Analytics, and Cloud Streaming.

The paper's evaluation runs enough runnable tasks to *saturate* a 16-core
platform (Section V-A/V-I). We mirror that here: each class saturates the
(single-CPU) simulator with ~16 runnable tasks -- a handful of latency-
sensitive foreground tasks against a CPU-bound background -- so that the
responsiveness/fairness trade-off the paper studies is actually exercised.
Under an under-loaded runqueue no scheduler has to make hard choices, and any
policy looks equally good; contention is what separates them.
"""

from .scheduler import Task


def _saturate(foreground, background, n_bg):
    """Replicate the CPU-bound background to reach a saturated runqueue."""
    tasks = list(foreground)
    for i in range(n_bg):
        base = background[i % len(background)]
        tasks.append(Task(f"{base.name}{i}", quantum=base.quantum,
                          sleep_ratio=base.sleep_ratio, io_ratio=base.io_ratio,
                          share=base.share))
    return tasks


def interactive_workload():
    fg = [
        Task("ui",     quantum=0.5, sleep_ratio=0.90, io_ratio=0.30, share=0.06),
        Task("input",  quantum=0.6, sleep_ratio=0.85, io_ratio=0.40, share=0.06),
        Task("render", quantum=0.7, sleep_ratio=0.75, io_ratio=0.20, share=0.06),
        Task("scroll", quantum=0.6, sleep_ratio=0.80, io_ratio=0.25, share=0.06),
        Task("compositor", quantum=0.7, sleep_ratio=0.70, io_ratio=0.20, share=0.06),
    ]
    bg = [
        Task("daemon", quantum=1.4, sleep_ratio=0.15, io_ratio=0.05, share=0.05),
        Task("indexer", quantum=1.6, sleep_ratio=0.10, io_ratio=0.10, share=0.05),
    ]
    return _saturate(fg, bg, 11)


def gaming_workload():
    fg = [
        Task("frame_builder", quantum=0.6, sleep_ratio=0.75, io_ratio=0.15, share=0.08),
        Task("physics",       quantum=0.8, sleep_ratio=0.65, io_ratio=0.10, share=0.07),
        Task("input_poll",    quantum=0.5, sleep_ratio=0.80, io_ratio=0.20, share=0.06),
        Task("audio",         quantum=0.6, sleep_ratio=0.70, io_ratio=0.30, share=0.06),
    ]
    bg = [
        Task("ai",       quantum=1.3, sleep_ratio=0.20, io_ratio=0.05, share=0.05),
        Task("streamer", quantum=1.4, sleep_ratio=0.15, io_ratio=0.20, share=0.05),
        Task("logger",   quantum=1.6, sleep_ratio=0.10, io_ratio=0.30, share=0.05),
    ]
    return _saturate(fg, bg, 12)


def ai_inference_workload():
    fg = [
        Task("rpc",      quantum=0.7, sleep_ratio=0.85, io_ratio=0.50, share=0.07),
        Task("preproc",  quantum=0.9, sleep_ratio=0.65, io_ratio=0.30, share=0.06),
        Task("dispatch", quantum=0.6, sleep_ratio=0.75, io_ratio=0.40, share=0.06),
    ]
    bg = [
        Task("infer",    quantum=1.5, sleep_ratio=0.15, io_ratio=0.05, share=0.05),
        Task("postproc", quantum=1.2, sleep_ratio=0.25, io_ratio=0.20, share=0.05),
        Task("bg_gc",    quantum=1.4, sleep_ratio=0.15, io_ratio=0.05, share=0.05),
    ]
    return _saturate(fg, bg, 13)


def data_analytics_workload():
    # Batch-heavy; a responsiveness bias is least likely to help here.
    fg = [
        Task("query",   quantum=0.8, sleep_ratio=0.60, io_ratio=0.30, share=0.07),
        Task("stream_agg", quantum=0.9, sleep_ratio=0.55, io_ratio=0.30, share=0.06),
    ]
    bg = [
        Task("joiner",     quantum=1.4, sleep_ratio=0.20, io_ratio=0.20, share=0.05),
        Task("sink",       quantum=1.3, sleep_ratio=0.20, io_ratio=0.40, share=0.05),
        Task("bg_compact", quantum=1.6, sleep_ratio=0.10, io_ratio=0.10, share=0.05),
    ]
    return _saturate(fg, bg, 14)


def streaming_workload():
    fg = [
        Task("encoder",    quantum=0.8, sleep_ratio=0.70, io_ratio=0.25, share=0.07),
        Task("packetizer", quantum=0.7, sleep_ratio=0.75, io_ratio=0.35, share=0.06),
        Task("webrtc",     quantum=0.7, sleep_ratio=0.70, io_ratio=0.50, share=0.06),
    ]
    bg = [
        Task("disk_io", quantum=1.4, sleep_ratio=0.25, io_ratio=0.60, share=0.05),
        Task("monitor", quantum=1.5, sleep_ratio=0.15, io_ratio=0.10, share=0.05),
    ]
    return _saturate(fg, bg, 13)
