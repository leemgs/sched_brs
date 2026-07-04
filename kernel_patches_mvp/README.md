# SCHED_BRS: Bounded Responsiveness Scheduler — 커널 패치 시리즈 (MVP)

**SCHED_BRS**는 응답성(responsiveness)과 공정성(fairness)을 함께 최적화하도록 설계된 Linux 커널 스케줄러 수정(패치) 세트입니다. 기존 스케줄러(CFS 등)가 이 두 목표를 상충 관계로 간주하는 것과 달리, SCHED_BRS는 커널 스케줄링 경로에 '제한된 편향(bounded bias)'을 통합하고 부하에 따라 동적으로 조정하여, 공정성 편차를 형식적으로 유계(bounded)로 유지하면서 낮은 꼬리 대기 시간(P95 tail latency)을 달성합니다.

이 디렉터리는 논문 *"Practical Bounded Responsiveness Scheduling for Low-Latency Mobile Systems"* (G. Lim)의 재현 아티팩트 중 **커널 패치 시리즈(illustrative)** 부분입니다. 패치는 실제 빌드 대상이 아닌, 논문의 커널 측 로직을 의사 C 코드로 보여주는 스케치입니다. 실행 가능한 참조 구현은 상위 디렉터리의 Python 시뮬레이터(`sched_brs_sim/`)와 벤치마크(`benchmarks/`, `scripts/`)에 있습니다.

## 주요 기능

1.  **Vruntime 편향 엔진 (Vruntime Biasing):** 대화형(interactive) 태스크가 가상 실행 시간(**vruntime**)을 더 느리게 누적하도록 하여 더 일찍 선택되게 합니다.
    * **핵심 공식 (Eq. 2):** `vruntime = vruntime + Δt * (1 - α * B_i)`
    * `1 - α·B_i`는 `[1 - α_max, 1] = [0.65, 1.0]` 범위의 **양수**이므로 vruntime은 단조 증가하며 진행 부호가 반전되지 않습니다 (Definition 1 / Lemma 1).
    * **B_i (Sec IV-C):** `0.5·sleep_ratio + 0.3·iowait_ratio + 0.2·wake_history`의 볼록 결합을 슬라이딩 윈도(W=64)에서 측정하고 EWMA(ρ=0.25)로 평활화한 [0,1] 점수.
2.  **선택 타이브레이커 (Sec IV-D):** vruntime이 비슷할 때 `argmin_i (vruntime_i - β · B_i)`로 상호작용 태스크를 우선합니다.
3.  **하이브리드 제어기 (Hybrid Controller):** **Jain 지수**와 **기아(starvation) 발생률**을 모니터링하여 `α`, `β`를 동적으로 조정하고, 가드레일 접근 시 편향을 감쇠(damp)합니다.
4.  **에이징 가드레일 (Sec IV-F):** 대기(undispatched)가 `S_max`(100 ms)를 초과한 태스크를 B_i와 무관하게 강제 승격하여 절대 기아를 유계로 만듭니다.
5.  **/proc 제어 인터페이스:** `bias_alpha`, `bias_beta`, `bias_mode`를 런타임에 안전하게 조정할 수 있는 최소 제어 표면.

## 🛠️ SCHED_BRS 커널 패치 시리즈 (9개)

다음은 Linux 커널 소스 트리에 순서대로 적용되는 패치 파일입니다 (Linux Kernel 6.8+ 대상).

| 파일 번호 | 파일명 | 주요 역할 |
| :--- | :--- | :--- |
| **0000** | `0000-sched-Enable-SCHED_BRS-build-and-Kconfig.patch` | 빌드 시스템 설정 및 SCHED_BRS 활성화 |
| **0001** | `0001-sched-Introduce-SCHED_BRS-framework.patch` | 기본 데이터 구조 및 초기화 프레임워크 도입 |
| **0002** | `0002-sched-BRS-Implement-vruntime-biasing.patch` | **핵심 기능:** vruntime 편향 엔진(Eq. 2) 구현 |
| **0003** | `0003-sched-BRS-Add-hybrid-controller-and-proc-interface.patch` | **핵심 기능:** 동적 제어기 및 태스크 선택 로직 |
| **0004** | `0004-sched-BRS-Add-mitigations-and-security-guardrails.patch` | 안정성/보안 완화 및 에이징 가드레일 |
| **0005** | `0005-sched-BRS-Add-NUMA-awareness-and-load-distribution.patch` | NUMA 인지 및 부하 분산 최적화 |
| **0006** | `0006-sched-BRS-Add-tracing-and-debug-interfaces.patch` | 트레이싱 및 디버그 훅 |
| **0007** | `0007-sched-BRS-Add-official-documentation.patch` | 커널 공식 문서화 |
| **0008** | `0008-sched-BRS-Final-cleanup-and-series-submission-note.patch` | 최종 정리 및 시리즈 제출 노트 |

## 설정 매개변수 (Table I: Defaults & Safe Ranges)

| 매개변수 | 기본값 | 안전 범위 | 설명 |
| :--- | :--- | :--- | :--- |
| `bias_alpha` | 0.20 | [0.10, 0.35] | Vruntime 편향 계수 (`α`) |
| `bias_beta`  | 0.15 | [0.05, 0.30] | 런큐 선택 증폭 계수 (`β`) |
| `bias_mode`  | hybrid | {static, adaptive, hybrid} | 제어기 모드 |

## 라이선스

이 프로젝트는 **Apache-2.0** 라이선스를 따릅니다. 자세한 내용은 상위 디렉터리의 `LICENSE.md`를 참조하십시오.
