import json
from executor.selenium_executor import SeleniumExecutor

BASE_URL = "https://www.saucedemo.com/"

with open("mappings/mapping.json", "r", encoding="utf-8") as f:
    mapping = json.load(f)

executor = SeleniumExecutor(mapping, BASE_URL)
executor.run_all_from_csv()