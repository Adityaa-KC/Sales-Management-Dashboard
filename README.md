# SmartRetail: Intelligent Sales Management & Inventory Optimization

SmartRetail is a Python and Streamlit application for managing retail sales and inventory, viewing business KPIs, and exploring transaction data with machine-learning-based analytics.

<https://sales-management-dashboard.streamlit.app/>

## Overview

SmartRetail is designed around a relational PostgreSQL database. The application uses a shared database schema for stores, products, customers, inventory, sales, and sale items. The UCI Online Retail dataset can be imported into a separate demonstration store so historical sample data does not get mixed with the user's own store records.

### Main capabilities

- **Business dashboard:** overview metrics for sales, revenue, inventory, and low-stock alerts.
- **Sales management:** sales and transaction records backed by the database.
- **Inventory management:** product stock levels and reorder-level monitoring where inventory data is available.
- **Customer views:** customer records associated with a store.
- **Market Basket Analysis:** Apriori frequent-itemset mining and association rules, with support, confidence, lift, leverage, and conviction metrics.
- **UCI demonstration dataset:** a data-preparation pipeline that validates and cleans the public dataset, plus an optional importer for a separate GBP demo store.
- **Database-backed pages:** store-scoped queries are intended to keep dashboard figures consistent with the selected store.

### Analytics status

Market Basket Analysis has been run against the processed UCI Online Retail dataset. In the reported run, the pipeline contained 20,726 invoices, 18,338 multi-product baskets, and 3,941 distinct product codes. The interface displayed up to 100 rules for the selected thresholds.

Customer segmentation and demand forecasting are part of the project direction; do not describe them as production-ready until their models have been implemented, tested, and evaluated against held-out data.

## Technology stack

- **Language:** Python
- **Web app:** Streamlit
- **Database:** PostgreSQL
- **ORM and migrations:** SQLAlchemy and Alembic
- **Data processing:** Pandas, NumPy
- **Machine learning / analytics:** scikit-learn, mlxtend; Prophet is listed for forecasting work
- **Visualization:** Plotly and Streamlit charts
- **Tests:** pytest

## Project structure

```text
Sales-Management-Dashboard/
├── app.py
├── app/
│   ├── analytics/
│   │   ├── market_basket.py
│   │   ├── segmentation.py
│   │   └── forecasting.py
│   ├── database/
│   │   ├── connection.py
│   │   └── models.py
│   ├── data/
│   │   ├── importer.py
│   │   └── transformer.py
│   ├── services/
│   └── utils/
├── pages/
│   ├── analytics.py
│   ├── sales.py
│   ├── inventory.py
│   ├── Customers_and_Segments.py
│   ├── Demand_Forecast.py
│   └── market_basket.py
├── scripts/
│   ├── prepare_uci_retail.py
│   └── import_uci_to_database.py
├── tests/
├── alembic/
├── data/
│   ├── raw/          # Local source files; do not commit
│   └── processed/    # Generated data; do not commit
├── requirements.txt
└── README.md
```

The exact files in your local checkout may vary as development continues.

## Requirements

- Python version supported by your installed Streamlit, Pandas, and project dependencies.
- A PostgreSQL database reachable from the app.
- Git (optional, for cloning and version control).
- The UCI Online Retail workbook only if you plan to prepare or import the demo dataset.

## Local setup

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd Sales-Management-Dashboard
```

Replace the URL with your actual GitHub repository URL.

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If the project uses a Python version incompatible with one of the pinned dependencies, use a compatible Python environment and update dependency pins deliberately rather than installing packages globally.

### 4. Configure the database connection

The application reads the database URL from Streamlit secrets. Create this file locally:

`.streamlit/secrets.toml`

```toml
[database]
url = "postgresql+psycopg://USERNAME:PASSWORD@HOST:PORT/DATABASE"
```

Replace the example values with your PostgreSQL credentials. The application configuration currently requires SSL for database connections.

**Security:** never commit `.streamlit/secrets.toml`, database passwords, API keys, or any other secrets to GitHub. Configure the same values in your hosting provider's secret/settings panel for deployment.

### 5. Apply database migrations

If the database has not already been initialized, review the existing Alembic migration history and run:

```bash
alembic upgrade head
```

Do not regenerate or delete migrations simply to fix a connection issue. Back up the database before applying schema changes.

### 6. Run the app

```bash
streamlit run app.py
```

Streamlit will print a local URL in the terminal, commonly `http://localhost:8501`.

## Preparing the UCI Online Retail dataset

The public UCI Online Retail dataset is historical data from a UK retailer. It is for demonstration and development, not a representation of your live store.

1. Download the workbook from the [official UCI dataset page](https://archive.ics.uci.edu/dataset/352/online%2Bretail).
2. Save it locally as `data/raw/Online Retail.xlsx`.
3. Prepare a clean dataset:

   ```bash
   python scripts/prepare_uci_retail.py
   ```

4. Review the outputs in `data/processed/`:
   - `sales_lines.csv`
   - `excluded_rows.csv`
   - `data_quality_report.json`

The preparation step handles invalid required values, cancellation invoices, negative-quantity return rows, missing customer IDs, and missing descriptions according to the implemented transformation rules. It preserves an exclusion report for review.

### Optional: import to a separate demo store

Back up your database first. Run the importer's dry run:

```bash
python scripts/import_uci_to_database.py
```

Only after reviewing the counts and confirming the target database is correct, explicitly authorize the import:

```bash
python scripts/import_uci_to_database.py --confirm-import
```

The importer is intended to create a separate `UCI Online Retail Demo` store with currency `GBP`. It does not infer current stock levels from historical sales and does not create inventory records for the UCI store.

Do not import the UCI data into your existing real-store records. The source data represents a different retailer, and its prices are in GBP.

## Running tests

Run the full test suite from the repository root:

```bash
python -m pytest -q
```

To run the market basket tests only:

```bash
python -m pytest -q tests/test_market_basket.py
```

If tests are skipped because an optional dependency is unavailable, install the project requirements and rerun them. A skipped test is not a passing validation of that code path.

## Deploying with Streamlit Community Cloud

1. Push the project to a GitHub repository.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/) and create a new app.
3. Select your repository, branch, and `app.py` as the main file.
4. In the app's **Settings / Secrets** area, add your database configuration in TOML format:

   ```toml
   [database]
   url = "postgresql+psycopg://USERNAME:PASSWORD@HOST:PORT/DATABASE"
   ```

5. Confirm that the PostgreSQL host allows connections from the deployment environment and that SSL requirements match the application's connection configuration.
6. Deploy and inspect the logs if startup fails.

Do not include raw dataset files, processed CSVs, database dumps, or credentials in the Git repository. Hosting providers may have storage, memory, execution-time, and database connection limits; test large imports locally or in a controlled environment, not during app startup.

## Add the deployed URL to GitHub's About section

After deployment:

1. Open your repository on GitHub.
2. On the repository page, find **About** on the right side.
3. Click the **gear icon** or **Edit repository details** beside About.
4. Paste your deployed app URL into the **Website** field.
5. Optionally add a short description, such as:

   `Streamlit-based retail sales and inventory management with database-backed analytics and market basket analysis.`
6. Add relevant topics, for example:
   `python`, `streamlit`, `postgresql`, `retail-analytics`, `machine-learning`, `market-basket-analysis`.
7. Click **Save changes**.

The Website field displays the deployed app link near the top of your repository. You can also add the same link near the top of this README so visitors see it immediately.

## Data, currency, and interpretation notes

- The UCI Online Retail dataset uses GBP; the demo store should use `GBP`.
- The UCI dataset does not provide a reliable current stock snapshot or actual product costs.
- Market basket rules describe co-purchase patterns. Association is not causation, and lift/confidence do not guarantee future sales.
- Demonstration data and live-store data should remain separated by store.
- Do not publish customer data, credentials, or database exports.

## Roadmap

- Complete and evaluate RFM customer segmentation with K-Means.
- Implement and evaluate time-series demand forecasting using chronological train/test splits and suitable error metrics.
- Add model-run metadata and explainable analytics summaries.
- Expand automated tests for database import idempotency, data integrity, and multi-store isolation.
- Improve deployment configuration and add screenshots of the live application.

## Dataset citation

Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository.  
https://doi.org/10.24432/C5BW33

---

## License

Add the license appropriate for this project before publishing it. The UCI dataset has its own license and attribution requirements; see the [official dataset page](https://archive.ics.uci.edu/dataset/352/online%2Bretail). Do not assume the dataset license automatically applies to the application source code.
