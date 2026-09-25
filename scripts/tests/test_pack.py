"""scripts/tests/test_pack.py — pack.py の受け入れテスト (schema §6.6)

- versions の重複・逆転解決が仕様通り
- 未回収伏線の抽出漏れなし（resolved_at 有無の境界）
- budget 制御（6.3 削り順）
- established ロールアップで proposed が残る
- --check 鮮度チェック
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "pack.py"
SAMPLE_GEN = HERE / "sample_project.py"
WORK = HERE / ".work"
PY = sys.executable


@pytest.fixture(scope="module")
def sample():
    dst = WORK / "pack_sample"
    shutil.rmtree(dst, ignore_errors=True)
    proc = subprocess.run([PY, str(SAMPLE_GEN), str(dst)],
                          capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return dst


def run(pack_sample: Path, *extra):
    proc = subprocess.run([PY, str(SCRIPT), "--project-dir", str(pack_sample), *extra],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout + proc.stderr


def ctx_of(sample: Path, n: int) -> str:
    return (sample / ".context" / f"ch{n:02d}.md").read_text(encoding="utf-8")


def test_ch03_versions_resolved(sample):
    code, out = run(sample, "--chapter", "3")
    assert code == 0, out
    ctx = ctx_of(sample, 3)
    # chara-001 は 3章から age=19 (versions)
    m = re.search(r"### chara-001:.*?年齢: (\d+)", ctx, re.S)
    assert m and m.group(1) == "19", "chara-001 の 3章時点の年齢は 19"


def test_unresolved_foreshadowing_included(sample):
    code, out = run(sample, "--chapter", "3")
    assert code == 0, out
    ctx = ctx_of(sample, 3)
    assert "未回収伏線" in ctx
    assert "古い日記" in ctx            # fs-001 (resolve_chapter=3, 未回収)
    assert "203号室へは戻るな" in ctx   # fs-002


def test_resolved_foreshadowing_excluded(sample):
    # fs-001 を回収済みにした複製で確認
    dst = WORK / "pack_resolved"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(sample, dst)
    plot = dst / "plot" / "plot-ch01.toml"
    plot.write_text(plot.read_text(encoding="utf-8")
                    .replace("resolve_chapter = 3\n", "resolve_chapter = 3\nresolved_at = 3\n"),
                    encoding="utf-8")
    code, out = run(dst, "--chapter", "3")
    assert code == 0, out
    ctx = ctx_of(dst, 3)
    assert "古い日記" not in ctx  # resolved_at 付きは pack に出ない


def test_established_recent_full_and_proposed_kept(sample):
    code, out = run(sample, "--chapter", "3")
    assert code == 0, out
    ctx = ctx_of(sample, 3)
    # 直近 (2章) の proposed は全件・【未確定】マーク付きで残る
    assert "【未確定】2章: 老婦人は美咲の祖母の名を口にした" in ctx
    # confirmed 1章・2章は出る
    assert "美咲が臼井市に引っ越した" in ctx
    assert "鏡が一瞬曇った" in ctx


def test_established_rollup_for_old_chapters(sample):
    # 1章を 3章から 3章以上前に見せるには章番号を操作するのが確実。
    # 4章用コンテキストだと 1章は N-3 以前 → ロールアップ表記になる
    dst = WORK / "pack_rollup"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(sample, dst)
    (dst / "plot" / "plot-ch04.toml").write_text(
        'id = "plot-ch04"\nchapter = 4\ntitle = "4章" \n'
        '[[scenes]]\ntitle = "t"\nlocation = "l"\npov = "chara-001"\n'
        'characters = ["chara-001"]\ncontent = "c"\n', encoding="utf-8")
    meta = dst / "meta.toml"
    meta.write_text(meta.read_text(encoding="utf-8").replace(
        'status = "draft"\n',
        'status = "draft"\n\n[[chapters]]\nnumber = 4\nplot = "plot/plot-ch04.toml"\nstatus = "draft"\n',
        1), encoding="utf-8")
    code, out = run(dst, "--chapter", "4")
    assert code == 0, out
    ctx = ctx_of(dst, 4)
    assert "1章（ロールアップ）: 美咲が臼井市に引っ越した" in ctx
    # 2章は直近2章分（N-2=2）なので全件のまま
    assert "鏡が一瞬曇った" in ctx


def test_budget_trims_last_chapter_tail(sample):
    # 全パック約794字 → budget 700 では本文末尾を削り、なお超過なら1章 summary が落ちる
    code, out = run(sample, "--chapter", "3", "--budget", "700")
    assert code == 0, out
    ctx = ctx_of(sample, 3)
    # priority 1〜4 は全員残る（メタ・キャラ・制約・伏線・established）
    assert "禁止語彙" in ctx
    assert "未回収伏線" in ctx
    assert "古い日記" in ctx
    assert "established" in ctx
    # 直前章本文は末尾から削られている
    assert "budget 制限により以下省略" in ctx


def test_budget_trims_summaries_before_higher_priority(sample):
    # budget 500 → 本文→要約→established→制約 の順で落ち、伏線は常に残る
    code, out = run(sample, "--chapter", "3", "--budget", "500")
    assert code == 0, out
    ctx = ctx_of(sample, 3)
    assert "禁止語彙" not in ctx   # 制約（priority 枠で最後に落とれる枠）は落ちる
    assert "古い日記" in ctx and "203号室" in ctx  # 伏線は絶対残る
    assert "年齢: 19" in ctx       # 対象章メタ・キャラは必ず残る


def test_freshness_check_stale(sample):
    # pack 実行 → 原典を touch → --check が警告する
    code, out = run(sample, "--chapter", "3")
    assert code == 0, out
    novel2 = sample / "novel" / "ch02.md"
    old = novel2.read_text(encoding="utf-8")
    novel2.write_text(old + "\n（推敲で1行追加）\n", encoding="utf-8")
    proc = subprocess.run([PY, str(SCRIPT), "--project-dir", str(sample), "--chapter", "3", "--check"],
                          capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "再生成" in proc.stdout


LOG_TOML = """[[log]]
id = "log-001"
date = "2026-09-10"
kind = "reject"
what = "第3章で美咲を覚醒させない案"
why = "弱すぎる"
affects = ["plot-ch03"]
by = "human"

[[log]]
id = "log-002"
date = "2026-09-11"
kind = "note"
what = "会話のトーンを硬めに統一する"
why = "地の文との温度差を消す"
affects = []
by = "agent"
"""


def test_production_log_included_in_pack(sample):
    dst = WORK / "pack_log"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(sample, dst)
    (dst / "production-log.toml").write_text(LOG_TOML, encoding="utf-8")
    code, out = run(dst, "--chapter", "3")
    assert code == 0, out
    ctx = ctx_of(dst, 3)
    assert "制作ログ" in ctx
    assert "- [2026-09-10][reject] 第3章で美咲を覚醒させない案 — 弱すぎる" in ctx
    assert "会話のトーンを硬めに統一する" in ctx  # 直近10件枠


def test_production_log_excluded_when_unrelated_and_old(sample):
    # 11件以上前の非関連エントリは載らない（直近10件 + 対象章関連のみ）
    dst = WORK / "pack_log_old"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(sample, dst)
    entries = ['[[log]]\nid = "log-%03d"\ndate = "2026-08-%02d"\nkind = "note"\n'
               'what = "古いメモ%02d"\nwhy = "w"\naffects = []\nby = "agent"\n'
               % (i, (i % 28) + 1, i) for i in range(1, 13)]
    entries.append('[[log]]\nid = "log-013"\ndate = "2026-09-12"\nkind = "change"\n'
                   'what = "第3章の視点を太郎に変更"\nwhy = "緊張を作る"\naffects = ["plot-ch03"]\nby = "human"\n')
    (dst / "production-log.toml").write_text("\n".join(entries), encoding="utf-8")
    code, out = run(dst, "--chapter", "3")
    assert code == 0, out
    ctx = ctx_of(dst, 3)
    assert "古いメモ01" not in ctx            # 直近10件の外・非関連 → 載らない
    assert "古いメモ04" in ctx                # 直近10件の境界内 → 載る
    assert "第3章の視点を太郎に変更" in ctx   # 対象章関連は全件載る


def test_versions_appearance_key_reflected(sample):
    # versions の [appearance] 系キー（outfit 等）は該当章のパックに反映される
    dst = WORK / "pack_ver_app"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(sample, dst)
    c = dst / "character" / "chara-002.toml"
    c.write_text(c.read_text(encoding="utf-8") + '\n[[versions]]\nfrom_chapter = 1\noutfit = "黒い外套"\n',
                 encoding="utf-8")
    code, out = run(dst, "--chapter", "3")
    assert code == 0, out
    ctx = ctx_of(dst, 3)
    assert "黒い外套" in ctx


def test_motivation_and_second_person_rendered(sample):
    # second_person / fears / catchphrase / habits がパックに出力される
    dst = WORK / "pack_disp"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(sample, dst)
    c = dst / "character" / "chara-001.toml"
    t = c.read_text(encoding="utf-8")
    t = t.replace('speech_style = "丁寧語"', 'speech_style = "丁寧語"\nsecond_person = "あなた"')
    t += ('\n[motivation]\nfears = "置いていかれること"\n'
          'catchphrase = "……そうですか"\nhabits = "袖口を直す"\n')
    c.write_text(t, encoding="utf-8")
    code, out = run(dst, "--chapter", "3")
    assert code == 0, out
    ctx = ctx_of(dst, 3)
    assert "二人称: あなた" in ctx
    assert "- 恐れ: 置いていかれること" in ctx
    assert "- 決め台詞: ……そうですか" in ctx
    assert "- 癖: 袖口を直す" in ctx


def test_multiline_summary_and_reordered_keys_pack_ok(sample):
    # §0 可読性ルール形（新順序＋複数行 summary）でも pack が通り、要約文が載る
    dst = WORK / "pack_reordered"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(sample, dst)
    (dst / "plot" / "plot-ch01.toml").write_text(
        'id = "plot-ch01"\n'
        "summary = '''\n"
        "美咲が臼井市に引っ越してくる。\n"
        "駅前で黒猫とすれ違う。\n"
        "'''\n"
        'summary_status = "confirmed"\n'
        "chapter = 1\n"
        'title = "導入"\n'
        'pov = "chara-001"\n'
        "\n[[scenes]]\n"
        'title = "引っ越し"\n'
        'location = "臼井駅"\n'
        'pov = "chara-001"\n'
        'characters = ["chara-001", "chara-002"]\n'
        "content = '''\n"
        "荷物の中から古い日記帳が出てくる。\n"
        "'''\n"
        "\n[[established]]\n"
        'content = "美咲が臼井市に引っ越した"\n'
        'status = "confirmed"\n'
        "\n[[foreshadowing]]\n"
        'id = "fs-001"\n'
        'content = "荷物から出た古い日記"\n'
        "resolve_chapter = 3\n",
        encoding="utf-8",
    )
    code, out = run(dst, "--chapter", "3")
    assert code == 0, out
    ctx = ctx_of(dst, 3)
    assert "美咲が臼井市に引っ越してくる" in ctx
    assert "駅前で黒猫とすれ違う" in ctx


def _deep_pack_sample(sample):
    # 両キャラに物語装置キー4件を付与した複製（schema §1 の深さ制御の検証用）
    dst = WORK / "pack_depth"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(sample, dst)
    for cid in ("chara-001", "chara-002"):
        c = dst / "character" / f"{cid}.toml"
        text = c.read_text(encoding="utf-8")
        # root キーは先頭テーブルより前に差し込む（末尾追記は [[versions]] 要素に入る）
        inject = (
            f'flaw = "深み-{cid}-flaw"\nquirk = "深み-{cid}-quirk"\n'
            f'heat = "深み-{cid}-heat"\n'
        )
        assert "\n[basic]\n" in text
        text = text.replace("\n[basic]\n", "\n" + inject + "[basic]\n", 1)
        text += f'\n[motivation]\nfalse_belief = "深み-{cid}-fb"\n'
        c.write_text(text, encoding="utf-8")
    return dst


def _section(ctx: str, cid: str) -> str:
    for part in re.split(r"^### ", ctx, flags=re.M):
        if part.startswith(f"{cid}:"):
            return part
    return ""


def test_depth_full_for_pov_and_first_appearance(sample):
    # ch1: chara-001 は視点＋初出、chara-002 は初出 → 両方 full
    dst = _deep_pack_sample(sample)
    code, out = run(dst, "--chapter", "1")
    assert code == 0, out
    ctx = ctx_of(dst, 1)
    assert "- 欠点: 深み-chara-001-flaw" in _section(ctx, "chara-001")
    assert "- 欠点: 深み-chara-002-flaw" in _section(ctx, "chara-002")
    assert "誤った信念" in _section(ctx, "chara-002")


def test_depth_slim_for_non_pov_repeat(sample):
    # ch3: 視点 chara-002 → full。chara-001 は初出1・非視点 → slim
    dst = _deep_pack_sample(sample)
    code, out = run(dst, "--chapter", "3")
    assert code == 0, out
    ctx = ctx_of(dst, 3)
    s2 = _section(ctx, "chara-002")
    assert "- 欠点: 深み-chara-002-flaw" in s2
    s1 = _section(ctx, "chara-001")
    assert "- 欠点:" not in s1
    assert "ズレ" not in s1
    assert "必死になる対象" not in s1
    assert "誤った信念" not in s1
    # 演技情報は slim でも残る
    assert "丁寧語" in s1
    assert "一人称: 私" in s1
