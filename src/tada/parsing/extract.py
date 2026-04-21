from typing import Any

from lxml import etree

from tada.xml.serialize import xml_subtree_to_dict
from tada.xml.xpath import select_elements


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

        node_dict = xml_subtree_to_dict(
            node,
            excluded_tags=excluded_tags,
            skip_ui_attrs=skip_ui_attrs,
        )

        if node_dict is not None:
            out[key] = node_dict

    return out
