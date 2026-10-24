"""Prepare an auditable clean copy of UCI Online Retail without database writes."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from app.data.transformer import transform_online_retail


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx", help="Original UCI XLSX file path.")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data" / "processed", help="Output directory for CSV and JSON files.")
    parser.add_argument("--sheet", default="0", help="Excel sheet name or zero-based index (default: 0).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        print(f"ERROR: Workbook not found: {args.input}\nDownload UCI Online Retail and place it at data/raw/Online Retail.xlsx, or pass --input PATH.", file=sys.stderr)
        return 2
    try:
        sheet = int(args.sheet) if str(args.sheet).isdigit() else args.sheet
        source = pd.read_excel(args.input, sheet_name=sheet, engine="openpyxl")
        result = transform_online_retail(source)
    except (ValueError, OSError, ImportError) as exc:
        print(f"ERROR: Could not prepare dataset: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: Unexpected preparation failure ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sales_path = args.output_dir / "sales_lines.csv"
    excluded_path = args.output_dir / "excluded_rows.csv"
    report_path = args.output_dir / "data_quality_report.json"
    result.sales_lines.to_csv(sales_path, index=False, encoding="utf-8")
    result.excluded_rows.to_csv(excluded_path, index=False, encoding="utf-8")
    report_path.write_text(json.dumps(result.report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("UCI Online Retail preparation complete.")
    print(f"Accepted sales lines : {result.report['accepted_sales_lines']:,}")
    print(f"Excluded source rows : {result.report['excluded_rows']:,}")
    print(f"Distinct invoices    : {result.report['distinct_invoices']:,}")
    print(f"Distinct products    : {result.report['distinct_products']:,}")
    print(f"Identified customers : {result.report['distinct_identified_customers']:,}")
    print(f"Sales lines          : {sales_path}")
    print(f"Excluded rows        : {excluded_path}")
    print(f"Quality report       : {report_path}")
    print("No database connection was opened and no database rows were modified.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
