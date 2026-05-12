import os
import csv
import json
import time
from collections import Counter
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
        reports_dir="reports",
        model_data=None
    ):

        self.mapping = mapping
        self.base_url = base_url
        self.csv_path = csv_path
        self.reports_dir = reports_dir
        self.model_data = model_data or {}

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

    def build_transition_map(self):

        transitions = self.model_data.get(
            "transitions",
            []
        )

        return {
            (
                transition["from"],
                transition["action"]
            ): transition["to"]
            for transition in transitions
        }

    def build_state_trace(self, actions):

        start_state = self.model_data.get("start_state")

        if not start_state:
            return []

        transition_map = self.build_transition_map()
        current_state = start_state
        states = [current_state]

        for action in actions:
            next_state = transition_map.get(
                (
                    current_state,
                    action
                )
            )

            if not next_state:
                break

            states.append(next_state)
            current_state = next_state

        return states

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

        start_time = time.perf_counter()
        driver = None
        action = "start"
        failed_action_index = None
        state_trace = self.build_state_trace(actions)

        try:

            driver = self.start_driver()

            driver.get(self.base_url)

            for index, action in enumerate(actions):
                failed_action_index = index
                self.execute_action(
                    driver,
                    action
                )

            duration = round(
                time.perf_counter() - start_time,
                3
            )

            return {
                "path_id": path_id,
                "status": "PASS",
                "actions": actions,
                "failed_action": None,
                "failed_action_index": None,
                "state_trace": state_trace,
                "failed_state": None,
                "duration_seconds": duration,
                "screenshot": None,
                "error": None
            }

        except Exception as e:

            duration = round(
                time.perf_counter() - start_time,
                3
            )
            screenshot = None

            if driver:
                screenshot = self.take_screenshot(
                    driver,
                    path_id,
                    action
                )

            failed_state = None

            if (
                failed_action_index is not None
                and failed_action_index < len(state_trace)
            ):
                failed_state = state_trace[failed_action_index]

            print(f"[FAIL] {e}")
            print(f"Screenshot: {screenshot}")

            return {
                "path_id": path_id,
                "status": "FAIL",
                "actions": actions,
                "failed_action": action,
                "failed_action_index": failed_action_index,
                "state_trace": state_trace,
                "failed_state": failed_state,
                "duration_seconds": duration,
                "screenshot": screenshot,
                "error": str(e)
            }

        finally:

            if driver:
                driver.quit()

    def build_analytics(self, results, total_duration):

        failed_results = [
            result for result in results
            if result["status"] == "FAIL"
        ]

        action_counter = Counter()
        path_counter = Counter()
        state_counter = Counter()

        for result in failed_results:
            failed_action = result.get("failed_action")

            if failed_action:
                action_counter[failed_action] += 1

            path_counter[str(result["path_id"])] += 1

            for state in result.get("state_trace", []):
                state_counter[state] += 1

        slowest_result = max(
            results,
            key=lambda result: result.get(
                "duration_seconds",
                0
            ),
            default=None
        )

        most_failed_action = action_counter.most_common(1)
        most_failed_path = path_counter.most_common(1)
        most_failed_state = state_counter.most_common(1)

        return {
            "total_duration": round(total_duration, 3),
            "average_duration": round(
                total_duration / len(results),
                3
            ) if results else 0,
            "slowest_path": {
                "path_id": slowest_result["path_id"],
                "duration": slowest_result.get(
                    "duration_seconds",
                    0
                )
            } if slowest_result else None,
            "most_failed_action": {
                "action": most_failed_action[0][0],
                "count": most_failed_action[0][1]
            } if most_failed_action else None,
            "most_failed_path": {
                "path_id": most_failed_path[0][0],
                "count": most_failed_path[0][1]
            } if most_failed_path else None,
            "most_failed_state": {
                "state": most_failed_state[0][0],
                "count": most_failed_state[0][1]
            } if most_failed_state else None,
            "failed_actions": [
                {
                    "action": action,
                    "fail_count": count
                }
                for action, count in action_counter.most_common()
            ],
            "failed_paths": [
                {
                    "path_id": path_id,
                    "fail_count": count
                }
                for path_id, count in path_counter.most_common()
            ],
            "failed_states": [
                {
                    "state": state,
                    "fail_frequency": count
                }
                for state, count in state_counter.most_common()
            ]
        }

    def run_all_from_csv(self):

        start_time = time.perf_counter()
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
        total_duration = time.perf_counter() - start_time
        analytics = self.build_analytics(
            results,
            total_duration
        )
        summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            **analytics,
            "results": results
        }

        print("\n===== SUMMARY =====")
        print(f"TOTAL : {total}")
        print(f"PASS  : {passed}")
        print(f"FAIL  : {failed}")
        print(f"TIME  : {summary['total_duration']}s")

        with open(self.report_path, "w", encoding="utf-8") as file:
            json.dump(summary, file, indent=2, ensure_ascii=False)

        print(f"Summary report: {self.report_path}")

        return summary
