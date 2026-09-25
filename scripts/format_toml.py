#!/usr/bin/env python3
"""novel2agent-jp: TOML リテラルの機械整形 (format_toml.py)

AI に「50文字くらいで改行して」と頼む運用は、修正指示のたびに崩れる。
判断を AI にさせず、スクリプトで直すのが正本。

対象: プロジェクト配下の全 TOML 内の複数行 ''' リテラル（キー不問）。
  1行リテラル（改行なし）は正規形のまま触らない。
やること:
  1. 先頭改行の強制: ``'''内容'''`` → ``'''\n内容\n'''``
     (TOML 仕様で開き直後の1改行は無視されるため、値の先頭は変わらない。
      末尾改行は値に ``\\n`` が1つ付く。schema の plot 例と同形になる)
  2. 1文1行: 。！？…＋閉じ括弧の後ろで割る。ただし全角10字以内の短文は孤立行にせず前後の文と同行に畳む
  3. 幅詰め: 半角換算80字相当（全角40字目安）超の行を、読点・開き括弧前で折る。
     行頭禁則（」、。、？！…）・行末禁則（「『（［）を避ける

\"...\" の1行もの（flaw / quirk 等の短い事実）は触らない。
\"...\" を ''' に変えると値に改行が混入するため、変換は人間が判断する。

標準ライブラリのみ (re + unicodedata + pathlib)。

Usage:
  python format_toml.py --project-dir <path>            # その場で直す
  python format_toml.py --project-dir <path> --check    # 直さず検査のみ（ hooks / CI 用。修正が必要なら exit 1）
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
import unicodedata
from pathlib import Path

# schema §0 と同じ閾値（validate.py の READABILITY_WIDTH と一致させる）
WIDTH = 80
MIN_BEFORE_BREAK = 40  # 折り返し前の断片がこれ未満なら無理に折らない
# 短文結合の閾値：表示幅20（全角10字）以下の文は単独行にせず前後の文と同行に畳む
SHORT_MERGE_WIDTH = 20

SENTENCE_RE = re.compile(r".+?(?:[。！？]+[」』）〉》】]*|[…―—]+[」』）〉》】]*|$)")
LITERAL_RE = re.compile(r"'''(.*?)'''", re.DOTALL)

BREAK_AFTER = set("、，, 　\t。！？…―—")
BREAK_BEFORE = set("「『（［〈《【")
# 文末判定：この正規表現に一致しない行は文の途中で折れた継続行 → 次行と結合する
SENT_END_RE = re.compile(r"[。！？…]+[」』）〉》】]*$")
LINE_HEAD_NG = set("」』）、。，．？！…―—ー・:;)]}）〉》】ぁぃぅぇぉっゃゅょァィゥェォッャュョ")
LINE_TAIL_NG = set("「『（［〈《【([:")


def display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)


def split_sentences(line: str) -> list[str]:
    """1論理行を文単位に割る。句読点なしの断片はそのまま1件。"""
    s = line.strip()
    if not s:
        return []
    parts = [m.group(0) for m in SENTENCE_RE.finditer(s) if m.group(0)]
    if not parts:
        return [s]
    # 最後の空マッチ掃除
    return [p for p in parts if p.strip()]


def wrap_sentence(s: str, width: int = WIDTH) -> list[str]:
    """1文を幅に収める。禁則を避け、無理な箇所はハードカット。"""
    if display_width(s) <= width:
        return [s]
    out: list[str] = []
    cur = ""
    cur_w = 0
    break_pos = -1  # cur 内の「ここで折ってよい」文字数
    break_w = 0
    i = 0
    chars = list(s)
    while i < len(chars):
        ch = chars[i]
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        w = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        cur += ch
        cur_w += w
        if ch in BREAK_AFTER or (nxt and nxt in BREAK_BEFORE):
            # 行末禁則文字で終わる折り方は除外
            if ch not in LINE_TAIL_NG:
                break_pos = len(cur)
                break_w = cur_w
        if cur_w > width:
            # ハードカット時の尻尾幅を先に見積もる（数文字の孤立行を作らないため）
            rest_w = display_width("".join(chars[i + 1:]))
            hard_tail_w = display_width(cur[-1:]) + rest_w
            if break_pos > 0 and (break_w >= MIN_BEFORE_BREAK or hard_tail_w <= SHORT_MERGE_WIDTH):
                head, tail = cur[:break_pos], cur[break_pos:]
                # 行頭禁則が次行頭に来るなら1字引き込む
                while tail and tail[0] in LINE_HEAD_NG and len(head) > 1:
                    tail = head[-1] + tail
                    head = head[:-1]
                out.append(head)
                cur, cur_w = tail, display_width(tail)
                break_pos = -1
                break_w = 0
            else:
                # ハードカット：尻尾が短文以下にならないよう切り位置を戻す
                rest = chars[i + 1:]
                rest_w = display_width("".join(rest))
                cut = len(cur) - 1
                while cut > 1 and display_width(cur[cut:]) + rest_w <= SHORT_MERGE_WIDTH:
                    cut -= 1
                while cut > 1 and (cur[cut - 1] in LINE_TAIL_NG):
                    cut -= 1
                head, tail = cur[:cut], cur[cut:]
                while tail and tail[0] in LINE_HEAD_NG and len(head) > 1:
                    tail = head[-1] + tail
                    head = head[:-1]
                out.append(head)
                cur, cur_w = tail, display_width(tail)
                break_pos = -1
                break_w = 0
        i += 1
    if cur:
        out.append(cur)
    return out


def group_sentences(sentences: list[str], width: int = WIDTH) -> list[str]:
    """文を1文1行にしつつ、短文（全角10字以下）は孤立行にせず前後の文と同行に畳む。

    結合するのは「次が短文」か「行が短文1件のみ（短い先頭＋次の文）」の場合だけ。
    長文＋長文は結合しない（1文1行・git diff 粒度を保つ）。結合後も width 以内。
    """
    lines: list[str] = []
    buf: list[str] = []
    buf_w = 0
    for sent in sentences:
        sw = display_width(sent)
        short_next = sw <= SHORT_MERGE_WIDTH
        short_head = len(buf) == 1 and display_width(buf[0]) <= SHORT_MERGE_WIDTH
        if buf and buf_w + sw <= width and (short_next or short_head):
            buf.append(sent)
            buf_w += sw
        else:
            if buf:
                lines.append("".join(buf))
            buf, buf_w = [sent], sw
    if buf:
        lines.append("".join(buf))
    return lines


def reflow_content(inner: str) -> str:
    """リテラル中身を行単位→文単位→短文結合→幅詰めで流し直す。"""
    raws = [r.strip() for r in inner.strip().replace("\r\n", "\n").split("\n") if r.strip()]
    # 継続行の結合：文末句読点で終わらない行は文の途中で折れた断片 → 次行と結合する
    joined: list[str] = []
    buf = ""
    for raw in raws:
        buf += raw
        if SENT_END_RE.search(buf):
            joined.append(buf)
            buf = ""
    if buf:
        joined.append(buf)
    sents: list[str] = []
    for line in joined:
        sents.extend(split_sentences(line))
    lines: list[str] = []
    for line in group_sentences(sents):
        lines.extend(wrap_sentence(line))
    return "\n".join(lines)


def normalize_match(m: re.Match) -> str:
    inner = m.group(1)
    if not inner.strip():
        return m.group(0)  # 空は触らない
    if "\n" not in inner:
        return m.group(0)  # 1行リテラルは触らない（短い事実は "..." 同様そのまま）
    body = reflow_content(inner)
    return "'''\n" + body + "\n'''"


def process_text(text: str) -> tuple[str, int]:
    """テキスト内の全リテラルを正規化。(新テキスト, 修正ブロック数)"""
    n = [0]

    def _sub(m: re.Match) -> str:
        new = normalize_match(m)
        if new != m.group(0):
            n[0] += 1
        return new

    return LITERAL_RE.sub(_sub, text), n[0]


def iter_toml_files(project: Path) -> list[Path]:
    files: list[Path] = []
    for sub in ("character", "worldbuilding", "plot"):
        d = project / sub
        if d.is_dir():
            files.extend(sorted(d.glob("*.toml")))
    for name in ("meta.toml", "production-log.toml"):
        p = project / name
        if p.is_file():
            files.append(p)
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description="novel2agent-jp TOML リテラル整形")
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--check", action="store_true", help="直さず検査のみ（修正が必要なら exit 1）")
    args = ap.parse_args()

    project = Path(args.project_dir)
    if not project.is_dir():
        print(f"[ERROR] project-dir が存在しない: {project}")
        return 1

    targets = iter_toml_files(project)
    if not targets:
        print("[OK] TOML がない（何もしない）")
        return 0

    need_fix: list[str] = []
    fixed = 0
    for path in targets:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[ERROR] {path.name}: 読み込み失敗: {e}")
            return 1
        new_text, n = process_text(text)
        if n == 0:
            continue
        # 整形後も TOML として読めることを確認（壊さない）
        try:
            tomllib.loads(new_text)
        except Exception as e:
            print(f"[ERROR] {path.name}: 整形結果が TOML 構文エラーになるため skip: {e}")
            return 1
        if args.check:
            need_fix.append(f"{path.name}（{n} 箇所）")
        else:
            path.write_text(new_text, encoding="utf-8")
            fixed += 1
            print(f"[FIXED] {path.name}（{n} 箇所）")

    if args.check:
        if need_fix:
            print("[NG] 整形が必要なファイル:")
            for line in need_fix:
                print(f"  - {line}")
            print("  → python scripts/format_toml.py --project-dir <project> で直すこと")
            return 1
        print(f"[OK] 全 {len(targets)} ファイル整形済み")
        return 0

    if fixed == 0:
        print(f"[OK] 全 {len(targets)} ファイル整形済み（変更なし）")
    else:
        print(f"[OK] {fixed} ファイル整形。validate.py で再確認すること")
    return 0


if __name__ == "__main__":
    sys.exit(main())
