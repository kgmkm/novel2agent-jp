"""scripts/tests/test_format_toml.py — format_toml.py の受け入れテスト

- 複数行リテラルの先頭・末尾改行を強制する（ユーザ報告の core_wound 形）
- 1行リテラルは触らない（短い事実は正規形のまま）
- 長文は1文1行＋80字相当で折る。冪等・--check・TOML 有効性を担保する
"""
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "format_toml.py"
PY = sys.executable


def run(project: Path, *extra):
    proc = subprocess.run(
        [PY, str(SCRIPT), "--project-dir", str(project), *extra],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, (proc.stdout + proc.stderr)


def make_project(root: Path, files: dict[str, str]) -> Path:
    if root.exists():
        import shutil
        shutil.rmtree(root)
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


WORK = HERE / ".work" / "fmt"


def test_leading_trailing_newline():
    p = make_project(WORK / "case1", {
        "character/chara-001.toml": (
            'id = "chara-001"\n'
            "[motivation]\n"
            "core_wound = '''自宅の開発室で過労死した。\n"
            "隣室に音が漏れない電気マッサージ器の仕様を詰めている最中だった。'''\n"
        ),
    })
    code, out = run(p)
    assert code == 0, out
    text = (p / "character" / "chara-001.toml").read_text(encoding="utf-8")
    assert "core_wound = '''\n自宅の開発室で過労死した。\n" in text
    assert text.rstrip().endswith("'''")
    # 値は末尾 \n が1つ付く以外変わらない
    v = tomllib.loads(text)["motivation"]["core_wound"]
    assert v == "自宅の開発室で過労死した。\n隣室に音が漏れない電気マッサージ器の仕様を詰めている最中だった。\n"


def test_single_line_literal_untouched():
    src = 'id = "plot-ch01"\ncontent = \'\'\'太郎の机の写真が視界に入る——\'\'\'\n'
    p = make_project(WORK / "case2", {"plot/plot-ch01.toml": src})
    code, out = run(p)
    assert code == 0, out
    assert (p / "plot" / "plot-ch01.toml").read_text(encoding="utf-8") == src


def test_long_line_wrapped_and_idempotent():
    long_sent = "美咲は窓の外を見ていた、雨粒がガラスを伝い、遠くで雷が鳴っている、その音を聞きながら彼女は昨日の出来事を思い出していた。"
    p = make_project(WORK / "case3", {
        "plot/plot-ch01.toml": "id = \"plot-ch01\"\nsummary = '''" + long_sent + "\nとなりの部屋の笑い声が聞こえた。'''\n",
    })
    code, out = run(p)
    assert code == 0, out
    text = (p / "plot" / "plot-ch01.toml").read_text(encoding="utf-8")
    import unicodedata
    dw = lambda s: sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)
    for line in tomllib.loads(text)["summary"].splitlines():
        assert dw(line) <= 80, line
    # 冪等
    code, out = run(p)
    assert "変更なし" in out, out
    code, out = run(p, "--check")
    assert code == 0, out


def test_check_reports_but_does_not_write():
    src = 'id = "chara-001"\ncore_wound = \'\'\'あ。\nい。\'\'\'\n'
    p = make_project(WORK / "case4", {"character/chara-001.toml": src})
    code, out = run(p, "--check")
    assert code == 1, out
    assert (p / "character" / "chara-001.toml").read_text(encoding="utf-8") == src


def test_validate_warns_on_missing_newline():
    src = 'id = "chara-001"\ncore_wound = \'\'\'あ。\nい。\'\'\'\n'
    p = make_project(WORK / "case5", {"character/chara-001.toml": src})
    proc = subprocess.run(
        [PY, str(HERE.parent / "validate.py"), "--project-dir", str(p)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = proc.stdout + proc.stderr
    assert "先頭・末尾に改行がない" in out, out


def test_short_sentences_merge():
    # 全角10字以内の短文は孤立行にならず前後の文と同行に畳まれる
    p = make_project(WORK / "case6", {
        "plot/plot-ch01.toml": (
            "id = \"plot-ch01\"\ncontent = '''\n"
            "匠はまだ何も気づいていない。\n"
            "落差をつける。\n"
            "本筋の種。\n"
            "'''\n"
        ),
    })
    code, out = run(p)
    assert code == 0, out
    v = tomllib.loads((p / "plot" / "plot-ch01.toml").read_text(encoding="utf-8"))["content"]
    assert v == "匠はまだ何も気づいていない。落差をつける。本筋の種。\n", repr(v)
    # 冪等
    code, out = run(p)
    assert "変更なし" in out, out


def test_long_sentences_stay_split():
    # 長文＋長文は結合しない（1文1行を保つ）
    p = make_project(WORK / "case7", {
        "plot/plot-ch01.toml": (
            "id = \"plot-ch01\"\ncontent = '''\n"
            "軟化したロクサーヌの顔を見て、ノエミアが自分にもと要求する。\n"
            "動機は酒場で見た錬成への興味だった。\n"
            "'''\n"
        ),
    })
    code, out = run(p)
    assert code == 0, out
    v = tomllib.loads((p / "plot" / "plot-ch01.toml").read_text(encoding="utf-8"))["content"]
    assert v == ("軟化したロクサーヌの顔を見て、ノエミアが自分にもと要求する。\n"
                 "動機は酒場で見た錬成への興味だった。\n"), repr(v)


def test_continuation_lines_rejoin():
    # 文末句読点なしの行は次行と同文 → 結合してから折り直す（単語途中分割＋数文字孤立行を作らない）
    p = make_project(WORK / "case8", {
        "plot/plot-ch01.toml": (
            "id = \"plot-ch01\"\ncontent = '''\n"
            "スケベジジイ、流れるような手つきでローションを手に塗りメルルの乳を揉み感触を確か\n"
            "める。\n"
            "'''\n"
        ),
    })
    code, out = run(p)
    assert code == 0, out
    v = tomllib.loads((p / "plot" / "plot-ch01.toml").read_text(encoding="utf-8"))["content"]
    # 尻尾切り回避のため読点で折る（短い頭＋長い尻尾。単語途中分割よりまし）
    assert v == ("スケベジジイ、\n"
                 "流れるような手つきでローションを手に塗りメルルの乳を揉み感触を確かめる。\n"), repr(v)
    assert "確か\nめる" not in v  # 単語途中分割なし
    # 冪等
    code, out = run(p)
    assert "変更なし" in out, out
