"""scripts/tests/test_pixiv_export.py — pixiv_export.py の新構造（novel/chNN.md）対応確認"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE.parent.parent / "scripts" / "pixiv_export.py"
SAMPLE_GEN = HERE / "sample_project.py"
WORK = HERE / ".work"
PY = sys.executable


def run(*extra):
    proc = subprocess.run([PY, str(SCRIPT), *extra],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout + proc.stderr


def make_project() -> Path:
    dst = WORK / "pixiv_sample"
    shutil.rmtree(dst, ignore_errors=True)
    proc = subprocess.run([PY, str(SAMPLE_GEN), str(dst)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return dst


def test_export_new_structure():
    p = make_project()
    out = p / "export" / "pixiv.md"
    code, s = run("--project-dir", str(p), "--output", str(out))
    assert code == 0, s
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "美咲は人波を縫って歩いていた" in text       # ch02 本文
    assert "段ボールの山" in text                      # ch01 本文
    assert "章数:" in text or "章数" in text


def test_verify_detects_no_change():
    p = make_project()
    out = p / "export" / "pixiv.md"
    code, s = run("--project-dir", str(p), "--output", str(out))
    assert code == 0, s
    code, s = run("--project-dir", str(p), "--verify")
    assert code == 0, s
    assert "変更なし" in s or "[OK]" in s


def test_old_filename_convention_still_works():
    # 旧規約（NNN-タイトル.md）の後方互換
    p = make_project()
    novel = p / "novel"
    (novel / "01-導入.md").write_text("旧規約の本文です。", encoding="utf-8")
    (novel / "ch01.md").unlink()
    (novel / "ch02.md").unlink()
    out = p / "export" / "pixiv.md"
    code, s = run("--project-dir", str(p), "--output", str(out))
    assert code == 0, s
    assert "旧規約の本文" in out.read_text(encoding="utf-8")
