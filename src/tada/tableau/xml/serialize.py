from collections import defaultdict
from typing import Any

from lxml import etree

from tada.tableau.xml.tags import get_local_tag_name

UI_ATTR_TOKEN = "tableausoftware.com/xml/user"


def subtree_to_dict(
    el: etree._Element,
    *,
    strip_blank_text: bool = True,
    excluded_tags: set[str] | None = None,
    skip_ui_attrs: bool = True,  # TODO: this a tableau specific policy and shouldn't live here
) -> dict[str, Any] | None:
    """
    Convert an XML element subtree into a nested dict.

    - Drops elements whose local tag name is in `excluded_tags`
    - Keeps attributes based on `keep_attribute` predicate (if provided)
    - Collapses repeated child tags into lists
    - Stores element text under "#text" (optionally stripping whitespace)
    """
    excluded_tags = excluded_tags or set()
    if get_local_tag_name(el.tag) in excluded_tags:
        return None

    # Attributes (optionally skipping UI attrs)
    node: dict[str, Any] = {
        get_local_tag_name(str(k)): str(v)
        for k, v in el.attrib.items()
        if not (
            skip_ui_attrs
            and (UI_ATTR_TOKEN in str(k) or UI_ATTR_TOKEN in get_local_tag_name(str(k)))
        )
    }

    # Text
    text = el.text or ""
    text = text.strip() if strip_blank_text else text
    if text:
        node["#text"] = text

    # Children -> bucket by tag name, then collapse 1-item lists
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for child in el:
        child_dict = subtree_to_dict(
            child,
            strip_blank_text=strip_blank_text,
            excluded_tags=excluded_tags,
            skip_ui_attrs=skip_ui_attrs,
        )
        if child_dict is not None:
            buckets[get_local_tag_name(child.tag)].append(child_dict)

    for tag_name, items in buckets.items():
        node[tag_name] = items[0] if len(items) == 1 else items

    return node
