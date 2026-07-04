from sched_brs_sim.workloads import ai_inference_workload
from benchmarks._common import run_workload

if __name__ == "__main__":
    run_workload("ai_inference", ai_inference_workload)
