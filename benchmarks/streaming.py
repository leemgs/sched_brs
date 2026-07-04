from sched_brs_sim.workloads import streaming_workload
from benchmarks._common import run_workload

if __name__ == "__main__":
    run_workload("streaming", streaming_workload)
