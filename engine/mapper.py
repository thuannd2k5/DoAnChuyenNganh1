import json


class MappingError(Exception):
    pass


class ActionMapper:
    REQUIRED_FIELDS = {
        "open_url": ["type", "path"],
        "click": ["type", "selector_type", "selector"],
        "input": ["type", "selector_type", "selector", "value"],
        "wait": ["type", "selector_type", "selector"],
        "assert_url_contains": ["type", "expected"],
        "assert_text": ["type", "selector_type", "selector", "expected"]
    }

    def __init__(self, mapping_path):
        self.mapping_path = mapping_path
        self.mapping = self.load_mapping()

    def load_mapping(self):
        try:
            with open(self.mapping_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            raise MappingError(f"Không tìm thấy file mapping: {self.mapping_path}")
        except json.JSONDecodeError:
            raise MappingError("File mapping.json không đúng định dạng JSON")

        if not isinstance(data, dict):
            raise MappingError("mapping.json phải là một object JSON")

        return data

    def validate(self):
        errors = []

        for action_name, action_data in self.mapping.items():
            if not isinstance(action_data, dict):
                errors.append(f"{action_name}: dữ liệu action phải là object")
                continue

            action_type = action_data.get("type")

            if action_type not in self.REQUIRED_FIELDS:
                errors.append(f"{action_name}: type không hợp lệ hoặc chưa được hỗ trợ")
                continue

            required_fields = self.REQUIRED_FIELDS[action_type]

            for field in required_fields:
                if field not in action_data:
                    errors.append(f"{action_name}: thiếu field '{field}'")

        return errors

    def map_action(self, action_name):
        if action_name not in self.mapping:
            raise MappingError(f"Action '{action_name}' không tồn tại trong mapping.json")

        return self.mapping[action_name]

    def map_path(self, steps):
        mapped_steps = []

        for step in steps:
            mapped_steps.append(self.map_action(step))

        return mapped_steps