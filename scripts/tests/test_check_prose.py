"""scripts/tests/test_check_prose.py — check_prose.py の受け入れテスト"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "check_prose.py"
sys.path.insert(0, str(HERE))
from sample_project import build  # noqa: E402

WORK = HERE / ".work"
PY = sys.executable


def run(project: Path, *extra):
    proc = subprocess.run(
        [PY, str(SCRIPT), "--project-dir", str(project), *extra],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, (proc.stdout + proc.stderr)


@pytest.fixture()
def sample():
    root = build(WORK / "prose_sample")
    # サンプル本文が短いためしきい値を下げて使う前提だが、中身を肉付け
    root.joinpath("novel/ch01.md").write_text(
        "# 第1章 導入\n\n美咲は段ボールの山を前にしてため息をついた。\n"
        "今日一日の疲れが背中にのしかかる。夜の臼井は静かだった。\n"
        "湯上がりの髪を乾かしながら、彼女は窓の外を見た。\n"
        "〜〜〜テスト本文を十分な長さにするための行がここに入る。〜〜〜\n"
        "夜風が少し涼しい。明日は商店街へ行こうと決めた。\n",
        encoding="utf-8",
    )
    root.joinpath("novel/ch02.md").write_text(
        "# 第2章 接触\n\n商店街のアーケード下、美咲は人波を縫って歩いていた。\n"
        "初対面のはずの老婦人が名を呼んだ。背筋に冷たいものが走る。\n"
        "〜〜〜テスト本文を十分な長さにするための行がここに入る。〜〜〜\n"
        "振り返ると、老婦人が立っていた。言葉が出てこない。\n",
        encoding="utf-8",
    )
    yield root
    shutil.rmtree(root, ignore_errors=True)


def test_sample_passes_with_low_threshold(sample):
    code, out = run(sample, "--min-chars", "50")
    assert code == 0, out


def test_empty_prose_detected(sample):
    # 段落頭全角空白ではなく「空本文」で壊れた事故の再現
    sample.joinpath("novel/ch01.md").write_text("# 第1章 導入\n\n\n", encoding="utf-8")
    code, out = run(sample, "--min-chars", "50")
    assert code == 1
    assert "本文が空" in out, out


def test_missing_novel_file_detected(sample):
    sample.joinpath("novel/ch01.md").unlink()
    code, out = run(sample, "--min-chars", "50")
    assert code == 1
    assert "本文ファイルが存在しない" in out, out


def test_zenkaku_indent_detected(sample):
    sample.joinpath("novel/ch01.md").write_text(
        "# 第1章 導入\n\n\u3000全角空白で始まる本文。これは警告対象である。\n"
        "〜〜〜テスト本文を十分な長さにするための行がここに入る。〜〜〜\n"
        "追加の行。さらに追加の行。十分な長さにする。\n"
        "追加の行。さらに追加の行。十分な長さにする。\n",
        encoding="utf-8",
    )
    code, out = run(sample, "--min-chars", "50")
    # 全角空白は警告（エラーではない）→ exit 0
    assert code == 0, out
    assert "全角空白" in out, out


def test_forbidden_word_detected(sample):
    sample.joinpath("novel/ch01.md").write_text(
        "# 第1章 導入\n\n美咲はスマホを取り出して为其の写真を撮った。\n"
        "〜〜〜テスト本文を十分な長さにするための行がここに入る。〜〜〜\n"
        "追加の行。さらに追加の行。十分な長さにする。\n"
        "追加の行。さらに追加の行。十分な長さにする。\n",
        encoding="utf-8",
    )
    code, out = run(sample, "--min-chars", "50")
    assert "禁止語彙" in out and "スマホ" in out, out


def test_chapter_filter(sample):
    code, out = run(sample, "--chapter", "2", "--min-chars", "50")
    assert code == 0, out
    assert "ch01" not in out, out


def test_strict_mode_fails_on_warnings(sample):
    sample.joinpath("novel/ch01.md").write_text(
        "# 第1章 導入\n\n\u3000全角空白のある本文。警告になる。\n"
        "〜〜〜テスト本文を十分な長さにするための行がここに入る。〜〜〜\n"
        "追加の行。さらに追加の行。十分な長さにする。\n"
        "追加の行。さらに追加の行。十分な長さにする。\n",
        encoding="utf-8",
    )
    code, out = run(sample, "--min-chars", "50", "--strict")
    assert code == 1
    assert "全角空白" in out
