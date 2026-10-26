"""Download the fixed public paper inputs, with resumable checked transfers."""
import hashlib
from importlib.resources import files
import json
import os
from pathlib import Path
import tempfile
import time
from urllib.parse import quote
import zipfile
import requests

from .builders import sha256

MANIFEST = json.loads((files("fulfill_model") / "resources/data_manifest.json").read_text())


def _md5(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "md5").hexdigest()


def _valid_archive(path, group):
    return path.is_file() and path.stat().st_size == group["size"] and _md5(path) == group["md5"]


def _download(path, group, *, get=requests.get, pause=time.sleep, progress=print):
    if _valid_archive(path, group):
        return
    part = path.with_suffix(path.suffix + ".part")
    url = f"https://zenodo.org/api/records/{MANIFEST['record']}/files/{quote(group['filename'])}/content"
    for attempt in range(4):
        offset = part.stat().st_size if part.exists() else 0
        if offset >= group["size"]:
            if offset == group["size"] and _md5(part) == group["md5"]:
                os.replace(part, path)
                return
            part.unlink()
            offset = 0
        try:
            with get(url, headers={"Range": f"bytes={offset}-"} if offset else {},
                     stream=True, timeout=(30, 120)) as response:
                response.raise_for_status()
                if offset and response.status_code == 206:
                    header = response.headers.get("Content-Range", "")
                    if not header.startswith(f"bytes {offset}-") or not header.endswith(f"/{group['size']}"):
                        raise ValueError("Unexpected resume response")
                    mode = "ab"
                else:
                    mode = "wb"
                progress(f"Downloading {group['filename']} ({group['size'] / 1e6:.1f} MB)")
                with part.open(mode) as handle:
                    for chunk in response.iter_content(2**20):
                        if chunk:
                            handle.write(chunk)
                            if handle.tell() > group["size"]:
                                raise ValueError("Downloaded file exceeds published size")
            if part.stat().st_size != group["size"] or _md5(part) != group["md5"]:
                raise OSError("Incomplete download or MD5 mismatch")
            os.replace(part, path)
            return
        except (requests.RequestException, OSError, ValueError) as exc:
            if attempt == 3:
                raise OSError(f"Cannot download {group['filename']}; rerun to resume: {exc}") from exc
            pause(2**attempt)


def ensure_data(directory="Data", *, groups=("shocks", "database"), offline=False, progress=print):
    """Reuse verified local files; fetch only missing groups. Never fetch results."""
    directory = Path(directory)
    if set(groups) - MANIFEST["groups"].keys():
        raise ValueError("Unknown data group")
    for name in groups:
        group = MANIFEST["groups"][name]
        destination = directory / group["directory"]
        missing = []
        for relative, spec in group["files"].items():
            target = destination / relative
            if target.exists():
                if target.stat().st_size != spec["size"] or sha256(target) != spec["sha256"]:
                    raise ValueError(f"Published input differs: {target}. Use a new --data directory; use --inputs for custom shock workbooks.")
            else:
                missing.append(relative)
        if not missing:
            continue
        if offline:
            raise FileNotFoundError(f"Missing {name} inputs in {destination}; run fulfill download or remove --offline")
        cache = directory / ".downloads"
        cache.mkdir(parents=True, exist_ok=True)
        archive = cache / group["filename"]
        _download(archive, group, progress=progress)
        # Select only manifest-listed paths. Mac metadata and arbitrary ZIP paths
        # are never extracted; staged payloads are checked before installation.
        with tempfile.TemporaryDirectory(prefix="fulfill-extract-", dir=cache) as temp:
            with zipfile.ZipFile(archive) as z:
                for relative in missing:
                    spec = group["files"][relative]
                    staged = Path(temp) / relative
                    staged.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(spec["member"]) as source, staged.open("wb") as target:
                        count = 0
                        for chunk in iter(lambda: source.read(2**20), b""):
                            count += len(chunk)
                            if count > spec["size"]:
                                raise ValueError(f"Extracted file exceeds published size: {relative}")
                            target.write(chunk)
                    if staged.stat().st_size != spec["size"] or sha256(staged) != spec["sha256"]:
                        raise ValueError(f"Extracted checksum mismatch: {relative}")
            for relative in missing:
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(Path(temp) / relative, target)
        progress(f"Verified {name}: {destination.resolve()}")
    return directory
