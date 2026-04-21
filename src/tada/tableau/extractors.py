from collections import defaultdict
from typing import Any

from lxml import etree

from tada.tableau.field_refs import build_field_map, replace_values
from tada.tableau.xml.select import select_elements
from tada.tableau.xml.serialize import subtree_to_dict


def extract_keyed_subtrees(
    root: etree._Element,
    xpath: str,
    *,
    key_attr: str,
    default_key: str,
    excluded_tags: set[str] | None = None,
    skip_ui_attrs: bool = True,
) -> dict[str, Any]:
    out: dict[str, dict] = {}
    for node in select_elements(root, xpath):
        key = node.attrib.get(key_attr, default_key)

        node_dict = subtree_to_dict(
            node,
            excluded_tags=excluded_tags,
            skip_ui_attrs=skip_ui_attrs,
        )

        if node_dict is not None:
            out[key] = node_dict

    return out


def extract_dashboards(
    root: etree._Element,
) -> dict[str, Any]:
    return extract_keyed_subtrees(
        root=root,
        xpath="/workbook/dashboards/dashboard",
        key_attr="name",
        default_key="dashboards",
        excluded_tags={"column", "column-instance", "cols", "style", "zone-style"},
    )


def extract_worksheets(
    root: etree._Element,
) -> dict[str, Any]:
    return extract_keyed_subtrees(
        root=root,
        xpath="/workbook/worksheets/worksheet",
        key_attr="name",
        default_key="worksheets",
        excluded_tags={"style", "layout-options", "simple-id"},
    )


def extract_datasources(
    root: etree._Element,
) -> dict[str, Any]:
    return extract_keyed_subtrees(
        root=root,
        xpath="/workbook/datasources/datasource[@name != 'Parameters']",
        key_attr="caption",
        default_key="datasources",
        excluded_tags={
            "column",
            "column-instance",
            "cols",
            "style",
            "layout",
            "group",
            "metadata-records",
            "folders-common",
        },
    )


def extract_parameters(
    root: etree._Element,
) -> dict[str, Any]:
    return extract_keyed_subtrees(
        root=root,
        xpath="/workbook/datasources/datasource[@name = 'Parameters']",
        key_attr="caption",
        default_key="parameters",
    )


def extract_tables(root: etree._Element) -> dict[str, Any]:
    return extract_keyed_subtrees(
        root=root,
        xpath="/workbook/datasources/datasource[@name != 'Parameters']/connection/relation",
        key_attr="name",
        default_key="tables",
    )


def extract_calculations(root: etree._Element) -> dict[str, Any]:
    raw_payload = extract_keyed_subtrees(
        root=root,
        xpath="/workbook/datasources/datasource[@name != 'Parameters']/column[calculation]",
        key_attr="name",
        default_key="unknown",
    )

    field_map = build_field_map(raw_payload)
    resolved = replace_values(raw_payload, field_map, skip_keys={"name"})

    return resolved


def extract_actions(
    root: etree._Element,
) -> dict[str, Any]:
    buckets: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for action_node in select_elements(root, "/workbook/actions/*"):
        action_type = etree.QName(action_node).localname

        action_dict = (
            subtree_to_dict(
                action_node,
                excluded_tags=set(),
                skip_ui_attrs=True,
            )
            or {}
        )

        dash = action_node.xpath("source/@dashboard")
        dashboard_name = (
            str(dash[0]).strip()
            if isinstance(dash, list) and dash and str(dash[0]).strip()
            else "Unknown"
        )

        buckets[action_type][dashboard_name].append(action_dict)

    # NOTE: if you truly want document order, don’t sort here.
    actions_out: dict[str, list[dict[str, Any]]] = {}
    for action_type in sorted(buckets.keys()):
        dashboards_out: list[dict[str, Any]] = []
        for dashboard_name in sorted(buckets[action_type].keys()):
            dashboards_out.append(
                {
                    "dashboard": dashboard_name,
                    action_type: buckets[action_type][dashboard_name],
                }
            )
        actions_out[f"dashboard_{action_type}"] = dashboards_out

    return actions_out
