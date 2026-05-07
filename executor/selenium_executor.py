import os
import csv
import json
from datetime import datetime
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from executor.assertions import (
    assert_element_visible,
    assert_text,
    assert_url_contains
)


class SeleniumExecutor:

    def __init__(
        self,
        mapping,
        base_url,
        csv_path,
        reports_dir="reports"
    ):

        self.mapping = mapping
        self.base_url = base_url
        self.csv_path = csv_path
        self.reports_dir = reports_dir

        self.screenshot_folder = os.path.join(
            reports_dir,
            "screenshots"
        )
        self.report_path = os.path.join(
            reports_dir,
            "execution_summary.json"
        )

        os.makedirs(
            self.screenshot_folder,
            exist_ok=True
        )
        os.makedirs(reports_dir, exist_ok=True)

    def start_driver(self):

        service = Service(
            ChromeDriverManager().install()
        )

        driver = webdriver.Chrome(
            service=service
        )

        driver.maximize_window()

        return driver

    def load_paths_from_csv(self):

        paths = []

        with open(
            self.csv_path,
            "r",
            encoding="utf-8"
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:

                actions = (
                    row["actions"]
                    .replace('"', '')
                    .split(",")
                )
                actions = [
                    action.strip()
                    for action in actions
                    if action.strip()
                ]

                paths.append({
                    "path_id": row["path_id"],
                    "actions": actions
                })

        return paths

    def take_screenshot(
        self,
        driver,
        path_id,
        action
    ):

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        filename = (
            f"path_{path_id}_{action}_{timestamp}.png"
        )

        filepath = os.path.join(
            self.screenshot_folder,
            filename
        )

        driver.save_screenshot(filepath)

        return filepath

    def get_by(self, selector_type):

        selector_map = {
            "css": By.CSS_SELECTOR,
            "id": By.ID,
            "xpath": By.XPATH
        }

        if selector_type not in selector_map:
            raise ValueError(
                f"Unsupported selector_type: {selector_type}"
            )

        return selector_map[selector_type]

    def find_element(self, driver, action, condition):

        selector = action["selector"]
        selector_type = action.get("selector_type", "css")
        by = self.get_by(selector_type)
        wait = WebDriverWait(driver, 10)

        return wait.until(condition((by, selector)))

    def execute_action(
        self,
        driver,
        action_name
    ):

        if action_name not in self.mapping:
            raise Exception(
                f"Action not found in mapping: {action_name}"
            )

        action = self.mapping[action_name]

        action_type = action["type"]

        if action_type == "sequence":

            for step in action["steps"]:
                self.execute_action(driver, step)

        elif action_type == "open_url":

            path = action.get("path", "/")
            driver.get(urljoin(self.base_url, path))

        elif action_type == "click":

            element = self.find_element(
                driver,
                action,
                EC.element_to_be_clickable
            )

            element.click()

        elif action_type == "input":

            value = action["value"]

            element = self.find_element(
                driver,
                action,
                EC.presence_of_element_located
            )

            element.clear()

            element.send_keys(value)

        elif action_type == "wait":

            element = self.find_element(
                driver,
                action,
                EC.visibility_of_element_located
            )

            if not assert_element_visible(element):
                raise Exception("Element is not visible")

        elif action_type == "wait_url":

            expected = action["value"]
            wait = WebDriverWait(driver, 10)
            wait.until(EC.url_contains(expected))

        elif action_type == "assert_url_contains":

            expected = action["expected"]

            ok = assert_url_contains(
                driver,
                expected
            )

            if not ok:
                raise Exception(
                    f"URL assertion fail: {expected}"
                )

        elif action_type == "assert_text":

            expected = action["expected"]

            element = self.find_element(
                driver,
                action,
                EC.presence_of_element_located
            )

            if not assert_text(element, expected):
                raise Exception(
                    f"Text assertion fail: expected '{expected}', actual '{element.text.strip()}'"
                )

        else:

            raise ValueError(
                f"Unsupported action type: {action_type}"
            )

    def run_path(
        self,
        path_id,
        actions
    ):

        driver = self.start_driver()
        action = "start"

        driver.get(self.base_url)

        try:

            for action in actions:
                self.execute_action(
                    driver,
                    action
                )

            driver.quit()

            return {
                "path_id": path_id,
                "status": "PASS",
                "screenshot": None,
                "error": None
            }

        except Exception as e:

            screenshot = self.take_screenshot(
                driver,
                path_id,
                action
            )

            print(f"[FAIL] {e}")
            print(f"Screenshot: {screenshot}")

            driver.quit()

            return {
                "path_id": path_id,
                "status": "FAIL",
                "screenshot": screenshot,
                "error": str(e)
            }

    def run_all_from_csv(self):

        paths = self.load_paths_from_csv()

        total = len(paths)

        results = []

        for p in paths:

            path_id = p["path_id"]

            actions = p["actions"]

            print(f"\nRUNNING PATH {path_id}")

            result = self.run_path(
                path_id,
                actions
            )
            results.append(result)

            if result["status"] == "PASS":
                print(f"PASS PATH {path_id}")

            else:
                print(f"FAIL PATH {path_id}")

        passed = len([
            result for result in results
            if result["status"] == "PASS"
        ])
        failed = total - passed
        summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "results": results
        }

        print("\n===== SUMMARY =====")
        print(f"TOTAL : {total}")
        print(f"PASS  : {passed}")
        print(f"FAIL  : {failed}")

        with open(self.report_path, "w", encoding="utf-8") as file:
            json.dump(summary, file, indent=2, ensure_ascii=False)

        print(f"Summary report: {self.report_path}")

        return summary
