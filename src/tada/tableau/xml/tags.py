from lxml import etree


def get_local_tag_name(tag: etree.QName | str) -> str:
    """Return the local (namespace-free) name of an XML tag.

    Accepts either:
    - `lxml.etree.QName`
    - a tag string, optionally in Clark notation: "{namespace}local"

    Returns the local part (e.g. "local").

    Args:
        tag: An XML tag name or QName.

    Returns:
        The local tag name with any namespace prefix/URI removed.
    """
    if isinstance(tag, etree.QName):
        return tag.localname

    tag_str = str(tag)
    if "}" not in tag_str:
        return tag_str

    return tag_str.split("}", 1)[1]
