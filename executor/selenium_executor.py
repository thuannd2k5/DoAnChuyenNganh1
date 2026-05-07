import os
import csv
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SeleniumExecutor:

    def __init__(self, mapping: dict, base_url: str):
        self.mapping = mapping
        self.base_url = base_url

        # CSV luôn nằm cố định trong reports/
        self.csv_path = "find_latest_csv()"
        
        # folder screenshot cố định
        self.screenshot_folder = "reports/screenshots"
        os.makedirs(self.screenshot_folder, exist_ok=True)

    # ==============================
    # 1. Start Chrome Driver
    # ==============================
    def start_driver(self):
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        driver.maximize_window()
        return driver

    # ==============================
    # 2. Screenshot
    # ==============================
    def take_screenshot(self, driver, path_id="unknown", action="error"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"path_{path_id}_{action}_{timestamp}.png"
        filepath = os.path.join(self.screenshot_folder, filename)

        driver.save_screenshot(filepath)
        return filepath

    # ==============================
    # 3. Read CSV Paths
    # ==============================
    def load_paths_from_csv(self):
        """
        Đọc reports/paths.csv
        Format CSV:
        path_id,actions
        1,"a,b,c"
        2,"a,c"
        """

        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"Không tìm thấy file CSV tại: {self.csv_path}")

        paths = []

        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                path_id = row["path_id"]
                actions_str = row["actions"].replace('"', '')
                actions = actions_str.split(",")

                paths.append({
                    "path_id": path_id,
                    "actions": actions
                })

        return paths

    # ==============================
    # 4. Execute Single Action
    # ==============================
    def execute_action(self, driver, action_code: str):
        """
        Input: action_code ví dụ "a"
        Output: chạy đúng lệnh Selenium tương ứng trong mapping.json
        """

        if action_code not in self.mapping:
            raise Exception(f"Không tìm thấy action '{action_code}' trong mapping.json")

        action = self.mapping[action_code]
        action_type = action.get("type")

        # default selector type: CSS
        selector = action.get("selector")
        value = action.get("value")

        wait = WebDriverWait(driver, 10)

        if action_type == "click":
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            element.click()

        elif action_type == "input":
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            element.clear()
            element.send_keys(value)

        elif action_type == "wait_url":
            wait.until(EC.url_contains(value))

        elif action_type == "wait_element":
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))

        else:
            raise Exception(f"Action type không hợp lệ: {action_type}")

    # ==============================
    # 5. Run One Path
    # ==============================
    def run_path(self, path_id: str, actions: list):
        """
        Input: actions = ["a","b","c"]
        Output: True nếu chạy thành công, False nếu fail
        """

        driver = self.start_driver()
        driver.get(self.base_url)

        try:
            for act in actions:
                self.execute_action(driver, act)

            driver.quit()
            return True

        except Exception as e:
            screenshot_path = self.take_screenshot(driver, path_id, act)
            driver.quit()

            print(f"[FAIL] Path {path_id} lỗi tại action '{act}'")
            print(f"Screenshot: {screenshot_path}")
            print(f"Error: {e}")

            return False

    # ==============================
    # 6. Run All Paths From CSV
    # ==============================
    def run_all_from_csv(self):
        """
        Đọc CSV và chạy toàn bộ path
        """

        paths = self.load_paths_from_csv()

        results = []
        total = len(paths)
        passed = 0

        for p in paths:
            path_id = p["path_id"]
            actions = p["actions"]

            print(f"\n[RUNNING] Path {path_id}: {actions}")

            ok = self.run_path(path_id, actions)

            if ok:
                passed += 1
                results.append((path_id, "PASS"))
                print(f"[PASS] Path {path_id}")
            else:
                results.append((path_id, "FAIL"))

        failed = total - passed

        print("\n==================== SUMMARY ====================")
        print(f"TOTAL : {total}")
        print(f"PASS  : {passed}")
        print(f"FAIL  : {failed}")
        print("=================================================")

        return results