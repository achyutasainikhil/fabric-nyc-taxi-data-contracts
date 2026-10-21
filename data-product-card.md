# Data Product Card — NYC Taxi Demand & Revenue Analytics

**Product owner (proposed):** Mobility Analytics Product Owner  
**Technical owner (proposed):** Mobility Analytics Engineering  
**Status:** Demo / non-production  
**Contract:** `contracts/nyc_taxi_silver.odcs.yaml`, version `1.0.0`  
**Initial data slice:** January 2024 NYC TLC Yellow Taxi records  
**Update cadence:** Source is published monthly; update when the selected source month is available and the pipeline succeeds.

## Product purpose

Provide a documented and quality-checked view of trip-level taxi activity for demand and recorded-charge analytics.

## Data deliverables

- `silver_yellow_taxi_trips`: contracted trip-level rows.
- `quarantine_yellow_taxi_trips`: excluded source rows with quality reasons for audit.
- `gold_daily_metrics`: daily trip and fare/charge metrics.
- `gold_pickup_zone_metrics`: volume and charges by pickup zone.
- `dq_contract_results`: latest blocking contract checks.

## Definitions and caveats

- `trip_date` is the calendar date of `pickup_datetime`.
- `recorded_total_amount` is the sum of source `total_amount`; the TLC dictionary says this excludes cash tips.
- This demo rejects negative fare/total rows, invalid time order, missing required fields, non-positive distances, distances above 100 miles, and present payment-type codes outside 0-6.
- The rules are demo product-policy choices; business owners should approve thresholds before production adoption.
- The TLC notes that trip records are supplied by technology providers and the TLC does not guarantee their accuracy or completeness.

## Consumer expectations

Consumers should use the Gold aggregations for exploratory reporting, read the contract before building joins, treat quarantine counts as operational data-quality signals, and request a contract version change rather than relying on undocumented schema changes.

## Support model for a real deployment

Replace this proposal with named owners, an operational support channel, a freshness/availability target, an incident process, data retention, sensitivity classification, and consumer-specific access roles. Do not invent an SLA that the upstream provider cannot support.
