"""Shared in-memory report packaging; domain calculations live in their own modules."""
import io
from pathlib import PurePosixPath
import zipfile

import pandas as pd


def package_evidence(files: dict[str, str | bytes], tables: dict[str, pd.DataFrame]) -> bytes:
    """Package original artifacts and tables with stable metadata and safe member paths."""
    artifacts = dict(files)
    artifacts.update({f"{name}.csv": frame.to_csv(index=False) for name, frame in tables.items()})
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in artifacts.items():
            if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts or "\\" in name:
                raise ValueError("Report members must have safe relative paths")
            member = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(member, value.encode("utf-8") if isinstance(value, str) else value)
    return stream.getvalue()
