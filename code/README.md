# SCHED_BRS Artifact (Reproduction Package)
<p align="center">
  <img src="brs_logo01.png" alt="BRS Logo" width="300"/>
</p>

This repository is a faithful, **runnable** reproduction package for the paper
*"Practical Bounded Responsiveness Scheduling for Low-Latency Mobile Systems."*
It contains a discrete-event simulator of the Bounded Responsiveness Scheduler
(BRS), a benchmark harness, the design-of-experiments and adversarial studies,
controller-adaptation traces, a synthetic-dataset generator, a unit/regression
test suite, and illustrative kernel-patch sketches showing how the bias hooks
integrate into CFS.

Exact numbers differ from real-kernel measurements, but the **mechanism** and
the **trends** match the paper: interactive (high-B) tasks get lower wake-to-run
tail latency, fairness stays above the floor (Jain's index ≥ 0.96), and
starvation stays bounded.

## 🧩 한눈에 보기 (At a Glance)

세 단계가 **하나의 파이프라인**으로 연결됩니다 — 워크로드를 **시뮬레이션**하고,
세 정책을 **벤치마크**하며, 결과를 **분석**합니다.

```mermaid
flowchart LR
    subgraph SIM["🧠 sched_brs_sim"]
        direction TB
        W["workloads.py<br/>포화 워크로드"]
        I["interactivity.py<br/>B_i 산출"]
        S["scheduler.py<br/>Eq.2 · tie-break<br/>controller · aging"]
        W --> S
        I --> S
    end

    subgraph BM["⚙️ benchmarks"]
        P["3정책 스코어링<br/>CFS · BFS/MuQSS · BRS"]
    end

    subgraph AN["📊 scripts"]
        R["analyze_results.py<br/>P95 · Jain · starvation"]
    end

    SIM -->|"telemetry / metrics"| BM
    BM -->|"results/*.csv"| AN

    style SIM fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a
    style BM  fill:#fef3c7,stroke:#f59e0b,color:#78350f
    style AN  fill:#dcfce7,stroke:#22c55e,color:#14532d
```

| 구성요소 | 역할 | 요약 |
|---|---|---|
| `sched_brs_sim/` | 🧠 **Simulation** | interactivity(B_i), vruntime 바이어싱(Eq.2), tie-break 선택, 하이브리드 컨트롤러, aging 가드레일을 담은 이산사건 스케줄러 (`static`/`adaptive`/`hybrid`, α=β=0 은 CFS) |
| `benchmarks/` | ⚙️ **Benchmark** | 5개 워크로드 + adversarial 에서 CFS·BFS/MuQSS 유사·BRS 세 정책을 12k 스텝 비교하여 `results/*.csv` 발행 |
| `scripts/` | 📊 **Analysis** | P95(interactive/all/background)·Jain·starvation 요약, DOE 스윕, 합성 데이터, 컨트롤러 적응 트레이스 산출 |

## 🔄 동작 흐름 (Operation Flow)

매 스케줄링 스텝은 다음 루프를 따릅니다 — 상호작용성 점수 산출 → vruntime 바이어싱 →
선택 → 컨트롤러/aging 보정 → 지표 기록.

```mermaid
sequenceDiagram
    autonumber
    participant W as 🧪 workloads
    participant B as 📈 interactivity (B_i)
    participant V as ⏱️ vruntime (Eq.2)
    participant SEL as 🎯 selection
    participant C as 🎛️ controller + aging
    participant M as 📊 metrics / telemetry

    W->>B: task 이벤트 (sleep / iowait / wake)
    B->>B: 슬라이딩 윈도우 (W=64) + EWMA (ρ=0.25)
    B->>V: B_i ∈ [0,1]
    V->>V: vruntime_i += Δt · (1 − α·B_i)
    V->>SEL: 갱신된 vruntime
    SEL->>SEL: argmin_i (vruntime_i − β·B_i)
    SEL->>C: 실행 태스크 선택
    C->>C: 매 제어주기 (α,β) 조정 + fairness/starvation 가드레일
    C-->>V: 기아 태스크 강제 승격 (aging)
    C->>M: J(Jain), S(starvation), P95 기록
    M->>W: 다음 스텝
```

**핵심 원칙**: 바이어스는 **엄격히 유한** — `1 − α·B_i ∈ [0.65, 1.0]` 이 항상 양수이므로
vruntime 은 단조 증가하고 CPU 점유 편차는 최대 `1/(1 − α_max) ≈ 1.54×` 로 묶입니다.

## 📂 데이터 흐름 (Data Flow)

산출물 관점에서 각 스크립트는 `results/` 아래로 결과를 발행합니다.

```mermaid
flowchart LR
    RUN["benchmarks/run_all.sh"] -->|"per-workload CSV"| R1["results/*.csv"]
    R1 --> AN["scripts/analyze_results.py"]
    AN -->|"P95 · Jain · BRS-vs-CFS reduction"| R2["results/summary.json"]
    LOG["scripts/log_adaptation.py"] -->|"(α,β,J,S) 트레이스"| R3["results/adaptation/"]
    SYN["scripts/gen_synth.py"] -->|"500k-token 합성셋"| R4["results/synth_tokens.txt"]
    DOE["scripts/doe_sweep.py"] -->|"surrogate R² + (α*, β*)"| OUT["stdout"]
```

## Core mechanism

BRS makes interactive tasks accumulate virtual runtime *more slowly* so they are
selected earlier, with a strictly bounded bias (Eq. 2):

```
vruntime_i += Δt · (1 − α · B_i)
```

Because `1 − α·B_i ∈ [1 − α_max, 1] = [0.65, 1.0]` is strictly positive,
vruntime stays monotone and per-task CPU share deviates from CFS by at most
`1/(1 − α_max) ≈ 1.54×` (Definition 1 / Lemma 1). The interactivity score
`B_i ∈ [0,1]` is the convex combination `0.5·sleep + 0.3·iowait + 0.2·wake_hist`
over a sliding window (W=64), EWMA-smoothed (ρ=0.25) — Section IV-C. Selection
uses the interactivity-aware tie-break `argmin_i (vruntime_i − β·B_i)`
(Section IV-D), and a hybrid controller adjusts (α,β) each control period with a
fairness/starvation guardrail and an aging (starvation-shield) force-promotion
(Section IV-F).

## What's inside
- `sched_brs_sim/` — the simulator: `interactivity.py` (B_i), `scheduler.py`
  (Eq. 2, tie-break, hybrid controller, aging guardrail; `static`/`adaptive`/
  `hybrid` modes, with `α=β=0` static emulating CFS), `workloads.py`
  (saturated representative workloads), `metrics.py`, `telemetry.py`.
- `benchmarks/` — five workload benchmarks plus `adversarial.py`
  (Sec IV-G/V-I), driven by `_common.py`, which scores three policies per
  workload — CFS (α=β=0), a BFS/MuQSS-like low-latency reference (α=0.30,
  β=0.25 static), and BRS (α=0.20, β=0.15 hybrid, Table I defaults) — over
  12k steps; `run_all.sh` emits CSVs to `results/`.
- `scripts/`
  - `analyze_results.py` — per-workload P95 (interactive/all/background),
    Jain, starvation, and BRS-vs-CFS P95 reduction.
  - `doe_sweep.py` — Section IV-I 5×5 DOE, surrogate fits (Eq. 4/5) with R²,
    held-out validation, and the closed-form Lagrangian optimum (Eq. 6).
  - `gen_synth.py` — Section V-C synthetic 500k-token dataset (log-normal
    mean 512, sd 128, seed 42).
  - `log_adaptation.py` — Section V-H controller-adaptation traces across
    idle→gaming→mixed transitions, written to `results/adaptation/`.
  - `run_gui_redraw.sh` — placeholder for the GUI-redraw harness (see paper
    artifact notes); not part of the automated pipeline.
- `tests/` — unit/regression tests for the Def. 1 bound, Lemma 1, `B_i ∈ [0,1]`,
  the Eq. 2 sign, CFS reduction, and the fairness floor.
- `kernel_patches/` — a single illustrative diff (`sched_brs.patch`) with the
  CFS touch points and `/proc/sys/sched_brs` knobs.
- `kernel_patches_mvp/` — a 9-part illustrative patch series (framework,
  vruntime biasing, hybrid controller, mitigations + aging guardrail, NUMA,
  tracing, docs, cleanup).
- `ci/run_tests.sh` — compiles sources, runs the test suite, benchmarks, DOE,
  adaptation traces, and the dataset generator.
- `results/` — generated CSVs, JSON summaries, and adaptation traces.
- `LICENSE.md` — Apache-2.0.

## Quick start
```bash
python3 -m venv .venv && source .venv/bin/activate   # optional
export PYTHONPATH="$PWD"

# Benchmarks -> results/*.csv
bash benchmarks/run_all.sh

# Summary (per-workload P95, fairness, BRS-vs-CFS reduction)
python scripts/analyze_results.py --input results --out results/summary.json

# Full paper-artifact pipeline (tests + DOE + adaptation + dataset)
bash ci/run_tests.sh
```

Representative simulator output (12k steps): interactive-class P95 falls ~21–33%
vs the CFS baseline across workloads with Jain's index ≥ 0.96 and ~0% starvation
— the same direction as the paper's −35.2%/−37.8% headline, at simulator scale.

## Individual studies
```bash
python scripts/doe_sweep.py        # surrogate R^2 + closed-form (α*, β*)
python benchmarks/adversarial.py   # adversary CPU share vs CFS, worst slowdown < 1.54x
python scripts/log_adaptation.py   # (α,β,J,S) trajectories; settles in 3–5 periods
python scripts/gen_synth.py        # results/synth_tokens.txt (+ summary)
python -m unittest discover -s tests -v
```

## Kernel patch sketches
The patches are **illustrative** pseudo-C, not build-ready. `kernel_patches/sched_brs.patch`
shows the vruntime scaling `scale = 10000 − α·B` (fixed-point form of Eq. 2),
the tie-break, and the aging guardrail inside `kernel/sched/fair.c`, plus the
`/proc/sys/sched_brs/*` interface. The `kernel_patches_mvp/` series breaks the
same logic into an ordered patch set. Replace with a production patch when ready.

## Folder structure
```
sched_brs-main/
├─ README.md
├─ LICENSE.md
├─ brs_logo01.png
├─ __init__.py
├─ kernel_patches/
│  └─ sched_brs.patch
├─ kernel_patches_mvp/
│  ├─ 0000..0008-sched-BRS-*.patch
│  └─ README.md
├─ sched_brs_sim/
│  ├─ __init__.py  interactivity.py  scheduler.py
│  ├─ workloads.py  metrics.py  telemetry.py
├─ benchmarks/
│  ├─ __init__.py  _common.py  run_all.sh
│  ├─ interactive.py  gaming.py  ai_inference.py
│  ├─ data_analytics.py  streaming.py  adversarial.py
├─ scripts/
│  ├─ analyze_results.py  doe_sweep.py  gen_synth.py
│  ├─ log_adaptation.py  run_gui_redraw.sh
├─ tests/
│  ├─ __init__.py  test_bounds.py
├─ ci/
│  └─ run_tests.sh
└─ results/
   └─ .gitkeep
```

## License
Apache-2.0. See `LICENSE.md`.
