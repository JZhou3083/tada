import zipfile
from pathlib import Path

from lxml import etree


def extract_twb_from_twbx(twbx_path: Path) -> bytes:
    """
    Extract the embedded Tableau workbook (.twb) from a packaged workbook (.twbx).

    The function expects the .twbx archive to contain exactly one .twb file and
    returns that file's raw bytes (no decoding, no disk writes).

    Args:
        twbx_path: Path to the source .twbx file.

    Returns:
        The raw contents of the single .twb file as bytes.

    Raises:
        ValueError: If the archive contains no .twb file or contains multiple .twb files.
        zipfile.BadZipFile: If `twbx_path` is not a valid zip archive.
        FileNotFoundError: If `twbx_path` does not exist.
    """
    with zipfile.ZipFile(twbx_path, "r") as zf:
        twb_members = [m for m in zf.namelist() if m.lower().endswith(".twb")]

        if not twb_members:
            raise ValueError("Invalid .twbx: no .twb file found inside the archive.")
        if len(twb_members) > 1:
            raise ValueError(
                "Invalid .twbx: multiple .twb files found inside the archive."
            )

        member = twb_members[0]
        return zf.read(member)


def load_workbook_xml(workbook_path: Path) -> etree._Element:
    """Load a Tableau workbook and return its parsed XML root element.

    Accepts either a plain Tableau workbook (``.twb``) or a packaged
    Tableau workbook (``.twbx``). For ``.twb`` files, the workbook XML is
    read directly from disk. For ``.twbx`` files, the embedded ``.twb``
    workbook is extracted first and then parsed.

    The XML is parsed with comments removed and blank text nodes stripped
    to produce a cleaner tree for downstream processing.

    Args:
        workbook_path: Path to a Tableau workbook file with a ``.twb`` or
            ``.twbx`` extension.

    Raises:
        ValueError: If ``workbook_path`` does not refer to a supported
            Tableau workbook type.
        etree.XMLSyntaxError: If the workbook contents are not valid XML.

    Returns:
        The root element of the parsed Tableau workbook XML.
    """
    match workbook_path.suffix:
        case ".twb":
            twb_bytes = workbook_path.read_bytes()
        case ".twbx":
            twb_bytes = extract_twb_from_twbx(workbook_path)
        case _:
            raise ValueError(
                f"File '{workbook_path}' is not a Tableau workbook ('.twb' or '.twbx')."
            )

    parser = etree.XMLParser(
        remove_comments=True,
        remove_blank_text=True,
        huge_tree=True,
    )
    return etree.fromstring(twb_bytes, parser)
