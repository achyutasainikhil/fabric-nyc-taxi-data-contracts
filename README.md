# NYC Taxi Data Contracts in Microsoft Fabric

A contract-first data engineering portfolio project using the Open Data Contract Standard (ODCS), Microsoft Fabric Lakehouse, PySpark, Delta tables, and GitHub Actions.

## Business scenario

A mobility analytics company wants a dependable data product for daily taxi demand and recorded trip revenue. Operations analysts need demand by pickup zone and day; finance analysts need consistent fare and total-amount definitions; report consumers need a documented schema and explicit quality guarantees.

**Data product:** NYC Taxi Demand & Revenue Analytics  
**Initial source slice:** NYC TLC Yellow Taxi trip records for January 2024 (Parquet) plus TLC taxi-zone lookup CSV.  
**Contracted output:** `silver_yellow_taxi_trips`  
**Gold outputs:** `gold_daily_metrics`, `gold_pickup_zone_metrics`, and `dq_contract_results`.

NYC TLC publishes monthly trip records and a separate taxi-zone lookup. The source documentation explains that the records are provided by authorized technology providers and the TLC does not guarantee their accuracy or completeness. The Silver quality rules in this project are product-owner policy choices, not official TLC guarantees.

## Architecture

```text
NYC TLC Yellow Taxi Parquet + Taxi Zone Lookup CSV
                    |
                    v
       Fabric Lakehouse / Bronze
      bronze_yellow_taxi_trips
       bronze_taxi_zone_lookup
                    |
                    v
         ODCS contract validation
      schema + quality policy / PySpark
            /                            v                   v
 silver_yellow_taxi_trips   quarantine_yellow_taxi_trips
           |
           v
       Fabric Lakehouse / Gold
   gold_daily_metrics | gold_pickup_zone_metrics
                    |
                    v
       SQL analytics endpoint / Power BI

GitHub repository: ODCS YAML + notebook source + unit tests + GitHub Actions
```

## What the contract states

The contract is in `contracts/nyc_taxi_silver.odcs.yaml` and declares ODCS `apiVersion: v3.1.0`.

- The schema and meanings of the contracted Silver fields.
- Required fields and null-value expectations.
- A valid `payment_type` domain for non-null codes.
- Product policy for chronological pickup/drop-off timestamps, `0 < trip_distance <= 100` miles, and non-negative fare/total amounts.
- Ownership, business purpose, limitations, granularity, and monthly-source context.

The standard can describe text rules and executable quality attributes. The Fabric notebook runs the operational PySpark checks because the data lives in a Fabric Delta table; `datacontract lint` in GitHub validates the contract document, while local unit tests protect the reference policy. Do not treat a successful contract lint as proof that live Fabric data passed its checks.

## Repository structure

```text
contracts/
  nyc_taxi_silver.odcs.yaml       # ODCS v3.1.0 contract
fabric/notebooks/
  01_ingest_bronze.ipynb          # download and load source data
  02_validate_and_build_silver.ipynb
  03_publish_gold.ipynb
src/
  quality_policy.py               # dependency-free policy reference
tests/
  test_quality_policy.py          # local policy unit tests
.github/workflows/
  contract-ci.yml                 # lint contract + run tests on PR/push
requirements-dev.txt
README.md
```

## Prerequisites

1. A Microsoft Fabric workspace on a Fabric-enabled capacity or trial, with permission to create Lakehouses and notebooks. Your tenant may restrict trial/capacity usage and Git integration.
2. A GitHub account and an empty repository for the project.
3. For local GitHub Actions reproduction, Python 3.11 and Git. You do not need a local Spark installation.
4. Public internet access from the Fabric notebook session to the NYC TLC file host.

## Part A — Build the project in Microsoft Fabric

### Step 1 — Create your workspace

1. Sign in to the Microsoft Fabric portal.
2. Create a workspace named `ws-nyc-taxi-data-contracts-dev` (or use a workspace you own).
3. Confirm that the workspace has a usable Fabric capacity/trial. If the New menu does not show Lakehouse or Notebook, check licensing, capacity, and tenant settings with your admin.

### Step 2 — Create a Lakehouse

1. In the workspace, select **New item → Lakehouse**.
2. Name it `lh_nyc_taxi_contracts`.
3. Open the Lakehouse explorer. Under **Files**, create folders named `landing` and `contracts` (if your UI does not support creating the folders directly, upload a small placeholder file into each folder and then delete the placeholder).
4. Keep this Lakehouse attached as the **default Lakehouse** for all three notebooks. The notebooks use `/lakehouse/default/Files/...` and managed Delta tables.

### Step 3 — Upload the contract into OneLake

1. Open `lh_nyc_taxi_contracts`.
2. In `Files/contracts`, upload `contracts/nyc_taxi_silver.odcs.yaml` from this repository.
3. Confirm the resulting OneLake path is `Files/contracts/nyc_taxi_silver.odcs.yaml`.
4. The Silver validation notebook deliberately fails with a clear message if the contract is missing; it does not silently bypass the contract.

### Step 4 — Import the notebooks

Use Fabric's **Import notebook** action to upload the three `.ipynb` files from `fabric/notebooks/` into the workspace. Repeat for each notebook.

- `01_ingest_bronze.ipynb`
- `02_validate_and_build_silver.ipynb`
- `03_publish_gold.ipynb`

Open each notebook and attach `lh_nyc_taxi_contracts` as its default Lakehouse. The import operation creates Fabric notebook items; it does not automatically upload the ODCS YAML into OneLake, so complete Step 3 separately.

### Step 5 — Run the Bronze ingestion notebook

1. Open `01_ingest_bronze`.
2. Verify the default Lakehouse is `lh_nyc_taxi_contracts`.
3. Run all cells. The notebook downloads:
   - `yellow_tripdata_2024-01.parquet` from the official TLC-hosted monthly file endpoint.
   - `taxi_zone_lookup.csv` from the TLC-hosted miscellaneous file endpoint.
4. The files are saved under `Files/landing/`.
5. The notebook loads these managed Delta tables:
   - `bronze_yellow_taxi_trips`
   - `bronze_taxi_zone_lookup`
6. Review the source schema, row count, and a sample of records. A full monthly file may take a few minutes depending on capacity and network.

The notebook is idempotent for this demo: rerunning it overwrites the two Bronze demo tables for the selected month. In a production incremental design, replace this with a month/partition-aware merge or append policy and maintain ingestion run IDs.

### Step 6 — Run contract validation and Silver transformation

1. Open `02_validate_and_build_silver`.
2. Confirm the contract YAML is in `Files/contracts/` and that the same Lakehouse is attached.
3. Run all cells.
4. The notebook normalizes source names to snake_case, casts fields, derives `trip_date` and `trip_duration_minutes`, and applies the publication rules.
5. Expected tables:
   - `silver_yellow_taxi_trips` — records that satisfy the product policy.
   - `quarantine_yellow_taxi_trips` — invalid records plus `quality_reason`.
   - `dq_contract_results` — contract/schema and data quality check outcomes.
6. Review the summary and `dq_contract_results`. The notebook raises an exception if a blocking check fails, so the downstream pipeline is stopped. It preserves quarantine evidence and only overwrites the consumer-facing Silver table after every blocking check passes; after a failed rerun, an existing Silver table remains the last successful version.

Product policy in this version:

- Required values for pickup/drop-off timestamps, pickup/drop-off zone IDs, distance, fare, and total amount.
- Drop-off must be later than pickup.
- Trip distance must be greater than 0 and no more than 100 miles.
- Fare and total amounts must be non-negative.
- Any non-null `payment_type` must be one of 0 through 6.

These rules are intentionally explicit and configurable. They are designed for a teaching/demo data product and should be agreed with real business owners before production use. Some genuine source rows, such as voids or corrections, may be routed to quarantine by the policy.

### Step 7 — Publish Gold tables

1. Open `03_publish_gold` after Notebook 02 has succeeded.
2. Run all cells.
3. The notebook joins the Silver trip data to the TLC zone lookup and creates:
   - `gold_daily_metrics`: trip count, recorded total amount, average fare, average tip, and average distance by pickup date.
   - `gold_pickup_zone_metrics`: trip count and recorded revenue by pickup zone/borough.
4. Review the data with `display(...)` in the notebook and open the tables in Lakehouse explorer.

### Step 8 — Explore with the SQL analytics endpoint / Power BI

1. Open the Lakehouse SQL analytics endpoint.
2. Query `gold_daily_metrics` and `gold_pickup_zone_metrics` using SQL. Example:

```sql
SELECT TOP 20 *
FROM dbo.gold_pickup_zone_metrics
ORDER BY trip_count DESC;
```

3. In the Lakehouse, select **New semantic model** (or create a Power BI report using the Lakehouse/SQL analytics endpoint, depending on your tenant UI).
4. Add `gold_daily_metrics` and `gold_pickup_zone_metrics`.
5. Suggested visuals: daily trips as a line chart, revenue by day, top 10 pickup zones by trips, and a KPI card for total recorded amount.

SQL analytics endpoint table visibility may take time to update after Delta writes. Refresh the endpoint/metadata if a just-written table is not immediately visible.

### Step 9 — Orchestrate with a Fabric Data Factory pipeline (recommended extension)

1. Select **New item → Data pipeline** and name it `pl_nyc_taxi_contract_first`.
2. Add Notebook activities in order: `01_ingest_bronze`, then `02_validate_and_build_silver`, then `03_publish_gold`.
3. Configure each activity to use the correct notebook and authentication method available in your tenant.
4. Connect activities with **On success** dependencies. Do not connect the Gold activity to the Bronze activity in parallel; Gold must wait for Silver validation to succeed.
5. Save and run the pipeline. Check activity outputs/run history.
6. After successful testing, use the pipeline's schedule controls for a refresh cadence appropriate to your source. The selected TLC source publishes monthly, so this demonstration does not claim real-time freshness.

The Silver notebook raises an exception on failed blocking checks, which should stop subsequent activities.

## Part B — Put it in GitHub

### Step 10 — Create the GitHub repository

1. On GitHub, create a repository named `fabric-nyc-taxi-data-contracts`.
2. Choose public if this is a portfolio repo; do not commit secrets, tokens, exported workspace data, or any private dataset.
3. For the easiest command-line route, create the repository without adding a README/license because this project already has both.

### Step 11 — Push the project files

Download the project ZIP, extract it, then open PowerShell or Git Bash in the extracted `fabric-nyc-taxi-data-contracts` folder:

```bash
git init
git branch -M main
git add .
git commit -m "feat: add Fabric data contract analytics project"
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/fabric-nyc-taxi-data-contracts.git
git push -u origin main
```

Replace `<YOUR_GITHUB_USERNAME>` with your GitHub username. If you created the repository with a README, clone it first and copy these files into the cloned repository instead of running `git init`.

### Step 12 — Verify the GitHub Actions workflow

1. Open the repository's **Actions** tab.
2. The workflow in `.github/workflows/contract-ci.yml` runs on pushes to `main` and pull requests targeting `main`.
3. It installs `datacontract-cli`, lints the ODCS file with `datacontract lint`, then runs the local tests with `pytest`.
4. Verify both steps complete successfully before merging future contract changes.

The workflow does not connect to your Fabric workspace or validate its live Delta tables. Data checks against actual Silver data execute in Notebook 02. You can add authenticated Fabric deployment automation later as a separate CI/CD stage.

### Step 13 — Connect Fabric workspace to GitHub (optional but useful)

Fabric supports Git integration with cloud GitHub repositories for supported workspace items, including Lakehouses, notebooks, and pipelines, subject to tenant settings and feature availability.

1. Make sure the repository is created and pushed first.
2. In Fabric, open `ws-nyc-taxi-data-contracts-dev` → **Workspace settings → Git integration**.
3. Choose **GitHub**, connect your account, select the repository and `main` branch, and choose a workspace folder if prompted.
4. Your tenant admin may need to enable the GitHub repository sync tenant setting. Workspace admin rights and a GitHub personal access token with the documented repository contents permissions may be required.
5. Review the pending changes carefully before committing/syncing. Do not assume Lakehouse table data is checked into Git; Fabric Git integration versions supported item definitions/metadata, not the actual table data or files stored in OneLake.
6. For a safer production workflow, use feature branches or separate Dev/Test workspaces, review diffs, and test before syncing a changed notebook to the shared workspace.

If Git integration is not available in your tenant, the repository still works as standard GitHub source control for the contract, notebook files, tests, and GitHub Actions.

## Part C — Demonstrate that the contract matters

### Step 14 — Change a rule deliberately

1. Create a branch: `git checkout -b feature/tighten-trip-distance-policy`.
2. Change the stated maximum distance in `contracts/nyc_taxi_silver.odcs.yaml` and the matching policy implementation/tests.
3. Open a pull request. GitHub Actions should lint the contract and run tests.
4. If the contract becomes invalid YAML or the code/tests disagree with expected behavior, the checks should fail.
5. After merge, upload the revised contract to OneLake before rerunning the Fabric Silver notebook.

For a more mature lifecycle, keep versioned contracts (`1.0.0`, `1.1.0`, etc.), add previous versions as CI comparison inputs, and use `datacontract breaking` where appropriate to detect backward-incompatible changes. A breaking change needs a consumer migration plan; editing the file alone is not a complete rollout.

### Step 15 — Simulate a quality failure in Fabric

In a disposable development workspace only, temporarily add a test condition to Notebook 02, such as treating a `trip_distance` of 0 as acceptable, or change the expected column name in a copied contract. Then rerun validation and inspect:

- Failed check in `dq_contract_results`.
- A stopped notebook run if a blocking validation failed.
- Quarantined records and their reasons.
- No refresh of Gold from a failed validation run.

Restore the published policy immediately after the demonstration. Do not change production workspace rules merely to create a demo failure.

## Contract ownership and operating model

| Area | Proposed owner | Responsibility |
|---|---|---|
| Source ingestion | Data Engineering | Load published monthly files and preserve provenance |
| ODCS contract | Data Product Owner + Data Engineering | Approve fields, definitions, and compatibility changes |
| Quality implementation | Data Engineering / Data Quality | Implement and monitor checks; retain quarantine evidence |
| Gold consumption | Analytics / Finance / Operations | Use the documented definitions and report defects |
| Change review | Repository maintainers + consumers | Review PRs and coordinate breaking changes |

## Troubleshooting

- **Notebook cannot find `/lakehouse/default/Files/...`:** Attach the Lakehouse and set it as the notebook's default Lakehouse. Verify the file exists in Files.
- **Notebook cannot find the contract:** Upload `nyc_taxi_silver.odcs.yaml` to `Files/contracts/` exactly as named.
- **`import yaml` fails:** Install PyYAML in a Fabric Environment/library configuration, publish the environment if required, attach it to the notebook, and rerun the notebook.
- **Parquet download fails:** Verify the Fabric session can reach `d37ci6vzurychx.cloudfront.net`; rerun ingestion after a transient network issue.
- **Column mismatch:** Check the notebook's `source-to-canonical` mapping against the selected month's Parquet schema. TLC warns that source schemas can change across years/months.
- **Git integration missing:** Check Fabric capacity, tenant settings, workspace-admin privileges, and GitHub repository permissions.
- **`datacontract lint` fails:** Read the CI log, verify YAML indentation and ODCS v3.1.0 field syntax, then rerun locally with `datacontract lint contracts/nyc_taxi_silver.odcs.yaml`.

## Run checks locally

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
datacontract lint contracts/nyc_taxi_silver.odcs.yaml
python -m pytest -q
```

## References

- Open Data Contract Standard v3.1.0: https://bitol-io.github.io/open-data-contract-standard/v3.1.0/
- Atlan data contracts overview: https://atlan.com/data-contracts/
- Data Contract CLI: https://github.com/datacontract/datacontract-cli
- NYC TLC Trip Record Data: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
- Fabric Data Engineering: https://learn.microsoft.com/en-us/fabric/data-engineering/
- Fabric Git integration overview: https://learn.microsoft.com/en-us/fabric/cicd/git-integration/intro-to-git-integration
- Fabric notebook activity in pipelines: https://learn.microsoft.com/en-us/fabric/data-factory/notebook-activity

## Source data note

The project downloads public NYC TLC source files at runtime. It does not package the source Parquet dataset in this repository. Public data availability, schema, and completeness are controlled by the publisher, not by this project.
