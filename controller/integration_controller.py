from engine.mapper import ActionMapper, MappingError


def prepare_execution(paths, mapping_path):
    mapper = ActionMapper(mapping_path)

    errors = mapper.validate()

    if errors:
        error_message = "\n".join(errors)
        raise MappingError(error_message)

    execution_plan = []

    for path in paths:
        path_id = path.get("path_id")
        steps = path.get("steps")

        if path_id is None:
            raise ValueError("Mỗi path phải có path_id")

        if not steps:
            raise ValueError(f"Path {path_id} không có steps")

        mapped_steps = mapper.map_path(steps)

        execution_plan.append({
            "path_id": path_id,
            "original_steps": steps,
            "mapped_steps": mapped_steps
        })

    return execution_plan