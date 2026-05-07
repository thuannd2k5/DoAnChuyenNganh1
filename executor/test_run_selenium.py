import argparse
import json
from executor.selenium_executor import SeleniumExecutor

parser = argparse.ArgumentParser()
parser.add_argument("--base-url", required=True)
parser.add_argument("--mapping", required=True)
parser.add_argument("--csv-path", required=True)
parser.add_argument("--reports-dir", default="reports")
args = parser.parse_args()

with open(args.mapping, "r", encoding="utf-8") as f:
    mapping = json.load(f)

executor = SeleniumExecutor(
    mapping,
    args.base_url,
    args.csv_path,
    reports_dir=args.reports_dir
)
executor.run_all_from_csv()
