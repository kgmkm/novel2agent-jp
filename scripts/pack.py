#!/usr/bin/env python3
"""novel2agent-jp: 第N章執筆用コンテキストパック生成 (P1-3)

スキーマ: schema/toml-schema.md §6
出力:   .context/chNN.md（再生成可能な派生物・.gitignore 対象）

Usage:
  python pack.py --project-dir <path> --chapter 3
  python pack.py --project-dir <path> --chapter 3 --budget 80000
  python pack.py --project-dir <path> --chapter 3 --check     # 鮮度チェックのみ
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

SOURCE_DIRS = ("character", "worldbuilding", "plot")
DEFAULT_BUDGET = 100_000  # トークン概算（日本語 ≈ 1 文字 ≈ 1 token）
APPEARANCE_KEYS = {"hair", "hair_color", "eyes", "skin", "face", "outfit", "outfit_special", "accessory"}


def est_tokens(text: str) -> int:
    """トークン概算。日本語では 1 文字 ≈ 1 トークン程度とみなす。"""
    return len(text)


# ---------------------------------------------------------------- ロード

def load_all(project: Path):
    files: dict[Path, dict] = {}
    errors: list[str] = []
    paths: list[Path] = []
    for sub in SOURCE_DIRS:
        d = project / sub
        if d.is_dir():
            paths.extend(sorted(d.glob("*.toml")))
    meta_path = project / "meta.toml"
    if meta_path.is_file():
        paths.append(meta_path)
    for f in paths:
        try:
            files[f] = tomllib.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"[ERROR] {f.name}: TOML 構文エラー: {e}")
    return files, errors


def by_prefix(files: dict[Path, dict], prefix: str):
    return [(f, d) for f, d in sorted(files.items())
            if f.stem.split("-")[0] == prefix or (prefix == "plot" and f.stem.startswith("plot-ch"))]


def load_log(project: Path) -> list[dict]:
    """production-log.toml の [[log]] を読む（スキーマ §7）。無ければ空。"""
    log_path = project / "production-log.toml"
    if not log_path.is_file():
        return []
    try:
        data = tomllib.loads(log_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    entries = data.get("log")
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict)]


# ---------------------------------------------------------------- versions 解決

def resolve_chara(data: dict, chapter: int) -> dict:
    """章 N 時点の属性を versions で解決する（from_chapter ≦ N の version のみ適用、後勝ち）。

    versions に [basic] 配下のキー（age / gender / first_person など）が書かれた場合は
    basic テーブルへ反映する（スキーマ §1 の「age などキャラ固有の追加キー」の扱い）。
    [appearance] 系キー（outfit / hair 等）は appearance テーブルへ反映する。
    """
    out = dict(data)
    basic = dict(out.get("basic") or {})
    for v in data.get("versions", []):
        a, b = v.get("from_chapter"), v.get("to_chapter")
        if not isinstance(a, int):
            continue
        if a <= chapter and (b is None or chapter <= b):
            basic_keys = {"age", "gender", "first_person", "speech_style", "height_cm"}
            for k, val in v.items():
                if k in ("from_chapter", "to_chapter", "note"):
                    continue
                if k in basic_keys:
                    basic[k] = val
                elif k in APPEARANCE_KEYS:
                    app = out.get("appearance")
                    if app is None or isinstance(app, dict):
                        app = dict(app or {})
                        app[k] = val
                        out["appearance"] = app
                    else:
                        out[k] = val
                else:
                    out[k] = val
    if basic:
        out["basic"] = basic
    out.pop("versions", None)
    return out


# ---------------------------------------------------------------- レンダ

def render_chara(cid: str, c: dict, full_depth: bool = True) -> str:
    """full_depth=False の章では flaw / quirk / heat / false_belief を出さない。
    物語装置キーを毎章出すと弱い LLM がチェックリストと読んで儀式化するため
    （schema §1）。演技情報（fears / catchphrase / habits 等）は常に出す。"""
    basic = c.get("basic", {}) if isinstance(c.get("basic"), dict) else {}
    design = c.get("design") if isinstance(c.get("design"), dict) else {}
    st = f"［{design['screen_time']}］" if design.get("screen_time") else ""
    lines = [f"### {cid}: {c.get('name_ja', '?')}（{c.get('name_ruby', '')}）{st}"]
    facts = [f"role: {c.get('role', '?')}"]
    if basic.get("age") is not None:
        facts.append(f"年齢: {basic['age']}")
    if basic.get("gender"):
        facts.append(f"性別: {basic['gender']}")
    if basic.get("first_person"):
        facts.append(f"一人称: {basic['first_person']}")
    if basic.get("second_person"):
        facts.append(f"二人称: {basic['second_person']}")
    lines.append("- " + " / ".join(facts))
    if basic.get("speech_style"):
        lines.append(f"- 口調: {basic['speech_style']}")
    p = c.get("personality")
    if isinstance(p, dict):
        if p.get("keywords"):
            lines.append(f"- 性格: {'、'.join(p['keywords'])}")
        if p.get("strengths"):
            lines.append(f"- 長所: {p['strengths']}")
        if p.get("weaknesses"):
            lines.append(f"- 短所: {p['weaknesses']}")
    if full_depth:
        for key, label in (("flaw", "欠点"), ("quirk", "ズレ"), ("heat", "必死になる対象")):
            if c.get(key):
                lines.append(f"- {label}: {c[key]}")
    m = c.get("motivation")
    if isinstance(m, dict):
        if full_depth and m.get("false_belief"):
            lines.append(f"- 誤った信念（物語中で崩される）: {m['false_belief']}")
        if m.get("fears"):
            lines.append(f"- 恐れ: {m['fears']}")
        if m.get("catchphrase"):
            lines.append(f"- 決め台詞: {m['catchphrase']}")
        if m.get("habits"):
            lines.append(f"- 癖: {m['habits']}")
    app = c.get("appearance")
    if isinstance(app, dict) and app:
        desc = "、".join(v for v in app.values() if isinstance(v, str))
        if desc:
            lines.append(f"- 外見: {desc}")
    for rel in c.get("relations", []):
        if isinstance(rel, dict):
            parts = [f"{rel.get('target', '?')}（{rel.get('kind', '')}"]
            if rel.get("function"):
                parts.append(f"・機能:{rel['function']}")
            if rel.get("emotion"):
                parts.append(f"・{rel['emotion']}")
            parts.append("）")
            text = "- 関係: " + "".join(parts)
            if rel.get("no_compromise"):
                text += f"／妥協不可: {rel['no_compromise']}"
            lines.append(text)
    return "\n".join(lines)


def render_constraints(worlds) -> str:
    lines = []
    for _, d in worlds:
        for c in d.get("constraints", []):
            if not isinstance(c, dict):
                continue
            kind = c.get("kind", "?")
            note = f"（{c['note']}）" if c.get("note") else ""
            if kind == "forbidden_words":
                lines.append(f"- 禁止語彙: {', '.join(c.get('words', []))}{note}")
            elif kind == "unknown_to":
                lines.append(f"- {c.get('target', '?')} の知識範囲外{note}: {', '.join(c.get('words', []))}")
            else:
                lines.append(f"- {kind}: {c.get('note', '')}{note}".rstrip())
    return "\n".join(lines)


# ---------------------------------------------------------------- パック構成

class Block:
    """budget 制御の単位。priority が大きいほど残す (6.3 の削り順: 小さい数字から削る)"""

    def __init__(self, text: str, priority: int):
        self.text = text
        self.priority = priority  # 1=最優先(削らない) … 6=最も削りやすい


def collect_blocks(files: dict[Path, dict], project: Path, chapter: int, plots_by_chapter) -> tuple[list[Block], list[str]]:
    blocks: list[Block] = []
    errors: list[str] = []

    target_plot = plots_by_chapter.get(chapter)
    if target_plot is None:
        errors.append(f"[ERROR] 章 {chapter} の plot TOML が存在しない")
        return blocks, errors
    _, plot = target_plot

    # --- (1) 対象章メタデータ + 登場キャラ: priority 1（削らない）
    lines = [f"# 第{chapter}章 執筆コンテキスト: {plot.get('title', '')}"]
    if plot.get("pov"):
        lines.append(f"- 章視点: {plot['pov']}")
    if plot.get("peak_intensity") is not None:
        lines.append(f"- 感情曲線ピーク: {plot['peak_intensity']}%")
    lines.append(f"- summary_status: {plot.get('summary_status', 'confirmed 前提')}")

    chars = {d.get("id"): d for _, d in by_prefix(files, "chara") if isinstance(d.get("id"), str)}
    appearing: set[str] = set()
    lines.append("\n## シーン")
    for s in plot.get("scenes", []):
        if not isinstance(s, dict):
            continue
        appearing.update(s.get("characters", []) or [])
        head = f"- 【{s.get('title', '?')}】{s.get('location', '?')}／{s.get('time', '')}".rstrip("／")
        if s.get("pov"):
            head += f"（視点 {s['pov']}）"
        lines.append(head)
        lines.append(f"  演出: {s.get('content', '')}")
        if s.get("emotion_peak"):
            lines.append(f"  感情: {s['emotion_peak']}")
        if s.get("characters"):
            lines.append(f"  登場: {', '.join(s['characters'])}")
    resolved = {cid: resolve_chara(chars[cid], chapter) for cid in sorted(appearing) if cid in chars}
    missing = [cid for cid in sorted(appearing) if cid not in chars]
    if missing:
        lines.append("\n**警告: character/ に存在しない ID → " + ", ".join(missing) + "**")
    lines.append("\n## 登場キャラ（この章時点で versions 解決済み）")
    pov = plot.get("pov")
    # 初出章の算出：物語装置キー（flaw/quirk/heat/false_belief）は
    # 章視点キャラと各キャラの初出章にだけ出す（schema §1）。毎章出すと
    # 弱い LLM がチェックリストと読んで儀式化する
    first_seen: dict[str, int] = {}
    for num in sorted(plots_by_chapter):
        try:
            _, pd = plots_by_chapter[num]
        except (TypeError, ValueError):
            continue
        if not isinstance(pd, dict):
            continue
        for s in pd.get("scenes", []) or []:
            if not isinstance(s, dict):
                continue
            for member in s.get("characters", []) or []:
                first_seen.setdefault(member, num)
    for cid in sorted(resolved):
        full = (cid == pov) or (first_seen.get(cid) == chapter)
        lines.append(render_chara(cid, resolved[cid], full_depth=full))
    blocks.append(Block("\n".join(lines), priority=1))

    # --- (2) worldbuilding 制約: priority 2
    wc = render_constraints(by_prefix(files, "world"))
    if wc:
        blocks.append(Block("## 世界観制約\n" + wc, priority=2))

    # --- (3) 未回収伏線: resolve_chapter ≦ N かつ resolved_at なし。
    # 伏線は「単一点情報源」の核心（§6.6 抽出漏れ禁止）のため budget でも削らない。priority 1 相当で保持
    fs_items: list[str] = []
    for num in sorted(c for c in plots_by_chapter if c < chapter):
        _, pd = plots_by_chapter[num]
        for fsh in pd.get("foreshadowing", []):
            if isinstance(fsh, dict) and isinstance(fsh.get("resolve_chapter"), int) \
                    and fsh["resolve_chapter"] <= chapter and not fsh.get("resolved_at"):
                fs_items.append(f"- [{num}章で張った → {fsh['resolve_chapter']}章で回収予定] "
                                f"{fsh.get('content', '')}")
    if fs_items:
        blocks.append(Block("## 未回収伏線\n" + "\n".join(fs_items), priority=2))

    # --- (4) established: 6.2。直近2章分は全件、それ以前は章単位ロールアップ（proposed は常に全件）。
    # 各要素を個別 block 化し、budget 削りに強くする。priority 4
    est_blocks = []
    for num in sorted(c for c in plots_by_chapter if c < chapter):
        _, pd = plots_by_chapter[num]
        confirmed_items = []
        for e in pd.get("established", []):
            if not isinstance(e, dict) or not e.get("content"):
                continue
            if e.get("status") == "proposed":
                est_blocks.append((num, f"- 【未確定】{num}章: {e['content']}"))
            else:
                confirmed_items.append(e["content"])
        if not confirmed_items:
            continue
        if chapter - num <= 2:
            for item in confirmed_items:
                est_blocks.append((num, f"- {num}章: {item}"))
        else:
            est_blocks.append((num, f"- {num}章（ロールアップ）: " + "、".join(confirmed_items)))
    if est_blocks:
        body = "\n".join(t for _, t in est_blocks)
        blocks.append(Block("## これまでに確定した出来事（established）\n" + body, priority=4))

    # --- (4b) 制作ログ: priority 4.5。affects が対象章 / 登場キャラに関係する全件 + 直近10件
    # （スキーマ §7。却下済みの案 reject は再提案防止のため優先的に載せる）
    log_entries = load_log(project)
    if log_entries:
        target_ids = {f"plot-ch{chapter:02d}"} | set(appearing)
        related: list[dict] = []
        related_idx: set[int] = set()
        for i, e in enumerate(log_entries):
            aff = {str(a) for a in (e.get("affects") or [])}
            if target_ids & aff:
                related.append(e)
                related_idx.add(i)
        start = max(0, len(log_entries) - 10)
        recent = [e for i, e in enumerate(log_entries) if i >= start and i not in related_idx]
        picked = related + recent
        if picked:
            log_lines = []
            for e in picked:
                why_first = str(e.get("why", "")).strip().splitlines()
                head = f"- [{e.get('date', '?')}][{e.get('kind', '?')}] {e.get('what', '')}"
                if why_first:
                    head += f" — {why_first[0]}"
                log_lines.append(head)
            blocks.append(Block("## 制作ログ（なぜ変えたか・却下した案）\n" + "\n".join(log_lines), priority=4.5))

    # --- (5) 過去章 summary（古い章から順に落とされる）: priority 5
    summaries = []
    for num in sorted(c for c in plots_by_chapter if c < chapter):
        _, pd = plots_by_chapter[num]
        sm = pd.get("summary")
        if not sm:
            continue
        st = pd.get("summary_status", "proposed")
        tag = "【未確定】" if st == "proposed" else ""
        summaries.append(Block(f"### 第{num}章 要約{tag}\n{sm}", priority=5))
    blocks.extend(summaries)

    # --- (6) 直前章本文: priority 6（末尾から削る）
    prev = chapter - 1
    meta_ch = meta_chapter_of(project, files, prev)
    novel_rel = (meta_ch or {}).get("novel") if meta_ch else None
    if meta_ch and not novel_rel:
        # meta に novel 未指定なら規約パス novel/chNN.md を試す（推測で埋めない方針のため、無ければ省略）
        cand = project / "novel" / (f"ch{prev:02d}.md")
        if cand.is_file():
            novel_rel = str(cand.relative_to(project))
    if meta_ch and novel_rel:
        src = project / novel_rel
        if src.is_file():
            body = src.read_text(encoding="utf-8").strip()
            blocks.append(Block(f"## 前章 ({prev}章) 本文\n\n{body}", priority=6))
        else:
            errors.append(f"[ERROR] {novel_rel} が存在しない（meta.toml chapters[{prev - 1}].novel）")
    return blocks, errors


def meta_chapter_of(project: Path, files: dict[Path, dict], number: int) -> dict | None:
    meta_path = project / "meta.toml"
    if meta_path not in files:
        return None
    for c in files[meta_path].get("chapters", []):
        if isinstance(c, dict) and c.get("number") == number:
            return c
    return None


# ---------------------------------------------------------------- 出力

def build_markdown(blocks: list[Block], budget: int) -> tuple[str, list[str]]:
    """budget 制御（§6.3 削り順）。

    priority 6 の直前章本文のみ「末尾から」部分的に削る。
    それでも超過する場合は priority 5（古い章 summary から）→ 4.5（制作ログ）→ 4 → 3 → 2 の順で
    block 単位で落とす。priority 1 は削らない。
    """
    notes: list[str] = []
    kept = list(blocks)

    def total() -> int:
        return sum(est_tokens(b.text) for b in kept)

    over = total() - budget
    if over <= 0:
        pass
    else:
        # (a) 直前章本文（priority 6）を末尾から削る
        for b in kept:
            if b.priority != 6:
                continue
            marker = "\n\n"
            i = b.text.find(marker)
            head, body_part = (b.text, "") if i < 0 else (b.text[:i], b.text[i + 2:])
            if body_part and over < len(body_part):
                keep_len = len(body_part) - over
                body_part = body_part[:keep_len] + "\n\n[…budget 制限により以下省略]"
                b.text = head + "\n\n" + body_part
                notes.append(f"budget({budget}) 超過: 直前章本文を末尾から {keep_len} 文字に削った")
                over = 0
                break
            else:
                kept.remove(b)
                notes.append(f"budget({budget}) 超過: 直前章本文を丸ごと削った")
                over = max(total() - budget, 0)
                break
        # (b) なお超過する場合: summary → established → 伏線 → 制約 の順に block 削除
        names = {2: "世界観制約", 3: "未回収伏線", 4: "established", 5: "章要約"}
        while total() > budget:
            for prio in (5, 4, 3, 2):
                candidates = [b for b in kept if b.priority == prio]
                if candidates:
                    dropped = candidates[0]  # 章順ソート済みリストの先頭 = 最古
                    kept.remove(dropped)
                    notes.append(f"budget({budget}) 超過: {names[prio]}の 1 ブロック（{dropped.text.splitlines()[0][:40]}…）を削った")
                    break
            else:
                notes.append("budget 超過だが削れるブロックがない（priority 1 のみ残存）")
                break

    # 出力順 = 収録順（priority 昇順）
    kept.sort(key=lambda b: b.priority)
    return "\n\n---\n\n".join(b.text for b in kept) + "\n", notes


def freshness_check(project: Path, project_file: Path, chapter: int | None = None) -> int:
    """pack.py --check: .context/chNN.md より新しい原典があれば警告。

    --chapter N を指定した場合は第 N 章のパックを構成する原典だけを比較する
    （対象章の plot + 全 character/worldbuilding + meta + chapter < N の plot/novel）。
    後続章の本文更新で前章パックが誤判定されないようにするため。
    """
    ctx_dir = project / ".context"
    if not ctx_dir.is_dir():
        print("[WARN] .context/ が無い → pack.py を実行して生成してください")
        return 1

    if chapter is None:
        source_files = [f for sub in SOURCE_DIRS + ("novel",)
                        for f in (project / sub).rglob("*")
                        if (project / sub).is_dir() and f.is_file()]
    else:
        files, errors = load_all(project)
        if errors:
            for e in errors:
                print(e)
            return 1
        chapter_of = {}
        for _, d in by_prefix(files, "plot"):
            if isinstance(d.get("chapter"), int):
                chapter_of[d["chapter"]] = d
        source_files = []
        for sub in ("character", "worldbuilding", "meta"):
            d = project / sub
            if sub == "meta":
                mf = project / "meta.toml"
                if mf.is_file():
                    source_files.append(mf)
            elif d.is_dir():
                source_files.extend(f for f in sorted(d.glob("*.toml")) if f.is_file())
        for num, data in chapter_of.items():
            if num <= chapter and len(data.get("id", "")) > 0:
                pf = project / "plot" / f"plot-ch{num:02d}.toml"
                if pf.is_file():
                    source_files.append(pf)
                novel_rel = None
                for c in files.get(project / "meta.toml", {}).get("chapters", []):
                    if isinstance(c, dict) and c.get("number") == num:
                        novel_rel = c.get("novel")
                        break
                if novel_rel:
                    nf = project / novel_rel
                    if nf.is_file():
                        source_files.append(nf)
        source_files = sorted(set(source_files))

    newest_source = max((f.stat().st_mtime for f in source_files), default=0.0)
    if newest_source == 0.0:
        print("[OK] 原典ファイルなし（新規プロジェクト）")
        return 0
    stale = 0
    for ctx in sorted(ctx_dir.glob("ch*.md")):
        if chapter is not None and ctx.stem != f"ch{chapter:02d}":
            continue
        if ctx.stat().st_mtime < newest_source:
            print(f"[WARN] {ctx.name}: 原典より古い → pack.py で再生成してください")
            stale += 1
    if not stale:
        print("[OK] すべての .context は原典より新しい")
    return 1 if stale else 0


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="novel2agent-jp コンテキストパック生成")
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    ap.add_argument("--check", action="store_true", help="鮮度チェックのみ")
    args = ap.parse_args()

    project = Path(args.project_dir)
    if not project.is_dir():
        print(f"[ERROR] project-dir が存在しない: {project}")
        return 1

    if args.check:
        return freshness_check(project, None, args.chapter)

    if args.chapter is None:
        ap.error("--chapter が必要（--check 以外の場合）")

    files, errors = load_all(project)
    meta_ch = meta_chapter_of(project, files, args.chapter)
    if meta_ch is None:
        errors.append(f"[ERROR] meta.toml に第{args.chapter}章の記述がない")

    plots_by_chapter = {}
    for _, d in by_prefix(files, "plot"):
        if isinstance(d.get("chapter"), int):
            plots_by_chapter[d["chapter"]] = (d.get("id"), d)

    blocks, pack_errors = collect_blocks(files, project, args.chapter, plots_by_chapter)
    errors.extend(pack_errors)
    if errors:
        for e in errors:
            print(e)
        return 1

    # project_dir 相対パスの正規化（キー比較用に resolve 済みと仮定して動くload）
    md, notes = build_markdown(blocks, args.budget)
    ctx_dir = project / ".context"
    ctx_dir.mkdir(exist_ok=True)
    out = ctx_dir / f"ch{args.chapter:02d}.md"
    out.write_text(md, encoding="utf-8")

    print(f"[OK] {out}")
    print(f"     約 {est_tokens(md)} トークン / budget {args.budget}")
    for n in notes:
        print(f"     [NOTE] {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
