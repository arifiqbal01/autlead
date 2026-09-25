from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.models.schemas.acquisition_plan import AcquisitionPlan


ACQUISITION_CONFIG_DIR = Path(__file__).parent / "acquisition"


class AcquisitionPlanNotFoundError(FileNotFoundError):
    pass


class AcquisitionPlanLoadError(ValueError):
    pass


def load_acquisition_plan(
    name: str,
) -> AcquisitionPlan:
    path = _resolve_acquisition_plan_path(name)

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            raw = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise AcquisitionPlanLoadError(
            f"Invalid YAML in acquisition plan '{name}'."
        ) from exc
    except OSError as exc:
        raise AcquisitionPlanLoadError(
            f"Could not read acquisition plan '{name}'."
        ) from exc

    if raw is None:
        raise AcquisitionPlanLoadError(
            f"Acquisition plan '{name}' is empty."
        )

    if not isinstance(raw, dict):
        raise AcquisitionPlanLoadError(
            f"Acquisition plan '{name}' must contain "
            "a YAML mapping at the root."
        )

    try:
        return AcquisitionPlan.model_validate(raw)
    except ValidationError as exc:
        raise AcquisitionPlanLoadError(
            f"Acquisition plan '{name}' failed validation:\n"
            f"{exc}"
        ) from exc


def _resolve_acquisition_plan_path(
    name: str,
) -> Path:
    normalized_name = name.strip()

    if not normalized_name:
        raise AcquisitionPlanNotFoundError(
            "Acquisition plan name cannot be empty."
        )

    if normalized_name.endswith(".yaml"):
        normalized_name = normalized_name[:-5]
    elif normalized_name.endswith(".yml"):
        normalized_name = normalized_name[:-4]

    if (
        "/" in normalized_name
        or "\\" in normalized_name
        or normalized_name in {".", ".."}
    ):
        raise AcquisitionPlanNotFoundError(
            f"Invalid acquisition plan name: '{name}'."
        )

    yaml_path = (
        ACQUISITION_CONFIG_DIR
        / f"{normalized_name}.yaml"
    )

    yml_path = (
        ACQUISITION_CONFIG_DIR
        / f"{normalized_name}.yml"
    )

    if yaml_path.is_file():
        return yaml_path

    if yml_path.is_file():
        return yml_path

    raise AcquisitionPlanNotFoundError(
        f"Acquisition plan '{normalized_name}' "
        f"was not found in {ACQUISITION_CONFIG_DIR}."
    )