from sched_brs_sim.workloads import interactive_workload
from benchmarks._common import run_workload

if __name__ == "__main__":
    run_workload("interactive", interactive_workload)
