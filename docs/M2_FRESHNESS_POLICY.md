# Evidence Freshness Policy

## Correction

2026+ must **not** be described as a pristine historical out-of-sample window for EBA Trader.

Reason: M1 connectivity validation already observed live BTC/USDT market data in August 2026, and current market information is naturally visible to the owner/research process.

Therefore the evidence roles are:

### Historical development
- 2021–2023: research
- 2024: validation

### Frozen historical holdout
- 2025: frozen OOS used once after development screening/freeze

The frozen OOS is a procedural holdout: it must not be used by the code/research process for parameter selection before the freeze. It is not claimed that public historical BTC prices are unknowable to humans.

### 2026 onward
2026+ is **not** a retrospective pristine OOS.

It is reserved for forward evidence only:

- PAPER execution after M2 historical gates;
- SHADOW execution against live market data;
- later MICRO_LIVE review only after forward evidence passes.

Forward evidence begins from the timestamp at which the strategy/configuration is frozen for that forward stage. Data before that timestamp cannot be relabeled as unseen forward evidence.

## Practical consequence

Historical M2 passing is necessary but insufficient. Even if the 2025 frozen OOS passes, no live-money promotion occurs until a later forward PAPER/SHADOW period has been observed without retrospective parameter changes.
