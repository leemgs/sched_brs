from sched_brs_sim.workloads import data_analytics_workload
from benchmarks._common import run_workload

if __name__ == "__main__":
    run_workload("data_analytics", data_analytics_workload)
