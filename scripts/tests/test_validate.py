"""scripts/tests/test_validate.py — validate.py の受け入れテスト

fixtures:
  ok/          エラー0・警告0
  bad_id/      ファイル名=ID 不一致
  bad_version/ versions 章範囲重複
  bad_syntax/  構文エラー（検証続行）
"""
import shutil
import subprocess
import sys
import re
from pathlib import Path

import pytest

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "validate.py"
FIXTURES = HERE / "fixtures"
WORK = HERE / ".work"
PY = sys.executable


def run(project: Path, *extra):
    proc = subprocess.run(
        [PY, str(SCRIPT), "--project-dir", str(project), *extra],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, (proc.stdout + proc.stderr)


@pytest.fixture()
def ok_project():
    dst = WORK / "ok"
    shutil.copytree(FIXTURES / "ok", dst, dirs_exist_ok=True)
    yield dst
    shutil.rmtree(dst, ignore_errors=True)


def copy_case(name: str) -> Path:
    dst = WORK / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(FIXTURES / name, dst)
    return dst


@pytest.mark.parametrize("case", ["bad_id", "bad_version", "bad_syntax"])
def test_negative_cases_exit_1(case: str):
    p = copy_case(case)
    code, out = run(p)
    assert code == 1, out


def test_id_mismatch_detected():
    code, out = run(copy_case("bad_id"))
    assert "ファイル名=ID 不一致" in out


def test_version_overlap_detected():
    code, out = run(copy_case("bad_version"))
    assert "章範囲重複" in out


def test_syntax_error_reports_but_continues():
    code, out = run(copy_case("bad_syntax"))
    assert "構文エラー" in out
    assert "検証結果" in out  # 他ファイルの検証結果は出力されている


def test_proposed_leaves_warning_but_exits_0():
    p = copy_case("ok_proposed")
    code, out = run(p)
    assert code == 0, out
    assert "proposed 残留" in out          # established
    assert "summary_status = proposed" in out


def test_ok_project_passes(ok_project):
    code, out = run(ok_project)
    assert code == 0, out
    assert "[ERROR]" not in out
    assert "エラー 0 件 / 警告 0 件" in out


def test_index_outputs_ids(ok_project):
    code, out = run(ok_project, "--index")
    assert code == 0, out
    assert "chara-001" in out and "桜井美咲" in out
    assert "world-001" in out
    assert "plot-ch01" in out and "覚醒" in out


LOG_OK = """[[log]]
id = "log-001"
date = "2026-09-13"
kind = "reject"
what = "第3章の結末を父娘の和解にする案"
why = '''丸すぎて主題と矛盾するため却下'''
affects = ["plot-ch01", "chara-001"]
by = "human"
"""


def test_production_log_ok_and_view(ok_project):
    (ok_project / "production-log.toml").write_text(LOG_OK, encoding="utf-8")
    code, out = run(ok_project)
    assert code == 0, out
    assert "[ERROR]" not in out
    code, out = run(ok_project, "--log")
    assert code == 0, out
    assert "log-001" in out and "reject" in out and "却下" in out
    code, out = run(ok_project, "--log", "--affects", "plot-ch01")
    assert code == 0 and "log-001" in out
    code, out = run(ok_project, "--log", "--affects", "plot-ch99")
    assert code == 0 and "該当エントリなし" in out


def test_production_log_bad_kind_and_id_exit_1(ok_project):
    bad = LOG_OK.replace('kind = "reject"', 'kind = "oops"').replace('id = "log-001"', 'id = "log-1"')
    (ok_project / "production-log.toml").write_text(bad, encoding="utf-8")
    code, out = run(ok_project)
    assert code == 1, out
    assert "kind 不正" in out
    assert "id 形式不正" in out


def test_production_log_affects_typo_warns_only(ok_project):
    warn = LOG_OK.replace('"chara-001"', '"chara-999"')
    (ok_project / "production-log.toml").write_text(warn, encoding="utf-8")
    code, out = run(ok_project)
    assert code == 0, out
    assert "chara-999" in out  # 参照ミスは警告のみで exit 0


def test_character_role_enum_exit_1(ok_project):
    c = ok_project / "character" / "chara-001.toml"
    c.write_text(c.read_text(encoding="utf-8").replace('role = "protagonist"', 'role = "hero"'),
                 encoding="utf-8")
    code, out = run(ok_project)
    assert code == 1, out
    assert "role 不正" in out


def test_long_single_line_warns_but_exits_0(ok_project):
    # §0 可読性ルール: 全角50字 = 100字相当 > 80 で警告。エラーにしない
    plot = ok_project / "plot" / "plot-ch01.toml"
    long_summary = "あ" * 50 + "。"
    plot.write_text(
        plot.read_text(encoding="utf-8").replace(
            'summary = "美咲が道端で魔法に覚醒する。"', f'summary = "{long_summary}"'
        ),
        encoding="utf-8",
    )
    code, out = run(ok_project)
    assert code == 0, out
    assert "80字相当超" in out
    assert "summary" in out


REORDERED_MULTILINE_PLOT = """id = "plot-ch01"
summary = '''
美咲が道端で魔法に覚醒する。
帰り道、空が赤かった。
'''
summary_status = "confirmed"
chapter = 1
title = "覚醒"
pov = "chara-001"

[[scenes]]
title = "帰り道"
location = "駅前商店街"
time = "夕方"
pov = "chara-001"
characters = ["chara-001", "chara-002"]
content = '''
太郎の机の写真が視界に入る。
美咲は足を止める。
'''

[[foreshadowing]]
id = "fs-001"
content = "太郎の机の古びた写真"
resolve_chapter = 3
"""


def test_new_key_order_and_multiline_pass(ok_project):
    # §3 推奨順 + 複数行リテラル: 警告なし・エラーなし（順序は機械の動作に影響しない）
    (ok_project / "plot" / "plot-ch01.toml").write_text(
        REORDERED_MULTILINE_PLOT, encoding="utf-8"
    )
    code, out = run(ok_project)
    assert code == 0, out
    assert "[ERROR]" not in out
    assert "80字相当超" not in out


def test_filename_suffix_passes(ok_project):
    # §0: {ID}-サフィックス名は exit 0（表示専用。ID が正本）
    (ok_project / "plot" / "plot-ch01.toml").rename(
        ok_project / "plot" / "plot-ch01-覚醒.toml"
    )
    (ok_project / "character" / "chara-001.toml").rename(
        ok_project / "character" / "chara-001-美咲.toml"
    )
    meta = ok_project / "meta.toml"
    meta.write_text(
        meta.read_text(encoding="utf-8").replace(
            'plot = "plot/plot-ch01.toml"', 'plot = "plot/plot-ch01-覚醒.toml"'
        ),
        encoding="utf-8",
    )
    code, out = run(ok_project)
    assert code == 0, out
    assert "[ERROR]" not in out
    assert "サフィックス" not in out  # 体裁警告もなし


def test_filename_suffix_prefix_mismatch_exit_1(ok_project):
    # 先頭 ID と中身の id が違えばエラー（サフィックス付きでも検出）
    (ok_project / "character" / "chara-001.toml").rename(
        ok_project / "character" / "chara-001-美咲.toml"
    )
    c = ok_project / "character" / "chara-001-美咲.toml"
    c.write_text(
        c.read_text(encoding="utf-8").replace('id = "chara-001"', 'id = "chara-002"'),
        encoding="utf-8",
    )
    code, out = run(ok_project)
    assert code == 1, out
    assert "ファイル名=ID 不一致" in out


def test_filename_suffix_chapter_check_with_suffix(ok_project):
    # plot 章番号照合はサフィックスを無視する（一致なら警告なし、不一致なら警告）
    (ok_project / "plot" / "plot-ch01.toml").rename(
        ok_project / "plot" / "plot-ch01-覚醒.toml"
    )
    meta = ok_project / "meta.toml"
    meta.write_text(
        meta.read_text(encoding="utf-8").replace(
            'plot = "plot/plot-ch01.toml"', 'plot = "plot/plot-ch01-覚醒.toml"'
        ),
        encoding="utf-8",
    )
    code, out = run(ok_project)
    assert code == 0, out
    assert "番号が一致しない" not in out
    plot = ok_project / "plot" / "plot-ch01-覚醒.toml"
    plot.write_text(
        plot.read_text(encoding="utf-8").replace("chapter = 1", "chapter = 2"),
        encoding="utf-8",
    )
    code, out = run(ok_project)
    assert code == 0, out
    assert "番号が一致しない" in out


def _report():
    sys.path.insert(0, str(HERE.parent))
    import validate as v

    return v, v.Report()


def test_suffix_forbidden_chars_are_error():
    v, r = _report()
    v.check_id("chara-001-美*咲", {"id": "chara-001"}, Path("chara-001-美咲.toml"), r)
    assert any("使用禁止文字" in e for e in r.errors)


def test_suffix_space_and_length_warn_only():
    v, r = _report()
    v.check_id("chara-001-美 咲", {"id": "chara-001"}, Path("x.toml"), r)
    assert not r.errors
    assert any("スペース" in w for w in r.warnings)
    r2 = v.Report()
    v.check_id("chara-001-" + "あ" * 20, {"id": "chara-001"}, Path("x.toml"), r2)
    assert not r2.errors
    assert any("長い" in w for w in r2.warnings)


def _with_deep_keys(ok_project, screen_time, keys=("flaw", "quirk")):
    # root キーは先頭テーブルより前に差し込む（末尾追記は [[versions]] 要素に入る）
    c = ok_project / "character" / "chara-001.toml"
    text = c.read_text(encoding="utf-8")
    root_keys = [k for k in keys if k != "false_belief"]
    inject = "".join(f'{k} = "深み-{k}"\n' for k in root_keys)
    assert "\n[basic]\n" in text
    text = text.replace("\n[basic]\n", "\n" + inject + "[basic]\n", 1)
    if "false_belief" in keys:
        text += '\n[motivation]\nfalse_belief = "深み-false_belief"\n'
    text += f'\n[design]\nscreen_time = "{screen_time}"\n'
    c.write_text(text, encoding="utf-8")


def test_minor_with_deep_keys_warns(ok_project):
    # §1 適用範囲：minor の物語装置キーは警告（exit 0 のまま）
    _with_deep_keys(ok_project, "minor")
    code, out = run(ok_project)
    assert code == 0, out
    assert "screen_time=minor" in out


def test_support_with_two_deep_keys_warns(ok_project):
    _with_deep_keys(ok_project, "support", ("flaw", "quirk"))
    code, out = run(ok_project)
    assert code == 0, out
    assert "screen_time=support" in out


def test_lead_with_deep_keys_no_scope_warning(ok_project):
    _with_deep_keys(ok_project, "lead", ("flaw", "quirk", "heat", "false_belief"))
    code, out = run(ok_project)
    assert code == 0, out
    assert "screen_time=lead" not in out
    assert "screen_time=support" not in out
    assert "物語装置キー" not in out


def test_support_with_one_deep_key_ok(ok_project):
    _with_deep_keys(ok_project, "support", ("quirk",))
    code, out = run(ok_project)
    assert code == 0, out
    assert "物語装置キー" not in out


def _set_plan(ok_project, work_status, plan_line):
    # plan_status 行の差し替え・削除ヘルパ（§5-18 企画承認ゲート用）
    meta = ok_project / "meta.toml"
    text = meta.read_text(encoding="utf-8")
    text = re.sub(r'^status = "writing"$', f'status = "{work_status}"', text, count=1, flags=re.M)
    text = re.sub(r'^plan_status = "confirmed"\n', "", text, count=1, flags=re.M)
    if plan_line is not None:
        text = text.replace("[work]\n", "[work]\n" + plan_line + "\n", 1)
    meta.write_text(text, encoding="utf-8")


def test_plan_gate_writing_without_confirmed_exit_1(ok_project):
    # writing で plan_status 未記入 → エラー（企画未承認の執筆を機械的に止める）
    _set_plan(ok_project, "writing", None)
    code, out = run(ok_project)
    assert code == 1, out
    assert "企画未承認" in out


def test_plan_gate_writing_draft_exit_1(ok_project):
    _set_plan(ok_project, "writing", 'plan_status = "draft"')
    code, out = run(ok_project)
    assert code == 1, out
    assert "企画未承認" in out


def test_plan_gate_writing_confirmed_passes(ok_project):
    code, out = run(ok_project)
    assert code == 0, out
    assert "企画未承認" not in out


def test_plan_gate_planning_without_plan_key_passes(ok_project):
    # planning 中の未記入は許容（旧プロジェクト移行のため）
    _set_plan(ok_project, "planning", None)
    code, out = run(ok_project)
    assert code == 0, out
    assert "企画未承認" not in out


def test_plan_gate_invalid_value_exit_1(ok_project):
    _set_plan(ok_project, "planning", 'plan_status = "ok"')
    code, out = run(ok_project)
    assert code == 1, out
    assert "plan_status 不正" in out
