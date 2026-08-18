# Flow 2 — Run Backtest Validation

Replays the global two-month blend month by month and compares it with a separately selected,
time-aware-popularity-only arm. There are no user-supplied optimization settings.

**Trigger**: the user clicks **Run Backtest Validation** on the Backtest tab.

```mermaid
sequenceDiagram
    participant Browser
    participant Route as FastAPI route
    participant Worker as Backtest worker
    participant Backtest as BacktestEngine
    participant Policy as PolicyEngine

    Browser->>Route: POST /api/backtest
    Route->>Worker: run service.run_backtest()
    Worker->>Backtest: run_backtest()
    loop each global prediction month
        Backtest->>Policy: evaluable_cases(month)
        Policy-->>Backtest: fixed policy-independent cohort
        Backtest->>Policy: select_policy(month)
        Policy-->>Backtest: selected blend policy (or bootstrap)
        Backtest->>Policy: select_popularity_arm(month)
        Policy-->>Backtest: independent pure-popularity policy
        loop each evaluable team-month case
            Backtest->>Policy: top_practices(case, blend policy)
            Policy-->>Backtest: two practices
            Backtest->>Policy: top_practices(case, popularity policy)
            Policy-->>Backtest: two practices
            Backtest->>Backtest: score both against observed outcome window
        end
        Backtest->>Backtest: record monthly metrics and policy audit
    end
    Backtest->>Backtest: aggregate complete-window primary results
    Backtest->>Backtest: aggregate all-month sensitivity results
    Backtest-->>Worker: per-month rows and both aggregates
    Worker-->>Route: result
    Route-->>Browser: backtest response
    Browser->>Browser: render primary, sensitivity, and per-month results
```

## Notes

- The route uses a worker thread so the event loop remains responsive while the calculation runs.
- `evaluable_cases()` establishes the same cohort for all 675 blend candidates and for the
  popularity arm. A policy never controls which cases are counted.
- The blend policy maximizes mean monthly HR@2 across completed earlier months. The comparison arm
  follows the same rule but is restricted to 100% popularity and independently selects only its
  recency weight.
- The result exposes per-month HR@2 for both arms, their difference, supporting rank-aware metrics,
  and separately labelled primary and sensitivity aggregates.
