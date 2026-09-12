#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pixiv_export.py — novel2hermes_jp pixiv小説エクスポート

novel/ 配下の.mdファイルを pixiv小説投稿用の単一ファイルに統合する。
本文は改変しない（pure conversion）。記法のみ pixiv 形式に統一する。

Usage:
    python pixiv_export.py --project-dir ~/novel-project
    python pixiv_export.py --input-dir ./novel --output ./export/pixiv.md
    python pixiv_export.py --project-dir ~/novel-project --split
    python pixiv_export.py --project-dir ~/novel-project --verify
    python pixiv_export.py --project-dir ~/novel-project --check-length

License: MIT
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

__version__ = "1.0.0"

# pixiv 単発投稿の字数制限
PIXIV_MAX_CHARS = 50000

# 推奨プレースホルダーフォーマット（最終形）
IMAGE_PLACEHOLDER_FINAL = "[※挿絵{}]"
# 内部用: プレースホルダー生成中の一意なマーカー（再マッチ回避用）
IMAGE_PLACEHOLDER_TMP = "\x00IMG{}\x00"


# ---------------------------------------------------------------------------
# 章読込
# ---------------------------------------------------------------------------

CHAPTER_FILE_RE = re.compile(r"^(\d+)-(.+)\.md$")
H1_H2_RE = re.compile(r"^#+\s+.+$", re.MULTILINE)


def load_novel_chapters(novel_dir: Path) -> list[dict]:
    """novel/配下の.mdファイルを章順にソートして読み込む

    Returns:
        list of {"order": int, "title": str, "body": str, "filename": str}
    """
    if not novel_dir.exists():
        raise FileNotFoundError(f"novel/ ディレクトリが存在しません: {novel_dir}")

    chapters = []
    for f in sorted(novel_dir.glob("*.md")):
        m = CHAPTER_FILE_RE.match(f.name)
        if not m:
            print(f"  [WARN] ファイル名規約に合致しないためスキップ: {f.name}", file=sys.stderr)
            continue

        order = int(m.group(1))
        file_title = m.group(2).replace("_", "　")
        content = f.read_text(encoding="utf-8")
        lines = content.split("\n")

        # 本文先頭のH1/H2を章タイトルとして優先
        first_heading = H1_H2_RE.match(lines[0]) if lines else None
        if first_heading:
            title = first_heading.group(0).lstrip("#").strip()
        else:
            title = file_title

        # H1/H2行は本文から除去（pixivで再付与するため）
        body = H1_H2_RE.sub("", content, count=1).strip()

        chapters.append({
            "order": order,
            "title": title,
            "body": body,
            "filename": f.name,
        })

    if not chapters:
        raise ValueError(f"章ファイルが見つかりません: {novel_dir}/*.md")

    return sorted(chapters, key=lambda c: c["order"])


# ---------------------------------------------------------------------------
# 記法変換
# ---------------------------------------------------------------------------

# 独自記法 → pixivルビ
RUBY_BRACE_RE = re.compile(r"\{([^|}]+)\|([^}]+)\}")
RUBY_RB_RE = re.compile(r"\[\[rb:\s*([^>]+?)\s*>\s*([^\]]+?)\s*\]\]")


def normalize_ruby(text: str) -> str:
    """独自ルビ記法を pixiv 形式 ｜漢字《るび》 に統一"""
    text = RUBY_BRACE_RE.sub(r"｜\1《\2》", text)
    text = RUBY_RB_RE.sub(r"｜\1《\2》", text)
    return text


def normalize_images(text: str) -> tuple[str, int]:
    """画像タグをプレースホルダーに置換

    対応入力:
        ![alt](URL)
        ![img](filename.png)
        [[image:N]]
        （※挿絵） 等の日本語マーカー

    実装: 内部マーカー (\x00IMG{N}\x00) で一旦置換し、最後に [※挿絵{N}] に変換する。
    これにより「※挿絵」マーカーが再マッチして二重カウントされるバグを防ぐ。
    """
    counter = [0]

    def replacer(match: re.Match) -> str:
        counter[0] += 1
        return IMAGE_PLACEHOLDER_TMP.format(counter[0])

    # Markdown標準の画像記法
    text = re.sub(r"!\[.*?\]\([^)]+\)", replacer, text)
    # [[image:N]] 形式
    text = re.sub(r"\[\[image:\d+\]\]", replacer, text)
    # （※挿絵） 等の日本語マーカー
    text = re.sub(r"（※挿絵）", replacer, text)
    text = re.sub(r"※挿絵", replacer, text)

    # 内部マーカー → 最終プレースホルダーに変換
    text = re.sub(r"\x00IMG(\d+)\x00", lambda m: IMAGE_PLACEHOLDER_FINAL.format(m.group(1)), text)

    return text, counter[0]


def normalize_whitespace(text: str) -> str:
    """連続空行を1つに統一。末尾改行を確保"""
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.rstrip() + "\n"


def render_chapter(order: int, title: str, body: str) -> str:
    """章をpixiv用のh2見出し付きで出力"""
    return f"## 第{order}章　{title}\n\n{body}"


# ---------------------------------------------------------------------------
# メタデータ
# ---------------------------------------------------------------------------

def load_proposal_metadata(project_dir: Path) -> dict:
    """proposal.md から title/synopsis/r18 を抽出"""
    proposal = project_dir / "proposal.md"
    meta = {"title": "", "synopsis": "", "r18": ""}
    if not proposal.exists():
        return meta

    text = proposal.read_text(encoding="utf-8")
    # 簡易パース: ## タイトル / ## 概要 / ## R-18
    for key, section in [("title", "タイトル"), ("synopsis", "概要"), ("r18", "R-18")]:
        m = re.search(rf"^##\s+{re.escape(section)}\s*\n(.+?)(?=\n##|\Z)", text, re.MULTILINE | re.DOTALL)
        if m:
            meta[key] = m.group(1).strip()
    return meta


def build_header(meta: dict, chapter_count: int, char_count: int, image_count: int) -> str:
    """pixiv設定メモのHTMLコメントヘッダー"""
    title = meta.get("title") or "（タイトル未設定 — proposal.md を確認）"
    synopsis = meta.get("synopsis") or "（あらすじ未設定）"
    r18 = meta.get("r18") or "（投稿時に設定）"

    return f"""<!--
pixiv設定メモ（投稿時に pixiv 側で入力）
==========================================
タイトル: {title}
あらすじ: {synopsis}
R-18:    {r18}
文字数:   約{char_count:,}字（コメント除く）
挿絵数:   {image_count}箇所
==========================================
-->



"""


def build_footer(source_files: list[str], chapter_count: int) -> str:
    """変換ログのHTMLコメントフッター"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    files_str = "\n             ".join(source_files)
    return f"""


---

<!--
変換ログ
==========================================
ソース:
             {files_str}

章数:       {chapter_count}
変換日時:   {now}
変換者:      pixiv_export.py v{__version__}
==========================================
このフッターは pixiv 投稿時に削除してください。
-->"""


# ---------------------------------------------------------------------------
# エクスポート
# ---------------------------------------------------------------------------

def build_pixiv_text(chapters: list[dict], meta: dict) -> tuple[str, int, int]:
    """章リストを受け取り pixiv 形式の単一テキストを生成

    Returns:
        (text, total_chars, total_images)
    """
    parts = []
    total_chars = 0
    total_images = 0

    for ch in chapters:
        body = ch["body"]
        body, n_imgs = normalize_images(body)
        body = normalize_ruby(body)
        body = normalize_whitespace(body)
        total_images += n_imgs
        total_chars += len(body)
        parts.append(render_chapter(ch["order"], ch["title"], body))

    body_text = "\n\n".join(parts)
    header = build_header(meta, len(chapters), total_chars, total_images)
    source_files = [ch["filename"] for ch in chapters]
    footer = build_footer(source_files, len(chapters))

    return header + body_text + footer, total_chars, total_images


def export_pixiv(
    project_dir: Path,
    output_path: Path,
    split: bool = False,
) -> dict:
    """プロジェクトディレクトリを受け取り、export/pixiv.md を生成"""
    novel_dir = project_dir / "novel"
    proposal_dir = project_dir

    chapters = load_novel_chapters(novel_dir)
    meta = load_proposal_metadata(proposal_dir)

    if split:
        # 章ごとに分割出力
        output_path.parent.mkdir(parents=True, exist_ok=True)
        files_written = []
        for ch in chapters:
            ch_meta = {**meta, "synopsis": f"{meta.get('synopsis', '')}（第{ch['order']}章）"}
            text, chars, imgs = build_pixiv_text([ch], ch_meta)
            ch_path = output_path.parent / f"{output_path.stem}_{ch['order']:02d}.md"
            ch_path.write_text(text, encoding="utf-8")
            files_written.append(str(ch_path))
        return {
            "mode": "split",
            "files": files_written,
            "chapters": len(chapters),
        }

    # 単一ファイル出力
    text, chars, imgs = build_pixiv_text(chapters, meta)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")

    return {
        "mode": "single",
        "output": str(output_path),
        "chapters": len(chapters),
        "chars": chars,
        "images": imgs,
    }


# ---------------------------------------------------------------------------
# 検証
# ---------------------------------------------------------------------------

COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
HEADING_RE = re.compile(r"^## .+$", re.MULTILINE)
HR_RE = re.compile(r"^---+\s*$", re.MULTILINE)
RUBY_INV_RE = re.compile(r"｜([^《]+)《([^》]+)》")
RUBY_BRACE_RE = re.compile(r"\{([^|}]+)\|([^}]+)\}")
RUBY_RB_RE = re.compile(r"\[\[rb:\s*([^>]+?)\s*>\s*([^\]]+?)\s*\]\]")


def normalize_for_diff(text: str) -> str:
    text = COMMENT_RE.sub("", text)
    text = HEADING_RE.sub("", text)
    text = HR_RE.sub("", text)
    text = re.sub(r"\[※挿絵\d+\]", "", text)
    text = RUBY_INV_RE.sub(r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.rstrip() + "\n"


def verify_no_modification(project_dir: Path, export_path: Path) -> bool:
    """novel/本文とexport本文が完全一致するか検証

    正規化:
    1. HTMLコメント除去
    2. 見出し除去
    3. プレースホルダー・画像タグ除去
    4. ルビ記法を統一的に除去（独自 {A|B} / pixiv ｜A《B》 / RB [[rb:]] をすべて親文字に）
    5. 連続空行を1つに
    6. 行頭・行末の空白除去
    7. 段落区切り（\n\n と \n の差）をすべて単一改行に統一

    注: 比較対象は「文字レベルの本文」であり、章間の段落幅や
    末尾改行の数は出力形式（pixiv形式）の都合で変わることがあるため、
    検証時は単一改行に正規化して比較する。
    """
    novel_dir = project_dir / "novel"

    export_body = normalize_for_diff(export_path.read_text(encoding="utf-8"))

    novel_body = ""
    for f in sorted(novel_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        text = re.sub(r"^#+\s+.+\n", "", text, count=1)
        text = re.sub(r"!\[.*?\]\([^)]+\)", "", text)
        # 独自ルビ記法も除去（export 側の pixiv ルビ除去と整合）
        text = RUBY_BRACE_RE.sub(r"\1", text)
        text = RUBY_RB_RE.sub(r"\1", text)
        novel_body += re.sub(r"\n{3,}", "\n\n", text).rstrip() + "\n"

    # 段落区切りを単一改行に統一
    export_body = re.sub(r"\n+", "\n", export_body.strip())
    novel_body = re.sub(r"\n+", "\n", novel_body.strip())
    return export_body == novel_body


def check_length(export_path: Path) -> dict:
    """文字数とプレースホルダー数を確認"""
    text = export_path.read_text(encoding="utf-8")
    body = COMMENT_RE.sub("", text)
    chars = len(body.strip())
    placeholders = re.findall(r"\[※挿絵\d+\]", body)
    return {
        "chars": chars,
        "max": PIXIV_MAX_CHARS,
        "over": chars > PIXIV_MAX_CHARS,
        "placeholders": len(placeholders),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="novel2hermes_jp pixiv小説エクスポート",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--project-dir", type=Path,
        help="novel2hermes_jp プロジェクトのルートディレクトリ",
    )
    parser.add_argument(
        "--input-dir", type=Path,
        help="個別指定: 入力ディレクトリ（novel/ の代わり）",
    )
    parser.add_argument(
        "--output", type=Path,
        help="個別指定: 出力ファイルパス",
    )
    parser.add_argument(
        "--split", action="store_true",
        help="章ごとに分割出力",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="差分検証のみ（変換しない）",
    )
    parser.add_argument(
        "--check-length", action="store_true",
        help="文字数チェックのみ（変換しない）",
    )
    parser.add_argument(
        "--version", action="version", version=f"pixiv_export.py v{__version__}",
    )

    args = parser.parse_args()

    # パス解決
    if args.project_dir:
        novel_dir = args.project_dir / "novel"
        proposal_dir = args.project_dir
        output_path = args.output or (args.project_dir / "export" / "pixiv.md")
    elif args.input_dir and args.output:
        novel_dir = args.input_dir
        proposal_dir = args.input_dir.parent
        output_path = args.output
    else:
        parser.error("--project-dir または（--input-dir と --output）が必要です")

    # 検証モード
    if args.verify:
        if not output_path.exists():
            print(f"[ERROR] 出力ファイルが存在しません: {output_path}", file=sys.stderr)
            return 1
        ok = verify_no_modification(proposal_dir, output_path)
        if ok:
            print(f"[OK] 本文変更なし: {output_path}")
            return 0
        else:
            print(f"[FAIL] 本文に差分あり: {output_path}", file=sys.stderr)
            return 1

    if args.check_length:
        if not output_path.exists():
            print(f"[ERROR] 出力ファイルが存在しません: {output_path}", file=sys.stderr)
            return 1
        result = check_length(output_path)
        status = "OVER" if result["over"] else "OK"
        print(f"[{status}] 文字数: {result['chars']:,} / {result['max']:,}")
        print(f"       挿絵プレースホルダー: {result['placeholders']} 箇所")
        return 1 if result["over"] else 0

    # 変換モード
    print(f"入力: {novel_dir}")
    print(f"出力: {output_path}")

    # 一時的に novel_dir を project_dir 配下として扱う
    if not args.project_dir and args.input_dir:
        # 個別指定の場合は load_novel_chapters 互換のパスを渡す
        import tempfile, shutil
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "novel").symlink_to(novel_dir.resolve())
            tmp_proj = tmp_path
            result = export_pixiv(tmp_proj, output_path, split=args.split)
    else:
        result = export_pixiv(args.project_dir, output_path, split=args.split)

    # 結果表示
    if result["mode"] == "split":
        print(f"\n[OK] 分割出力完了: {len(result['files'])}ファイル")
        for f in result["files"]:
            print(f"  - {f}")
    else:
        print(f"\n[OK] 出力完了: {result['output']}")
        print(f"     章数: {result['chapters']}")
        print(f"     文字数: {result['chars']:,}字")
        print(f"     挿絵プレースホルダー: {result['images']}箇所")

        if result["chars"] > PIXIV_MAX_CHARS:
            print(f"\n[WARN] 50,000字を超過。--split で分割を検討してください。", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
