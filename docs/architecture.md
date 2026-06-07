# Architecture Notes

AuroraVault mirrors the lab's diagram but adds a trust layer.

## Conceptual model mapping

- `FinancialInstrument` -> append-only `financial_instruments.jsonl`
- `DataSource` -> append-only `data_sources.jsonl`
- `TimeSeries` -> append-only `time_series.jsonl`
- `TimeSeriesPoint` -> append-only `time_series_points.jsonl`
- `Portfolio` -> append-only `portfolios.jsonl`
- `PortfolioAsset` -> append-only `portfolio_assets.jsonl`

## Design choices

- The warehouse is document-oriented, so heterogeneous attributes fit naturally in each `data` payload.
- Every write is immutable and versioned.
- Every record stores provenance, a previous-record hash, and a current hash.
- Historical reads choose the latest record whose `valid_from` is less than or equal to the requested time.
- Deletion is represented by a tombstone version, not by removing the record.

## Unique twist

The store acts like a small ledger. Each version points to the previous hash, which makes the warehouse auditable and easy to inspect.
