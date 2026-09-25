#!/usr/bin/env python3
"""novel2agent-jp: プロジェクト雛形生成 (init.py)

planning workflow 冒頭の「ディレクトリ + 空 meta.toml + AGENTS.md + .gitignore」を安全に作る。
既存 meta.toml がある場合は上書きしない（エラーで停止）。

Usage:
  python init.py --project-dir <path>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

META_TEMPLATE = """[work]
title = "（作品タイトル）"
genre = "（ジャンル）"
status = "planning"                  # planning / writing / revision / complete
plan_status = "draft"                # draft / confirmed。企画承認は必ずユーザが行い confirmed へ（planning §7）

# chapters は plot TOML 作成後に追記する（validate.py が chapters[?].plot 必須を検査）。
# 例:
# [[chapters]]
# number = 1
# plot = "plot/plot-ch01.toml"
# novel = "novel/ch01.md"            # 未執筆の間は novel 行を省略
# status = "draft"
"""

PROPOSAL_TEMPLATE = """proposal_status: proposed

# 【作品タイトル（仮）】企画書

- ターゲット層:
- ジャンル:
- 想定プラットフォーム:
- 長さ（章数・文字数）:

## あらすじ

（300〜500字）

## テーマ・モチーフ

## 登場人物

| 名前 | 役割 | 一言 |
|------|------|------|

## 章構成

| 章 | タイトル | 概要 |
|----|---------|------|

## 感情曲線

| 章 | ピーク強度(%) | 支配的感情 | 曲線形状 |
|----|--------------|-----------|---------|
"""

AGENTS_TEMPLATE = """# AGENTS.md — 作品の憲法

<!--
本テンプレートの規則は必ず保持。作品固有の規則を追記して使う。
-->

## 必須規則（テンプレート既定・削除しない）

- 本文は `novel/chNN.md` にのみ書く。plot TOML・.context への書き戻しはしない
- **Markdown 段落は空白なし**: 段落頭に全角空白（U+3000）を入れない（編集経路で壊れる事故対策。check_prose.py が検出する）
- キャラ初出時に本文へふりがなを添える（例: 桜井美咲（さくらい みさき））。表記は character TOML の `name_ja` / `name_ruby` に合わせる
- 一人称・口調は character TOML の `[basic]` に従う
- 五感ローテーション: シーンごとに視覚以外の感覚を 2 つ以上
- 禁止語彙は worldbuilding の `[[constraints]] kind = "forbidden_words"` に従い、最初から使わない

## 作品固有の文体規則

（ここに追記）
"""

GITIGNORE_TEMPLATE = """.context/
"""

PRODUCTION_LOG_TEMPLATE = """# 制作ログ（追記専用）
#
# 企画・執筆・推敲で「既定の決定を変えた」「案を却下した」ときだけ書く。初回の決定は書かない。
# 新しいエントリは下に足す。過去のエントリは消さない。撤回も新しいエントリとして書く。
# スキーマ: schema/toml-schema.md §7。読むとき: validate.py --project-dir <project> --log
#
# [[log]]
# id = "log-001"          # log-NNN 連番・重複不可
# date = "2026-09-15"     # YYYY-MM-DD
# kind = "change"         # change / reject / note
# what = "一行で何をしたか"
# why = '''なぜ変えたか。却下の場合は、なぜ捨てたか'''
# affects = ["plot-ch01", "chara-001"]   # 章ID / キャラID / "proposal" / "agents"（0件可）
# by = "agent"            # agent / human
"""

PLOT_TEMPLATE = None  # 未使用: plot TOML は planning workflow の手順で個別に作る


def main() -> int:
    ap = argparse.ArgumentParser(description="novel2agent-jp プロジェクト雛形生成")
    ap.add_argument("--project-dir", required=True)
    args = ap.parse_args()
    project = Path(args.project_dir)

    meta_path = project / "meta.toml"
    if meta_path.exists():
        print(f"[ERROR] {meta_path} が既に存在する（上書きしません）")
        return 1

    for d in ("character", "worldbuilding", "plot", "novel", ".context"):
        (project / d).mkdir(parents=True, exist_ok=True)

    if not project.joinpath("proposal.md").exists():
        project.joinpath("proposal.md").write_text(PROPOSAL_TEMPLATE, encoding="utf-8")
    meta_path.write_text(META_TEMPLATE, encoding="utf-8")
    if not project.joinpath("AGENTS.md").exists():
        project.joinpath("AGENTS.md").write_text(AGENTS_TEMPLATE, encoding="utf-8")
    gi = project / ".gitignore"
    if gi.exists():
        content = gi.read_text(encoding="utf-8")
        if ".context/" not in content:
            gi.write_text(content.rstrip() + "\n.context/\n", encoding="utf-8")
    else:
        gi.write_text(GITIGNORE_TEMPLATE, encoding="utf-8")
    plog = project / "production-log.toml"
    if not plog.exists():
        plog.write_text(PRODUCTION_LOG_TEMPLATE, encoding="utf-8")

    print(f"[OK] プロジェクト雛形を生成: {project}")
    print("  next: proposal.md を書く → proposal_status: confirmed は必ずユーザが変える")
    print("        python scripts/validate.py --project-dir " + str(project) + "  で初回検証")
    print("        planning-workflow.md §0.5 参照")
    return 0


if __name__ == "__main__":
    sys.exit(main())
