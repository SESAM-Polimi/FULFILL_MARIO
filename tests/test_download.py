import hashlib
import json
from pathlib import Path
import zipfile
import pytest

from fulfill_model import data


class Response:
    def __init__(self, content, status=200, headers=None):
        self.content,self.status_code,self.headers = content,status,headers or {}
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def raise_for_status(self): pass
    def iter_content(self, size): yield self.content


def spec(content):
    return dict(filename="example.zip",size=len(content),md5=hashlib.md5(content).hexdigest())


def test_download_resumes_and_verifies(tmp_path):
    payload=b"a checked download"
    target=tmp_path/"example.zip"
    target.with_suffix(".zip.part").write_bytes(payload[:4])
    def get(url,headers,**kw):
        assert headers == {"Range":"bytes=4-"}
        return Response(payload[4:],206,{"Content-Range":f"bytes 4-{len(payload)-1}/{len(payload)}"})
    data._download(target,spec(payload),get=get,pause=lambda _:None,progress=lambda _:None)
    assert target.read_bytes() == payload


def test_server_ignoring_range_restarts(tmp_path):
    payload=b"complete"
    target=tmp_path/"example.zip";target.with_suffix(".zip.part").write_bytes(b"bad")
    data._download(target,spec(payload),get=lambda *a,**k:Response(payload),pause=lambda _:None,progress=lambda _:None)
    assert target.read_bytes()==payload


def test_bad_checksum_never_installed(tmp_path):
    target=tmp_path/"example.zip"
    with pytest.raises(OSError,match="Cannot download"):
        data._download(target,spec(b"good"),get=lambda *a,**k:Response(b"evil"),pause=lambda _:None,progress=lambda _:None)
    assert not target.exists()


def test_extracts_only_manifest_members_and_detects_edits(tmp_path,monkeypatch):
    cache=tmp_path/".downloads";cache.mkdir()
    path=cache/"small.zip"
    with zipfile.ZipFile(path,"w") as z:
        z.writestr("flows/safe.txt",b"safe")
        z.writestr("../outside.txt",b"not selected")
        z.writestr("__MACOSX/._safe.txt",b"not selected")
    group=spec(path.read_bytes())|dict(filename="small.zip",directory="database",files={"flows/safe.txt":dict(member="flows/safe.txt",size=4,sha256=hashlib.sha256(b"safe").hexdigest())})
    monkeypatch.setattr(data,"MANIFEST",dict(record=15341618,groups={"database":group}))
    data.ensure_data(tmp_path,groups=("database",),progress=lambda _:None)
    assert (tmp_path/"database/flows/safe.txt").read_bytes()==b"safe"
    assert not (tmp_path.parent/"outside.txt").exists()
    data.ensure_data(tmp_path,groups=("database",),offline=True)
    (tmp_path/"database/flows/safe.txt").write_bytes(b"edit")
    with pytest.raises(ValueError,match="differs"):
        data.ensure_data(tmp_path,groups=("database",),offline=True)


def test_offline_does_not_fetch(tmp_path,monkeypatch):
    monkeypatch.setattr(data,"_download",lambda *a,**k:pytest.fail("download called offline"))
    with pytest.raises(FileNotFoundError):
        data.ensure_data(tmp_path,groups=("shocks",),offline=True)
