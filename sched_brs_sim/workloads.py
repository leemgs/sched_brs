from .scheduler import Task

def interactive_workload():
    # mix of short interactive tasks and background
    tasks = [
        Task("ui", quantum=0.5, sleep_ratio=0.9, recent_wakeup=True, share=0.25),
        Task("input", quantum=0.6, sleep_ratio=0.8, recent_wakeup=True, share=0.20),
        Task("render", quantum=0.7, sleep_ratio=0.6, recent_wakeup=True, share=0.25),
        Task("daemonA", quantum=1.2, sleep_ratio=0.2, recent_wakeup=False, share=0.15),
        Task("daemonB", quantum=1.4, sleep_ratio=0.1, recent_wakeup=False, share=0.15),
    ]
    return tasks

def gaming_workload():
    tasks = [
        Task("frame_builder", quantum=0.6, sleep_ratio=0.7, recent_wakeup=True, share=0.35),
        Task("physics", quantum=0.9, sleep_ratio=0.5, recent_wakeup=True, share=0.25),
        Task("ai", quantum=1.0, sleep_ratio=0.4, recent_wakeup=False, share=0.15),
        Task("streamer", quantum=1.1, sleep_ratio=0.3, recent_wakeup=False, share=0.15),
        Task("logger", quantum=1.3, sleep_ratio=0.2, recent_wakeup=False, share=0.10),
    ]
    return tasks

def ai_inference_workload():
    tasks = [
        Task("rpc", quantum=0.7, sleep_ratio=0.8, recent_wakeup=True, share=0.30),
        Task("preproc", quantum=0.9, sleep_ratio=0.6, recent_wakeup=True, share=0.25),
        Task("postproc", quantum=1.0, sleep_ratio=0.5, recent_wakeup=False, share=0.20),
        Task("bg_gc", quantum=1.2, sleep_ratio=0.2, recent_wakeup=False, share=0.15),
        Task("exporter", quantum=1.1, sleep_ratio=0.1, recent_wakeup=False, share=0.10),
    ]
    return tasks

def data_analytics_workload():
    tasks = [
        Task("stream_agg", quantum=1.0, sleep_ratio=0.5, recent_wakeup=True, share=0.30),
        Task("joiner", quantum=1.1, sleep_ratio=0.4, recent_wakeup=False, share=0.25),
        Task("sink", quantum=1.0, sleep_ratio=0.3, recent_wakeup=False, share=0.25),
        Task("bg_compact", quantum=1.3, sleep_ratio=0.2, recent_wakeup=False, share=0.10),
        Task("metrics", quantum=1.2, sleep_ratio=0.2, recent_wakeup=False, share=0.10),
    ]
    return tasks

def streaming_workload():
    tasks = [
        Task("encoder", quantum=0.8, sleep_ratio=0.6, recent_wakeup=True, share=0.30),
        Task("packetizer", quantum=0.9, sleep_ratio=0.6, recent_wakeup=True, share=0.25),
        Task("webrtc", quantum=0.9, sleep_ratio=0.5, recent_wakeup=True, share=0.20),
        Task("disk_io", quantum=1.1, sleep_ratio=0.3, recent_wakeup=False, share=0.15),
        Task("monitor", quantum=1.1, sleep_ratio=0.2, recent_wakeup=False, share=0.10),
    ]
    return tasks
