from sched_brs_sim.workloads import gaming_workload
from benchmarks._common import run_workload

if __name__ == "__main__":
    run_workload("gaming", gaming_workload)
