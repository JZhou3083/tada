import zipfile
from pathlib import Path


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
