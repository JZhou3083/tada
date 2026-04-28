from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict

from tada.tableau.extractors import (
    extract_actions,
    extract_calculations,
    extract_dashboards,
    extract_datasources,
    extract_parameters,
    extract_tables,
    extract_worksheets,
)
from tada.tableau.loader import load_workbook_xml
from tada.tableau.xml.prune import drop_xpaths


class WorkbookSection(str, Enum):
    DATASOURCES = "datasources"
    CALCULATIONS = "calculations"
    DASHBOARDS = "dashboards"
    WORKSHEETS = "worksheets"
    ACTIONS = "actions"
    PARAMETERS = "parameters"
    TABLES = "tables"

    def fetch_from(self, workbook: Workbook) -> Any:
        """Return the corresponding attribute from a Workbook object."""
        return getattr(workbook, self.value)


class Workbook(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    datasources: dict[str, Any]
    calculations: dict[str, Any]
    dashboards: dict[str, Any]
    worksheets: dict[str, Any]
    actions: dict[str, Any]
    parameters: dict[str, Any]
    tables: dict[str, Any]

    @classmethod
    def from_file(cls, workbook_path: Path) -> Self:
        """
        Create a Workbook object from a Tableau workbook file e.g. '.twb' or '.twbx'
        """
        root = load_workbook_xml(workbook_path)

        # Remove unwanted Tableau metadata from the tree
        root, _ = drop_xpaths(
            root,
            [
                "//external",
                "//thumbnails",
                "//document-format-change-manifest",
            ],
        )

        # TODO: original code writes the clean XML at this point to a fresh file, needed?
        # TODO: next perform the PII scan

        datasources = extract_datasources(root)
        calculations = extract_calculations(root)
        dashboards = extract_dashboards(root)
        worksheets = extract_worksheets(root)
        actions = extract_actions(root)
        parameters = extract_parameters(root)
        tables = extract_tables(root)

        return cls(
            name=workbook_path.name,
            datasources=datasources,
            calculations=calculations,
            dashboards=dashboards,
            worksheets=worksheets,
            actions=actions,
            parameters=parameters,
            tables=tables,
        )

    def write_debug(self, debug_dir: Path) -> None:
        """
        Write all parsed workbook attributes to JSON files in ``debug_dir``.
        """
        data = self.model_dump(mode="json")
        workbook_attributes = {k: v for k, v in data.items() if k != "name"}

        for attribute_name, attribute_value in workbook_attributes.items():
            output_path = debug_dir / f"{attribute_name}.json"
            output_path.write_text(
                json.dumps(
                    attribute_value, indent=2, ensure_ascii=False, sort_keys=True
                ),
                encoding="utf-8",
            )
