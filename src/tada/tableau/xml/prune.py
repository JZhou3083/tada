from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy

from lxml import etree


def drop_xpaths(
    root: etree._Element,
    xpaths: Iterable[str],
) -> tuple[etree._Element, int]:
    """
    Return a copy of `root` with nodes matching any of the given XPath expressions removed.

    This function does NOT mutate the input tree. It deep-copies `root`, applies removals
    to the copy, and returns the new root plus the number of removed elements.

    Args:
        root: Root element of the XML tree to copy and prune.
        xpaths: XPath expressions evaluated against the copied tree. Each matched element is removed.

    Returns:
        (new_root, removed_count):
            new_root is the pruned copy of the original root.
            removed_count is the number of elements removed.
    """
    new_root = deepcopy(root)
    removed = 0

    for xpath_expr in xpaths:
        result = new_root.xpath(xpath_expr)

        # .xpath() can return different types depending on expression/result
        if not isinstance(result, list):
            continue

        for node in result:
            if not isinstance(node, etree._Element):
                continue

            parent = node.getparent()
            if isinstance(parent, etree._Element):
                parent.remove(node)
                removed += 1

    return new_root, removed
