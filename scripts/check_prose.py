#!/usr/bin/env python3
"""novel2agent-jp: 本文品質チェック (check_prose.py)

novel/chNN.md の機械検査。validate.py が TOML 構造を検証するのに対し、
本スクリプトは本文ファイルの存在と品質を検査する。

検査項目（最低限）:
  1. 本文存在: meta.toml の chapters[].novel が参照するファイルが、
     見出し以外の本文（しきい値以上の文字数・空行だけの本文でない）を持つか
  2. 全角空白段落頭: 段落頭に全角空白がある行の検出
     （エージェントの編集経路で壊れる事故対策。作品規則として禁止）
  3. 禁止語彙: worldbuilding [[constraints]] kind="forbidden_words" との照合
  4. 一人称: character [basic].first_person と本文の照合
     （本文中のセリフ一人称が、指定された一人称の他候補を頻出する場合に警告）
  5. 章見出し: meta の章タイトル（plot title）と本文見出しの照合

標準ライブラリのみで動作する（tomllib + re + pathlib）。

Usage:
  python check_prose.py --project-dir <path>                # 全章検査
  python check_prose.py --project-dir <path> --chapter 2    # 章指定
  python check_prose.py --project-dir <path> --min-chars 200
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

ERR = "[ERROR]"
WARN = "[WARN]"

# セリフに登場しやすい一人称候補（first_person 以外の候補が頻出する場合に警告）
FIRST_PERSON_CANDIDATES = ["私", "俺", "僕", "わたし", "うち", "あたし"]


def load_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def strip_headings_and_blanks(text: str) -> list[str]:
    """見出し行と空行を除いた本文行を返す。"""
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        lines.append(s)
    return lines


def prose_char_count(text: str) -> int:
    """見出しと空行を除いた本文文字数。"""
    return sum(len(line) for line in strip_headings_and_blanks(text))


def leading_zenkaku_lines(text: str) -> list[int]:
    """段落頭に全角空白（\\u3000）を含む行の行番号（1始まり）。"""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("\u3000"):
            out.append(i)
    return out


def find_forbidden_words(text: str, words: list[str]) -> list[str]:
    return [w for w in words if w and w in text]


def first_person_issues(text: str, expected: str | None) -> list[str]:
    """expected 以外の一人称候補が本文中に複数回出現したら報告（推定・警告止まり）。

    台詞中の他人や地の文の指訳に引っかかる偽陽性があるため、しきい値は
    「3 回以上・かつ expected が指定されている場合のみ」とする。
    """
    if not expected:
        return []
    issues = []
    for cand in FIRST_PERSON_CANDIDATES:
        if cand == expected or len(cand) <= 1 and cand in expected:
            continue
        # 期待値の部分文字列（"私" ⊂ "わたし" などは別表記として両方数える必要はないため除外条件は上の len チェックでカバー）
        n = text.count(cand)
        if n >= 3:
            issues.append(f"'{cand}' が {n} 回（指定一人称は '{expected}'）")
    return issues


def check_chapter(prose: str, meta_ch: dict, plot: dict | None,
                  forbidden: list[str], first_people: dict[str, str | None],
                  min_chars: int) -> tuple[list[str], list[str]]:
    errors, warnings = [], []

    # --- 1. 本文存在 ---
    n = prose_char_count(prose)
    if n == 0:
        errors.append(f"本文が空（見出し・空行以外の文字数 0）。保存事故の可能性 → 再保存・再確認のこと")
    elif n < min_chars:
        errors.append(f"本文文字数が不足: {n} 文字 < しきい値 {min_chars} 文字")

    # --- 2. 段落頭全角空白 ---
    zl = leading_zenkaku_lines(prose)
    if zl:
        warnings.append(
            f"段落頭に全角空白がある行: {zl[:10]}{'…' if len(zl) > 10 else ''} "
            f"（作品規則: Markdown 段落は空白なし。削除のこと）"
        )

    # --- 3. 禁止語彙 ---
    for w in find_forbidden_words(prose, forbidden):
        warnings.append(f"禁止語彙が本文に含まれる: '{w}'")

    # --- 4. 一人称 ---
    for msg in first_person_issues(prose, first_people.get("pov")):
        warnings.append(f"一人称の揺れ候補: {msg}")

    # --- 5. 章見出し ---
    title = meta_ch.get("title") or (plot or {}).get("title")
    head_lines = [l for l in prose.splitlines() if l.strip().startswith("#") or re.match(r"^\s*(第?\s*\d+\s*[章話])", l)]
    if title and head_lines:
        if all(title not in h for h in head_lines):
            warnings.append(f"章見出しに章タイトル '{title}' が含まれない: {head_lines[0][:40]}")

    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="novel2agent-jp 本文品質チェック")
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--chapter", type=int, help="章を限定する場合")
    ap.add_argument("--min-chars", type=int, default=100, help="見出し以外の最低本文文字数")
    ap.add_argument("--strict", action="store_true", help="警告でも exit 1")
    args = ap.parse_args()

    project = Path(args.project_dir)
    if not project.is_dir():
        print(f"{ERR} project-dir が存在しない: {project}")
        return 1

    meta_path = project / "meta.toml"
    if not meta_path.is_file():
        print(f"{ERR} meta.toml が存在しない: {meta_path}")
        return 1
    try:
        meta = load_toml(meta_path)
    except Exception as e:
        print(f"{ERR} meta.toml の読み込みに失敗: {e}")
        return 1

    # 禁止語彙の収集
    forbidden: list[str] = []
    for f in sorted((project / "worldbuilding").glob("*.toml")):
        try:
            w = load_toml(f)
        except Exception as e:
            print(f"{ERR} {f.name}: TOML 構文エラー: {e}")
            return 1
        for c in w.get("constraints", []):
            if isinstance(c, dict) and c.get("kind") == "forbidden_words":
                forbidden.extend(wd for wd in c.get("words", []) if isinstance(wd, str))

    # plot の章タイトル
    plots: dict[int, dict] = {}
    for f in sorted((project / "plot").glob("plot-ch*.toml")):
        try:
            p = load_toml(f)
        except Exception as e:
            print(f"{ERR} {f.name}: TOML 構文エラー: {e}")
            return 1
        if isinstance(p.get("chapter"), int):
            plots[p["chapter"]] = p

    # 一人称（キャラID → first_person）
    first_people: dict[str, str | None] = {}
    for f in sorted((project / "character").glob("*.toml")):
        try:
            c = load_toml(f)
        except Exception:
            continue
        cid = c.get("id")
        if isinstance(cid, str):
            first_people[cid] = ((c.get("basic") or {}).get("first_person") if isinstance(c.get("basic"), dict) else None)

    chapters = meta.get("chapters", [])
    if args.chapter is not None:
        chapters = [c for c in chapters if isinstance(c, dict) and c.get("number") == args.chapter]

    total_err, total_warn = 0, 0
    for mc in chapters:
        if not isinstance(mc, dict):
            continue
        num = mc.get("number")
        novel_rel = mc.get("novel")
        label = f"ch{num:02d}" if isinstance(num, int) else "?"
        if not novel_rel:
            print(f"{WARN} {label}: meta.toml に novel パス未指定（未執筆とみなして skip）")
            continue
        novel_path = project / novel_rel
        if not novel_path.is_file():
            print(f"{ERR} {label}: 本文ファイルが存在しない: {novel_rel}")
            total_err += 1
            continue
        prose = novel_path.read_text(encoding="utf-8")
        plot = plots.get(num)
        pov = (plot or {}).get("pov")
        errs, warns = check_chapter(prose, mc, plot, forbidden, {"pov": first_people.get(pov)}, args.min_chars)
        total_err += len(errs)
        total_warn += len(warns)
        print(f"\n== {label} ({novel_rel}) ==")
        for e in errs:
            print(f"{ERR} {e}")
        for w in warns:
            print(f"{WARN} {w}")
        if not errs and not warns:
            print("[OK] 検査項目すべて合格")

    print(f"\n本文チェック完了: エラー {total_err} 件 / 警告 {total_warn} 件")
    if total_err:
        return 1
    return 1 if (args.strict and total_warn) else 0


if __name__ == "__main__":
    sys.exit(main())
