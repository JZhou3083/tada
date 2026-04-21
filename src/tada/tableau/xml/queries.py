from lxml import etree


def select_elements(
    root: etree._Element, xpath_expr: str, *, strict: bool = True
) -> list[etree._Element]:
    """Evaluate an XPath expression and return only element nodes.

    Args:
        root: Context node for XPath evaluation.
        xpath_expr: XPath expression expected to produce a node-set.
        strict: If True, raise TypeError when the XPath result is not a list
            (i.e., the XPath evaluates to a scalar such as bool/float/str).
            If False, return an empty list in that case.

    Returns:
        List of matching elements (non-element XPath results are filtered out).

    Raises:
        TypeError: If strict=True and the XPath expression does not return a node-set.
    """
    result = root.xpath(xpath_expr)

    if not isinstance(result, list):
        if strict:
            raise TypeError(
                f"XPath expression must return a node-set (list); got {type(result).__name__} for expr={xpath_expr!r}"
            )
        return []

    return [n for n in result if isinstance(n, etree._Element)]
