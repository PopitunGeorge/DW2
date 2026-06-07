# Project Report

## What was built

AuroraVault is a runnable financial data warehouse prototype for Acme Ltd. It ingests market-data style payloads, stores them in an append-only document store, exposes the data through a REST API, and publishes an MCP tool server for LLM clients.

## Data used

The demo dataset contains:

- `GM` and `MSFT` equities
- `BTC` crypto prices
- a retired legacy instrument to demonstrate temporal deletion
- two market-data providers: Nasdaq Data Link and Bloomberg-style feeds
- a sample portfolio for Acme Ltd

## Reproducibility

1. Seed the demo data.
2. Start the API.
3. Query assets, sources, and time-series endpoints.
4. Use the MCP server with an MCP-capable client.

## IIAGen statement

The classroom template was not included in the workspace. Add the required usage statement here before submission.
