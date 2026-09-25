#!/usr/bin/env python3
"""novel2agent-jp: TOML 設定の機械検証 (P1)

スキーマ: schema/toml-schema.md
方針: 値を推測で埋めない。構造エラーは exit 1、警告系は明示出力して継続。

Usage:
  python validate.py --project-dir <path>
  python validate.py --project-dir <path> --index          # ID 一覧のみ出力
  python validate.py --project-dir <path> --log            # 制作ログの表出力
  python validate.py --project-dir <path> --log --affects plot-ch03
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
import unicodedata
from pathlib import Path

ID_PREFIXES = {"chara", "plot", "fs", "world"}
VALID_WORK_STATUS = {"planning", "writing", "revision", "complete"}
VALID_CHAPTER_STATUS = {"draft", "written", "revised", "confirmed"}
VALID_SUMMARY_STATUS = {"proposed", "confirmed"}
VALID_CONSTRAINT_KINDS = {"forbidden_words", "unknown_to", "era"}
VALID_ROLES = {"protagonist", "antagonist", "support"}
VALID_SCREEN_TIME = {"lead", "support", "minor"}
VALID_LOG_KINDS = {"change", "reject", "note"}
VALID_LOG_BY = {"agent", "human"}
LOG_ID_RE = re.compile(r"^log-\d{3}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

ERR = "[ERROR]"
WARN = "[WARN]"

# §0 可読性ルール：1行は全角40字（半角80字相当）目安
READABILITY_WIDTH = 80

# §0 ファイル名サフィックスで使用禁止の文字（Windows/macOS 共通で作れない・壊れるもの）
FORBIDDEN_FILENAME_CHARS = set('\\/:*?"<>|')

LITERAL_RE = re.compile(r"'''(.*?)'''", re.DOTALL)


def check_literal_style(path, r: Report) -> None:
    """''' リテラルの先頭・末尾改行を警告する（スキーマ §5-19。エラーにしない）。

    tomllib は整形済み値しか見ないため原文テキストで検査する。
    直し方は format_toml.py（references/toml-formatting.md）。
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return
    for m in LITERAL_RE.finditer(text):
        if not m.group(1).strip():
            continue
        if "\n" not in m.group(1):
            continue  # 1行リテラルは正規形（短い事実はそのまま書く）
        if not m.group(1).startswith("\n") or not m.group(1).endswith("\n"):
            r.warn(path, "''' リテラルの先頭・末尾に改行がない"
                         " → scripts/format_toml.py --project-dir <project> で直すこと（schema §0-3）")
            return


def display_width(text: str) -> int:
    """半角換算の表示幅。全角（W/F）は2、それ以外は1で数える。"""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)


def check_readability(path, label: str, value: object, r: Report) -> None:
    """plot 長文の1行超過を警告する（スキーマ §5-16。エラーにしない）。"""
    if not isinstance(value, str) or not value.strip():
        return
    for line in value.splitlines():
        if display_width(line) > READABILITY_WIDTH:
            head = line.strip()[:30]
            r.warn(path, f"{label}: 1行が80字相当超（{display_width(line)}字相当・「{head}…」）"
                         f"→ §0可読性ルール（1文1行・40字目安）で改行すること")
            return


# ---------------------------------------------------------------- ローダ

def load_all(project: Path) -> tuple[dict[Path, dict], list[tuple[Path, str]]]:
    files: dict[Path, dict] = {}
    parse_errors: list[tuple[Path, str]] = []
    paths: list[Path] = []
    for sub in ("character", "worldbuilding", "plot"):
        d = project / sub
        if d.is_dir():
            paths.extend(sorted(d.glob("*.toml")))
    meta = project / "meta.toml"
    if meta.is_file():
        paths.append(meta)
    for f in paths:
        try:
            files[f] = tomllib.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            parse_errors.append((f, str(e)))
    return files, parse_errors


def by_prefix(files: dict[Path, dict], prefix: str) -> list[tuple[Path, dict]]:
    return [(f, d) for f, d in sorted(files.items())
            if f.stem.split("-")[0] == prefix or (prefix == "plot" and f.stem.startswith("plot-ch"))]


# ---------------------------------------------------------------- チェック

class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.proposed_warnings: list[str] = []  # 未確定設定（proposed）系の警告

    def error(self, path, msg):
        self.errors.append(f"{ERR} {path.name}: {msg}")

    def warn(self, path, msg):
        self.warnings.append(f"{WARN} {path.name}: {msg}")


def type_ok(v, typ) -> bool:
    if typ is int:
        return isinstance(v, int) and not isinstance(v, bool)
    return isinstance(v, typ)


def check_keys(data: dict, required: dict[str, type], path, label: str, r: Report) -> None:
    missing = [k for k in required if k not in data]
    if missing:
        r.error(path, f"{label}: 必須キー欠落 {missing}")
    wrong = [
        f"{k}(期待{t.__name__},実{type(data[k]).__name__})"
        for k, t in required.items() if k in data and not type_ok(data[k], t)
    ]
    if wrong:
        r.error(path, f"{label}: 型不正 {wrong}")


def check_id(stem: str, data: dict, path, r: Report) -> None:
    # スキーマ §0: ファイル名は {ID} または {ID}-サフィックス（例: chara-001-瀬川匠）
    file_id, suffix = file_id_of(stem)
    if file_id is None:
        r.error(path, f"ファイル名形式不正: {stem}（期待 {{ID}} または {{ID}}-サフィックス）")
        return
    if "id" not in data:
        r.error(path, "id キーが存在しない")
    elif data["id"] != file_id:
        r.error(path, f"ファイル名=ID 不一致: id={data['id']!r}（ファイル名先頭は {file_id!r}）")
    num = re.search(r"(\d+)$", file_id).group(1)
    if int(num) < 1:
        r.error(path, f"ID 連番不正: {file_id}（連番は 1 以上）")
    if suffix is not None:
        check_suffix(path, suffix, r)


def file_id_of(stem: str) -> tuple[str | None, str | None]:
    """ファイル名先頭から ID 部分を取り出す。suffix 付きも受理する。"""
    m = re.match(r"^(chara-\d{3}|world-\d{3}|plot-ch\d{2}|fs-\d{3})(?:-(.+))?$", stem)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def check_suffix(path, suffix: str, r: Report) -> None:
    """人間向けサフィックスの検査。OS で作れない文字はエラー、体裁は警告。"""
    if any(c in FORBIDDEN_FILENAME_CHARS or ord(c) < 32 for c in suffix):
        r.error(path, f"ファイル名サフィックスに使用禁止文字あり: {suffix!r}（\\/ : * ? \" < > | と制御文字は不可）")
        return
    if suffix != suffix.strip(" .") or suffix.startswith("."):
        r.error(path, f"ファイル名サフィックスの先頭・末尾不正: {suffix!r}（先頭の .・末尾の空白/. は不可）")
        return
    if " " in suffix or "　" in suffix:
        r.warn(path, f"ファイル名サフィックスにスペースあり: {suffix!r} → _ にすること")
    if display_width(suffix) > 30:
        r.warn(path, f"ファイル名サフィックスが長い（{display_width(suffix)}字相当）: {suffix!r} → 全角10字以内目安にすること")


def ranges_overlap(known: list[tuple[int, int | None]], a: int, b: int | None, path, idx: int, r: Report) -> None:
    """versions 章範囲重複の正確判定"""
    for k, (x, y) in enumerate(known):
        hi_a = 10**9 if b is None else b
        hi_x = 10**9 if y is None else y
        if max(a, x) <= min(hi_a, hi_x):
            r.error(path, f"versions[{idx}]: 章範囲重複 ({a}..{b if b is not None else '∞'} vs {x}..{y if y is not None else '∞'})")
            return


def validate_characters(chars, r: Report) -> set[str]:
    ids: set[str] = set()
    relations: list[tuple[Path, int, str]] = []
    for path, data in chars:
        check_id(path.stem, data, path, r)
        check_keys(
            data,
            {"id": str, "name_ja": str, "name_ruby": str, "role": str},
            path, "character ルート", r,
        )
        if type_ok(data.get("id"), str):
            ids.add(data["id"])
        # 任意キーの型検査（存在する場合のみ）＋仮名チェック（character-design-guide §0）
        role_v = data.get("role")
        if type_ok(role_v, str) and role_v not in VALID_ROLES:
            r.error(path, f"role 不正 '{role_v}'（protagonist / antagonist / support）")
        for opt in ("flaw", "quirk", "heat"):
            if opt in data and not type_ok(data[opt], str):
                r.error(path, f"{opt}: 文字列でない（{type(data[opt]).__name__}）")
        for key in ("name_ja", "name_ruby"):
            val = data.get(key)
            if type_ok(val, str) and re.search(r"(TBD|未定|（仮）|\(仮\))", val):
                r.warn(path, f"{key} が仮名のまま（{val}）→ 名前を確定してからプロットへ進むこと")
        design = data.get("design")
        if design is not None:
            if not isinstance(design, dict):
                r.error(path, "[design] がテーブルでない")
            else:
                stv = design.get("screen_time")
                if stv is not None and (not type_ok(stv, str) or stv not in VALID_SCREEN_TIME):
                    r.error(path, f"[design].screen_time 不正 '{stv}'（lead / support / minor）")
                if type_ok(stv, str) and stv in ("support", "minor"):
                    deep = [k for k in ("flaw", "quirk", "heat") if data.get(k)]
                    m = data.get("motivation")
                    if isinstance(m, dict) and m.get("false_belief"):
                        deep.append("false_belief")
                    if stv == "minor" and deep:
                        r.warn(path, f"screen_time=minor に物語装置キー {deep} あり → TOMLに書かず発想手順に留めること（schema §1）")
                    elif stv == "support" and len(deep) >= 2:
                        r.warn(path, f"screen_time=support の物語装置キーが {len(deep)} 件 {deep} → 1件までに絞ること（schema §1）")
        basic = data.get("basic")
        if basic is None:
            r.error(path, "[basic] セクション必須")
        elif not isinstance(basic, dict):
            r.error(path, "[basic] がテーブルでない")
        else:
            check_keys(basic, {"gender": str, "age": int, "first_person": str}, path, "[basic]", r)
        versions = data.get("versions", [])
        if versions and not isinstance(versions, list):
            r.error(path, "versions は [[versions]] 配列")
            versions = []
        known: list[tuple[int, int | None]] = []
        for i, v in enumerate(versions):
            if not isinstance(v, dict):
                r.error(path, f"versions[{i}] がテーブルでない")
                continue
            a = v.get("from_chapter")
            b = v.get("to_chapter")
            if not type_ok(a, int):
                r.error(path, f"versions[{i}]: from_chapter 必須(int)")
                continue
            if b is not None and (not type_ok(b, int) or b < a):
                r.error(path, f"versions[{i}]: 章範囲逆転 (from={a}, to={b})")
                continue
            ranges_overlap(known, a, b, path, i, r)
            known.append((a, b))
        for i, rel in enumerate(data.get("relations", [])):
            if not isinstance(rel, dict):
                r.error(path, f"relations[{i}] がテーブルでない")
                continue
            t = rel.get("target")
            if not type_ok(t, str):
                r.error(path, f"relations[{i}]: target 必須(str)")
            else:
                relations.append((path, i, t))
            for opt in ("kind", "function", "emotion", "call", "no_compromise", "note"):
                if opt in rel and not type_ok(rel[opt], str):
                    r.error(path, f"relations[{i}].{opt}: 文字列でない")
    for path, i, t in relations:
        if t not in ids:
            r.error(path, f"relations[{i}]: target '{t}' が存在しない chara ID")
    return ids


def validate_worlds(worlds, ref_ids: set[str], r: Report) -> None:
    for path, data in worlds:
        check_id(path.stem, data, path, r)
        check_keys(
            data,
            {"id": str, "title": str, "kind": str},
            path, "world ルート", r,
        )
        for i, c in enumerate(data.get("constraints", [])):
            if not isinstance(c, dict):
                r.error(path, f"constraints[{i}] がテーブルでない")
                continue
            kind = c.get("kind")
            if not type_ok(kind, str):
                r.error(path, f"constraints[{i}]: kind 必須(str)")
            elif kind not in VALID_CONSTRAINT_KINDS:
                r.error(path, f"constraints[{i}]: kind 不正 '{kind}'")
            elif kind == "forbidden_words" and not (isinstance(c.get("words"), list) and c["words"]):
                r.error(path, f"constraints[{i}]: forbidden_words には words 配列必須")
            elif kind == "unknown_to":
                if not type_ok(c.get("target"), str):
                    r.error(path, f"constraints[{i}]: unknown_to には target(ID) 必須")
                elif c["target"] not in ref_ids:
                    r.error(path, f"constraints[{i}]: target '{c['target']}' が存在しない")


def validate_plots(plots, ref_ids: set[str], r: Report) -> None:
    fs_ids: set[str] = set()
    for path, data in plots:
        check_id(path.stem, data, path, r)
        check_keys(
            data,
            {"id": str, "chapter": int, "title": str},
            path, "plot ルート", r,
        )
        ch = data.get("chapter")
        file_id, _suffix = file_id_of(path.stem)
        if type_ok(ch, int) and file_id != f"plot-ch{ch:02d}":
            r.warn(path, f"chapter={ch} とファイル名 {path.stem} の番号が一致しない")
        if type_ok(data.get("pov"), str) and data["pov"] not in ref_ids:
            r.error(path, f"pov: ID '{data['pov']}' が存在しない")

        scenes = data.get("scenes")
        if not isinstance(scenes, list) or not scenes:
            r.error(path, "scenes 必須・1件以上")
            scenes = []
        for i, s in enumerate(scenes):
            if not isinstance(s, dict):
                r.error(path, f"scenes[{i}] がテーブルでない")
                continue
            check_keys(
                s,
                {"title": str, "location": str, "pov": str, "characters": list, "content": str},
                path, f"scenes[{i}]", r,
            )
            chars_list = s.get("characters")
            if isinstance(chars_list, list):
                for cid in chars_list:
                    if not type_ok(cid, str):
                        r.error(path, f"scenes[{i}].characters: ID が文字列でない: {cid!r}")
                    elif cid not in ref_ids:
                        r.error(path, f"scenes[{i}].characters: ID '{cid}' が存在しない")
            if type_ok(s.get("pov"), str) and s["pov"] not in ref_ids:
                r.error(path, f"scenes[{i}].pov: ID '{s['pov']}' が存在しない")
            check_readability(path, f"scenes[{i}].content", s.get("content"), r)

        for i, f in enumerate(data.get("foreshadowing", [])):
            if not isinstance(f, dict):
                r.error(path, f"foreshadowing[{i}] がテーブルでない")
                continue
            check_keys(f, {"id": str, "content": str, "resolve_chapter": int}, path, f"foreshadowing[{i}]", r)
            fid = f.get("id")
            if type_ok(fid, str):
                if fid in fs_ids:
                    r.error(path, f"foreshadowing id 重複: {fid}")
                fs_ids.add(fid)
                if not fid.startswith("fs-"):
                    r.error(path, f"foreshadowing id prefix 不正: {fid}")
            rc = f.get("resolve_chapter")
            ra = f.get("resolved_at")
            if type_ok(rc, int) and type_ok(ra, int) and ra != rc:
                r.warn(path, f"foreshadowing[{i}]: resolved_at={ra} が resolve_chapter={rc} と不一致")
            check_readability(path, f"foreshadowing[{i}].content", f.get("content"), r)

        for i, e in enumerate(data.get("established", [])):
            if not isinstance(e, dict):
                r.error(path, f"established[{i}] がテーブルでない")
                continue
            st = e.get("status")
            if st is not None and st not in VALID_SUMMARY_STATUS:
                r.error(path, f"established[{i}]: status 不正 '{st}'")
            elif st == "proposed":
                content_head = str(e.get("content", ""))[:30]
                r.proposed_warnings.append(
                    f"{WARN} {path.name}: established[{i}]: proposed 残留（{content_head}…） → 確定は人間が status を confirmed に変更"
                )
            for cid in e.get("characters", []):
                if type_ok(cid, str) and cid not in ref_ids:
                    r.error(path, f"established[{i}].characters: ID '{cid}' が存在しない")
            check_readability(path, f"established[{i}].content", e.get("content"), r)

        ss = data.get("summary_status")
        check_readability(path, "summary", data.get("summary"), r)
        ch = data.get("chapter")
        if ss is not None and ss not in VALID_SUMMARY_STATUS:
            r.error(path, f"summary_status 不正 '{ss}'")
        elif ss == "proposed":
            r.proposed_warnings.append(
                f"{WARN} {path.name}: summary_status = proposed（章 {ch if type_ok(ch, int) else '?'} の要約が未確定） → 要約を確認のうえ人間が confirmed に変更"
            )


def validate_meta(project: Path, files: dict[Path, dict], r: Report) -> dict | None:
    meta_path = project / "meta.toml"
    if meta_path not in files:
        r.error(meta_path, "meta.toml が存在しない")
        return None
    data = files[meta_path]
    work = data.get("work")
    if not isinstance(work, dict):
        r.error(meta_path, "[work] セクション必須")
    else:
        check_keys(work, {"title": str, "genre": str, "status": str}, meta_path, "[work]", r)
        if work.get("status") not in VALID_WORK_STATUS:
            r.error(meta_path, f"work.status 不正 '{work.get('status')}'")
        # 企画承認ゲート（planning §7）：執筆フェーズ以降は plan_status = confirmed 必須。
        # planning 中の未記入は許容（旧プロジェクト移行のため。執筆時に必ずエラーになる）
        plan = work.get("plan_status")
        if work.get("status") in ("writing", "revision", "complete") and plan != "confirmed":
            r.error(meta_path, "企画未承認で執筆フェーズに入っている：[work] plan_status をユーザが confirmed に変更すること（planning §7）")
        elif plan is not None and plan not in ("draft", "confirmed"):
            r.error(meta_path, f"work.plan_status 不正 '{plan}'（draft / confirmed）")
    chapters = data.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        # 雛形（init.py 直後・plot 未作成）では chapters 未記入を許す（work.status = planning の場合のみ）
        work = data.get("work")
        if isinstance(work, dict) and work.get("status") == "planning":
            r.warn(meta_path, "[[chapters]] 未記入（planning 中は許容。plot 作成後に追記すること）")
        else:
            r.error(meta_path, "[[chapters]] 必須・1件以上")
        return data
    prev: int | None = None
    for i, c in enumerate(chapters):
        if not isinstance(c, dict):
            r.error(meta_path, f"chapters[{i}] がテーブルでない")
            continue
        check_keys(c, {"number": int, "plot": str}, meta_path, f"chapters[{i}]", r)
        num = c.get("number")
        if type_ok(num, int):
            if prev is not None and num <= prev:
                r.error(meta_path, f"chapters[{i}]: 章番号逆転/重複 ({prev} → {num})")
            prev = num
        rel = c.get("plot")
        if type_ok(rel, str):
            target = project / rel
            if not target.is_file():
                r.error(meta_path, f"chapters[{i}].plot: '{rel}' が存在しない")
            elif target.resolve() not in {f.resolve() for f in files}:
                r.error(meta_path, f"chapters[{i}].plot: '{rel}' が構文エラーでロード失敗")
        # 本文パスの存在チェック（schema §4: novel = "novel/chNN.md"、未執筆は省略可）
        novel_rel = c.get("novel")
        if novel_rel is not None:
            if not type_ok(novel_rel, str):
                r.error(meta_path, f"chapters[{i}].novel: 文字列で指定する（実 {type(novel_rel).__name__}）")
            elif not (project / novel_rel).is_file():
                r.error(meta_path, f"chapters[{i}].novel: '{novel_rel}' が存在しない（本文未保存 or パス誤り）")
        st = c.get("status")
        if st is not None and st not in VALID_CHAPTER_STATUS:
            r.error(meta_path, f"chapters[{i}]: status 不正 '{st}'")
    return data


# ---------------------------------------------------------------- index

def build_index(chars, worlds, plots) -> list[str]:
    out = [f"{'ID':<11} 種別   名称"]
    for _, d in chars:
        out.append(f"{d.get('id', '?'):<11} chara  {d.get('name_ja', '')}")
    for _, d in worlds:
        out.append(f"{d.get('id', '?'):<11} world  {d.get('title', '')}")
    for _, d in plots:
        out.append(f"{d.get('id', '?'):<11} plot   ch{d.get('chapter', '?')}: {d.get('title', '')}")
    return out


def check_proposal_sync(project: Path, chars, r: Report) -> None:
    """proposal.md の人物名・ふりがなと character TOML の照合（T6・警告系）。

    proposal.md の登場人物一覧に TOML の name_ja が見つからない、または
    proposal 側のふりがな表記が TOML の name_ruby と一致しない場合に警告する。
    """
    proposal = project / "proposal.md"
    if not proposal.is_file():
        return
    text = proposal.read_text(encoding="utf-8")
    for path, d in chars:
        name = d.get("name_ja")
        if type_ok(name, str) and name and name not in text:
            r.proposed_warnings.append(
                f"{WARN} proposal.md: character {d.get('id', '?')} の『{name}』が proposal.md に見つからない"
                f"（人物の追加漏れ or proposal の更新忘れ）"
            )
        ruby = d.get("name_ruby")
        if type_ok(ruby, str) and ruby:
            # ふりがなの区切り（'・' と半角/全角スペース）を揃えて比較
            norm = lambda s: s.replace("・", " ").replace("\u3000", " ")
            if norm(name or "") in text and norm(ruby) not in norm(text):
                r.proposed_warnings.append(
                    f"{WARN} proposal.md: 『{name}』のふりがな表記が TOML（{ruby}）と一致しない可能性"
                )


# ---------------------------------------------------------------- 制作ログ

def validate_log(project: Path, ref_ids: set[str], plots, r: Report) -> None:
    """production-log.toml の検証（スキーマ §7）。構造はエラー、参照先は警告のみ。"""
    log_path = project / "production-log.toml"
    if not log_path.is_file():
        return
    try:
        data = tomllib.loads(log_path.read_text(encoding="utf-8"))
    except Exception as e:
        r.error(log_path, f"TOML 構文エラー: {e}")
        return
    entries = data.get("log")
    if entries is None:
        return  # エントリ 0 件は正常（初回の決定は書かない方針）
    if not isinstance(entries, list):
        r.error(log_path, "[[log]] は配列で書く")
        return
    plot_ids = {d.get("id") for _, d in plots if type_ok(d.get("id"), str)}
    seen: set[str] = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            r.error(log_path, f"log[{i}] がテーブルでない")
            continue
        check_keys(
            e,
            {"id": str, "date": str, "kind": str, "what": str, "why": str, "by": str},
            log_path, f"log[{i}]", r,
        )
        eid = e.get("id")
        if type_ok(eid, str):
            if not LOG_ID_RE.match(eid):
                r.error(log_path, f"log[{i}]: id 形式不正 '{eid}'（期待 log-NNN）")
            elif eid in seen:
                r.error(log_path, f"log[{i}]: id 重複 '{eid}'")
            else:
                seen.add(eid)
        d = e.get("date")
        if type_ok(d, str) and not DATE_RE.match(d):
            r.error(log_path, f"log[{i}]: date 形式不正 '{d}'（期待 YYYY-MM-DD）")
        k = e.get("kind")
        if type_ok(k, str) and k not in VALID_LOG_KINDS:
            r.error(log_path, f"log[{i}]: kind 不正 '{k}'（change / reject / note）")
        b = e.get("by")
        if type_ok(b, str) and b not in VALID_LOG_BY:
            r.error(log_path, f"log[{i}]: by 不正 '{b}'（agent / human）")
        aff = e.get("affects")
        if aff is not None:
            if not isinstance(aff, list):
                r.error(log_path, f"log[{i}]: affects は配列で書く")
            else:
                for a in aff:
                    if not type_ok(a, str):
                        r.error(log_path, f"log[{i}].affects: 文字列でない {a!r}")
                    elif a in ("proposal", "agents"):
                        continue
                    elif a.startswith("plot-ch"):
                        if a not in plot_ids:
                            r.warn(log_path, f"log[{i}].affects: '{a}' に対応する plot が見つからない")
                    elif a not in ref_ids:
                        r.warn(log_path, f"log[{i}].affects: '{a}' が存在しない ID の可能性")


def print_log(project: Path, affects_filter: str | None) -> int:
    """--log: 制作ログを日付順の表で出力（--affects で絞り込み）。"""
    log_path = project / "production-log.toml"
    if not log_path.is_file():
        print(f"{ERR} production-log.toml が存在しない: {log_path}")
        return 1
    try:
        data = tomllib.loads(log_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"{ERR} production-log.toml: TOML 構文エラー: {e}")
        return 1
    entries = [e for e in (data.get("log") or []) if isinstance(e, dict)]
    if affects_filter:
        entries = [e for e in entries if affects_filter in (e.get("affects") or [])]
    entries.sort(key=lambda e: (str(e.get("date", "")), str(e.get("id", ""))))
    if not entries:
        print("[OK] 該当エントリなし" if affects_filter else "[OK] log エントリなし（初回の決定は書かない方針）")
        return 0
    print(f"{'date':<11} {'kind':<7} {'id':<8} {'by':<6} what")
    print("-" * 92)
    for e in entries:
        what = str(e.get("what", "")).replace("\n", " ")
        print(f"{str(e.get('date', '')):<11} {str(e.get('kind', '')):<7} {str(e.get('id', '')):<8} {str(e.get('by', '')):<6} {what}")
        why_lines = str(e.get("why", "")).strip().splitlines()
        if why_lines:
            suffix = "…" if len(why_lines) > 1 else ""
            print(f"{'':<33}└ {why_lines[0]}{suffix}")
        aff = e.get("affects")
        if aff:
            print(f"{'':<33}affects: {', '.join(map(str, aff))}")
    print(f"\n計 {len(entries)} 件" + (f"（affects = {affects_filter} で絞り込み）" if affects_filter else ""))
    return 0


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="novel2agent-jp 設定検証")
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--index", action="store_true", help="ID→名称一覧のみ出力")
    ap.add_argument("--log", action="store_true", help="制作ログを日付順の表で出力")
    ap.add_argument("--affects", help="--log と併用。指定 ID を含むエントリに絞る")
    args = ap.parse_args()

    project = Path(args.project_dir)
    if not project.is_dir():
        print(f"{ERR} project-dir が存在しない: {project}")
        return 1

    files, parse_errors = load_all(project)
    chars = by_prefix(files, "chara")
    worlds = by_prefix(files, "world")
    plots = by_prefix(files, "plot")

    if args.index:
        for line in build_index(chars, worlds, plots):
            print(line)
        return 0

    if args.log:
        return print_log(project, args.affects)

    r = Report()
    for path, err in parse_errors:
        print(f"{ERR} {path.name}: TOML 構文エラー: {err}")
        r.error(path, "構文エラーのためこのファイルは検証不能")

    chara_ids = validate_characters(chars, r)
    # 参照 ID は構文エラーで欠けた分も考慮 → ロード済み ID の和集合
    ref_ids = chara_ids | {d.get("id") for _, d in worlds if type_ok(d.get("id"), str)}
    validate_worlds(worlds, ref_ids, r)
    validate_plots(plots, ref_ids, r)
    validate_meta(project, files, r)
    check_proposal_sync(project, chars, r)
    validate_log(project, ref_ids, plots, r)
    for path in files:
        check_literal_style(path, r)
    log_path = project / "production-log.toml"
    if log_path.is_file():
        check_literal_style(log_path, r)

    print()
    print(f"== 検証結果 ({len(files)} TOML ファイル) ==")
    for line in r.errors:
        print(line)
    if r.proposed_warnings:
        print(f"\n-- 未確定設定（proposed）: {len(r.proposed_warnings)} 件 --")
        for line in r.proposed_warnings:
            print(line)
    # 警告合計 = proposed 系 + その他
    total_warnings = len(r.warnings) + len(r.proposed_warnings)
    if r.warnings:
        print("\n-- その他の警告 --")
        for line in r.warnings:
            print(line)
    print(f"\nエラー {len(r.errors)} 件 / 警告 {total_warnings} 件（うち未確定設定 {len(r.proposed_warnings)} 件）")
    return 0 if not r.errors else 1


if __name__ == "__main__":
    sys.exit(main())
