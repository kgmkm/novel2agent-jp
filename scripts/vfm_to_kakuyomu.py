#!/usr/bin/env python3
"""VFM (Vivliostyle Flavored Markdown) をカクヨム記法に変換するスクリプト。

カクヨムのエピソード本文で使える独自記法はルビ `｜漢字《るび》` と
傍点 `《《テキスト》》` の2つだけ（https://kakuyomu.jp/help/entry/notation）。
太字・斜体・見出し・画像・生HTMLは本文では機能しないため、VFM 側の記法は
テキスト化または除去して、投稿画面に貼り付け可能なプレーンテキストに落とす。

5段階の変換パイプラインを実装:
  Phase 1: プリプロセス（フロントマター・見出し・脚注）
  Phase 2: 構造変換（改ページ記号 → 場面転換マーカー）
  Phase 3: インライン変換（ルビ・傍点など）
  Phase 4: プレーンテキスト変換（サポート外形式の除去）
  Phase 5: ポストプロセス（正規化）

変換後の検証は validate_kakuyomu() が行う（親文字20字・ルビ50字の上限、
裸の山括弧、未変換ルビ記法の残留など）。警告は stderr に出るだけで
変換は止めない（原稿側で直す。Upstream Fix）。

使用法:
    python3 vfm_to_kakuyomu.py input.md [-o output.txt]

ライブラリとしての使用:
    from vfm_to_kakuyomu import convert, validate_kakuyomu
    warnings = []
    result = convert(vfm_text, warnings=warnings)
    warnings.extend(validate_kakuyomu(result))
"""

import argparse
import re
import sys
from collections import Counter

# カクヨム記法の制約（https://kakuyomu.jp/help/entry/notation）
RUBY_PARENT_MAX = 20   # 親文字は最大20文字
RUBY_TEXT_MAX = 50     # ルビ文字は最大50文字

# 改ページ記号 `===` の変換先（カクヨムには改ページがないため場面転換記号にする）
# ランキング上位作の実測で最頻だった区切り記号は ◇（109件 / 166話走査）
DEFAULT_SCENE_BREAK = '◇'

# 変換後のルビ（`｜親文字《ルビ》` と、原稿に直接書かれた `親文字《ルビ》` の両方を検出）
RUBY_ANY_RE = re.compile(r'(｜?)([^\n《》｜]{1,60}?)《([^》\n]{1,80})》')
# 傍点（中に変換済みルビ `《…》` が入る場合も許容。改行はまたがない）
EMPHASIS_DOTS_RE = re.compile(r'《《((?:[^\n《》]|《[^\n》]*》)*)》》')
# VFM の HTML 傍点（VFM に圏点記法がないため HTML 直書きされることがある）
EMPHASIS_HTML_RE = re.compile(r'<em class=["\']emphasis-dot["\']>(.+?)</em>')

# 画像プレースホルダー（pixiv_export.py と同一の書式。投稿時に人間が処理する目印）
IMAGE_PLACEHOLDER_FINAL = '[※挿絵{}]'
# 内部用: 置換中の一意なマーカー（再マッチ回避用）
IMAGE_PLACEHOLDER_TMP = '\x00IMG{}\x00'


def convert(text: str, warnings: list | None = None,
            scene_break: str = DEFAULT_SCENE_BREAK) -> str:
    """VFMテキスト全体をカクヨム記法に変換する。

    Args:
        text: VFM形式のテキスト
        warnings: 警告メッセージの追記先（None なら黙って変換する）
        scene_break: 改ページ記号 `===` の変換先（空文字なら行ごと除去）

    Returns:
        カクヨム記法に変換されたテキスト
    """
    stats: Counter = Counter()

    def note(key: str) -> None:
        stats[key] += 1

    # Phase 1: プリプロセス
    text = _remove_frontmatter(text)
    text = _convert_headings(text)
    text = _convert_footnotes(text)

    if warnings is not None and re.search(r'\{[^}\n]*\n[^}]*\}', text):
        warnings.append(
            'ルビ記法が改行をまたいでいます。カクヨムではルビが無効になります'
            '（親文字とルビを同じ行に置く）'
        )

    # Phase 2: 構造変換
    text = _convert_scene_breaks(text, scene_break)

    # Phase 3: インライン変換（順序が重要）
    text = _convert_ruby(text)
    text = _convert_emphasis_dots(text, warnings)
    text = _convert_bold(text, note)
    text = _convert_italic(text, note)
    text = _convert_links(text)
    text = _convert_autolinks(text, note)
    text = _convert_images(text, note)
    text = _convert_page_jump(text, note)

    # Phase 4: プレーンテキスト変換
    text = _remove_html_comments(text)
    text = _convert_strikethrough(text)
    text = _convert_blockquotes(text)
    text = _convert_code_blocks(text)
    text = _convert_tables(text)
    text = _convert_lists(text)

    # Phase 5: ポストプロセス
    text = _normalize_blank_lines(text)
    text = text.strip()

    if warnings is not None:
        warnings.extend(_stats_warnings(stats, text))

    return text


def extract_title(text: str) -> str:
    """原稿先頭の見出し（novel/chNN.md の `# 章タイトル`）を取り出す。

    カクヨムではエピソードタイトルを投稿画面で設定するため、変換時は
    本文から除去される。ここで取り出した文字列をタイトル欄に転記する。
    """
    m = re.search(r'^#{1,6}\s+(.+)$', text, flags=re.MULTILINE)
    return m.group(1).strip() if m else ''


# ============================================================
# Phase 1: プリプロセス
# ============================================================

def _remove_frontmatter(text: str) -> str:
    """ファイル先頭のYAMLフロントマター（---で囲まれた部分）を除去する。"""
    return re.sub(r'\A---\n.*?\n---\n', '', text, flags=re.DOTALL)


def _convert_headings(text: str) -> str:
    """見出し行を処理する。

    カクヨムのエピソード本文は見出し記法を解釈しない（`## 一` はそのまま
    文字として表示される）。また作品タイトル・エピソードタイトル・章の
    大見出し／小見出しは投稿画面で設定する。

    - 原稿先頭の見出し（`novel/chNN.md` の `# 章タイトル`）は除去する
      （投稿画面のエピソードタイトルと重複するため）
    - それ以外の見出し（`## 一` 等の節マーカー）は `#` を外して本文の
      1行として残す（節番号を落とさない）
    """
    text = re.sub(r'\A\s*#{1,6}\s+.+\n?', '', text, count=1)
    return re.sub(r'^#{1,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)


def _convert_footnotes(text: str) -> str:
    """脚注をインライン形式に変換する。

    手順:
      1. [^N]: 定義文 を収集
      2. [^N]: 定義行を除去（参照置換より先に行う）
      3. テキスト中の [^N] を （定義文） に置換
    """
    # 脚注定義を収集
    definitions = {}
    for m in re.finditer(r'^\[\^(\d+)\]:\s*(.+)$', text, flags=re.MULTILINE):
        definitions[m.group(1)] = m.group(2)

    # 脚注定義行を先に除去（参照置換で定義行内の[^N]が誤変換されるのを防ぐ）
    text = re.sub(r'^\[\^(\d+)\]:\s*.+$', '', text, flags=re.MULTILINE)

    # 脚注参照をインライン注釈に置換
    def _replace_ref(m):
        num = m.group(1)
        if num in definitions:
            return '（' + definitions[num] + '）'
        return m.group(0)  # 定義が見つからない場合はそのまま

    text = re.sub(r'\[\^(\d+)\]', _replace_ref, text)

    return text


# ============================================================
# Phase 2: 構造変換
# ============================================================

def _convert_scene_breaks(text: str, scene_break: str) -> str:
    """改ページ記号（3つ以上の=）を場面転換マーカーに変換する。

    カクヨムにはページ区切りがないので、意味を落とさず読者に伝わる形として
    1行の記号（既定 `＊`）に置き換える。連続した記号は1つに畳む。
    """
    if not scene_break:
        return re.sub(r'^={3,}$', '', text, flags=re.MULTILINE)

    text = re.sub(r'^={3,}$', scene_break, text, flags=re.MULTILINE)

    # 記号が連続する場合は1つに畳む（間に空行があっても詰める）
    esc = re.escape(scene_break)
    text = re.sub(rf'^{esc}[ \t]*\n(?:[ \t]*\n)+(?=^{esc}[ \t]*\n)',
                  '', text, flags=re.MULTILINE)
    text = re.sub(rf'^{esc}[ \t]*\n(?:{esc}[ \t]*\n)+',
                  scene_break + '\n', text, flags=re.MULTILINE)
    return text


# ============================================================
# Phase 3: インライン変換
# ============================================================

def _convert_ruby(text: str) -> str:
    """VFMルビ記法をカクヨムルビ記法に変換する。

    複合ルビ: {親文字|ルビ1|ルビ2|...}
      親文字の文字数とルビの数が一致する場合、各文字に個別にルビを振る。
    単一・グループルビ: {親文字|ルビ}
      ｜親文字《ルビ》 に変換。

    親文字の先頭に全角縦線 ｜ を必ず付ける（漢字以外を含む親文字でも
    範囲が確定するため）。既にカクヨム記法の `｜漢字《るび》` や
    `漢字《るび》` が書かれている場合はそのまま通る。
    """
    def _replace_ruby(m):
        content = m.group(1)
        parts = content.split('|')
        if len(parts) < 2:
            return m.group(0)

        parent = parts[0]
        rubies = parts[1:]

        # 複合ルビ: 親文字数とルビ数が一致する場合
        if len(parent) == len(rubies) and len(parent) > 1:
            return ''.join(f'｜{ch}《{rb}》' for ch, rb in zip(parent, rubies))

        # 単一・グループルビ
        return f'｜{parent}《{"/".join(rubies)}》'

    return re.sub(r'\{([^}]+)\}', _replace_ruby, text)


def _convert_emphasis_dots(text: str, warnings: list | None = None) -> str:
    """傍点《《テキスト》》をカクヨム記法として整える。

    - VFM原稿の `《《テキスト》》` はカクヨムの傍点記法と同一なのでそのまま残す
    - VFM の HTML 傍点 `<em class="emphasis-dot">` は `《《》》` に変換する
    - ルビと傍点の同時使用はカクヨムでは不可。傍点の中にルビがある場合は
      ルビを優先して傍点を外し、警告を出す
    """
    text = EMPHASIS_HTML_RE.sub(r'《《\1》》', text)

    def _replace_dots(m):
        inner = m.group(1)
        if '｜' in inner or '《' in inner:
            if warnings is not None:
                warnings.append(
                    'ルビと傍点は併用できません。傍点を外しました（ルビ優先）: '
                    + _clip(f'《《{inner}》》')
                )
            return inner
        return f'《《{inner}》》'

    return EMPHASIS_DOTS_RE.sub(_replace_dots, text)


def _convert_bold(text: str, note) -> str:
    """**太字** をテキスト化する（カクヨムは太字に対応しない）。"""
    def _strip(m):
        note('bold')
        return m.group(1)

    return re.sub(r'\*\*(.+?)\*\*', _strip, text)


def _convert_italic(text: str, note) -> str:
    """*斜体* をテキスト化する。
    **太字** は先に処理済みのため、単独の * にマッチする。
    """
    def _strip(m):
        note('italic')
        return m.group(1)

    return re.sub(r'\*(.+?)\*', _strip, text)


def _convert_links(text: str) -> str:
    """URLリンクを テキスト（URL） に変換する。

    カクヨムで自動リンクになるのはカクヨムのURLのみ（本文・紹介文限定、
    アプリでは未実装）。他サイトのURLはただの文字列になるため、
    リンク先が失われないようURLを括弧書きで残す。
    テキストとURLが同じ場合はURLだけ残す。
    画像記法 ![...](...) にはマッチしないよう注意する。
    """
    def _repl(m):
        label, url = m.group(1), m.group(2)
        if label.strip() == url.strip():
            return url
        return f'{label}（{url}）'

    return re.sub(
        r'(?<!!)\[([^\]]+)\]\((https?://[^)]+)\)',
        _repl,
        text,
    )


def _convert_autolinks(text: str, note) -> str:
    """GFM の自動リンク <https://...> を裸のURLに変換する。"""
    def _repl(m):
        note('autolink')
        return m.group(1)

    return re.sub(r'<(https?://[^>\s]+)>', _repl, text)


def _convert_images(text: str, note) -> str:
    """画像参照を [※挿絵N] プレースホルダーに置換する。

    カクヨムは作品ページ・エピソードページに画像を掲載できない
    （公式FAQ「小説に表紙や挿絵を入れることはできますか？」）。
    挿絵は近況ノート等で共有するため、位置の目印だけ残す。
    pixiv_export.py と同じ2段階置換（NULマーカー経由）で
    プレースホルダーの再マッチを防ぐ。
    """
    counter = [0]

    def _repl(m):
        counter[0] += 1
        note('image')
        return IMAGE_PLACEHOLDER_TMP.format(counter[0])

    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', _repl, text)
    # 内部マーカー → 最終プレースホルダーに変換
    return re.sub(r'\x00IMG(\d+)\x00',
                  lambda m: IMAGE_PLACEHOLDER_FINAL.format(m.group(1)), text)


def _convert_page_jump(text: str, note) -> str:
    """[%N]（ページジャンプ）を除去する（カクヨムに対応機能がない）。"""
    def _repl(m):
        note('page_jump')
        return ''

    return re.sub(r'\[%\d+\]', _repl, text)


# ============================================================
# Phase 4: プレーンテキスト変換（サポート外形式の除去）
# ============================================================

def _remove_html_comments(text: str) -> str:
    """HTMLコメントを除去する。

    カクヨムは生HTMLをタグとして解釈せず文字として表示するため、
    `<!-- ... -->` はそのままでは本文に露出してしまう。
    """
    return re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)


def _convert_strikethrough(text: str) -> str:
    """~~打ち消し線~~ をプレーンテキストに変換する。"""
    return re.sub(r'~~(.+?)~~', r'\1', text)


def _convert_blockquotes(text: str) -> str:
    """引用行の > プレフィックスを除去する。"""
    return re.sub(r'^>\s?', '', text, flags=re.MULTILINE)


def _convert_code_blocks(text: str) -> str:
    """コードブロック（```...```）を中身のテキストのみに変換する。"""
    return re.sub(
        r'```[^\n]*\n(.*?)```',
        r'\1',
        text,
        flags=re.DOTALL,
    )


def _convert_tables(text: str) -> str:
    """Markdownテーブル各行をスペース区切りテキストに変換する。
    区切り行（| --- | --- |）は除去する。
    """
    lines = text.split('\n')
    result = []
    for line in lines:
        # 区切り行（| --- | --- | 等）を除去
        if re.match(r'^\|[\s\-:|]+\|$', line):
            continue
        # テーブル行を変換
        if line.startswith('|') and line.endswith('|'):
            cells = [c.strip() for c in line.strip('|').split('|')]
            result.append(' '.join(cells))
        else:
            result.append(line)
    return '\n'.join(result)


def _convert_lists(text: str) -> str:
    """箇条書き・番号付きリストのマーカーを除去する。"""
    # 箇条書き: - item
    text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)
    # 番号付きリスト: 1. item
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    return text


# ============================================================
# Phase 5: ポストプロセス
# ============================================================

def _normalize_blank_lines(text: str) -> str:
    """連続する空行を最大2行に正規化する。"""
    return re.sub(r'\n{3,}', '\n\n', text)


# ============================================================
# 警告・検証
# ============================================================

def _clip(s: str, limit: int = 40) -> str:
    """警告メッセージ用に長い文字列を切り詰める。"""
    return s if len(s) <= limit else s[:limit] + '…'


def _stats_warnings(stats: Counter, text: str) -> list[str]:
    """変換で落とした要素の件数警告（1件ずつ出さない）。"""
    messages = []
    if stats['bold']:
        messages.append(
            f'太字（**…**）はカクヨムで表示できません。{stats["bold"]}箇所をテキスト化しました'
            '（強調したい箇所は傍点《《…》》への書き換えを検討）')
    if stats['italic']:
        messages.append(
            f'斜体（*…*）はカクヨムで表示できません。{stats["italic"]}箇所をテキスト化しました')
    if stats['image']:
        messages.append(
            f'画像はカクヨム本文に掲載できません。{stats["image"]}箇所を [※挿絵N] に置換しました'
            '（近況ノート等で共有し、プレースホルダーは削除）')
    if stats['page_jump']:
        messages.append(
            f'ページジャンプ [%N] はカクヨムに対応機能がありません。{stats["page_jump"]}箇所を除去しました')
    if stats['autolink']:
        messages.append(
            f'自動リンク <URL> を裸のURLに変換しました（{stats["autolink"]}箇所）。'
            '自動リンクになるのはカクヨムのURLのみ')
    if re.search(r'<[a-zA-Z/][^>\n]{0,60}>', text):
        messages.append(
            'HTMLタグが残っています。カクヨムではタグとして機能せず、文字として表示されます')
    return messages


def validate_kakuyomu(text: str) -> list[str]:
    """変換後のテキストがカクヨム記法の制約に収まっているか検証する。

    検出項目:
      1. 親文字が20文字を超えるルビ
      2. ルビ文字が50文字を超えるルビ
      3. 対応の取れない山括弧（改行をまたぐ傍点など）
      4. 未変換のルビ記法 {…|…} の残留

    Returns:
        警告メッセージのリスト（変換は止めない）
    """
    warnings: list[str] = []

    # 傍点の括弧を外して中身を検証対象に残す
    t = EMPHASIS_DOTS_RE.sub(r'\1', text)

    for m in RUBY_ANY_RE.finditer(t):
        parent, ruby = m.group(2), m.group(3)
        if len(parent) > RUBY_PARENT_MAX:
            warnings.append(
                f'ルビ親文字が{RUBY_PARENT_MAX}文字を超えています'
                f'（{len(parent)}文字）: {_clip(m.group(0))}'
            )
        if len(ruby) > RUBY_TEXT_MAX:
            warnings.append(
                f'ルビ文字が{RUBY_TEXT_MAX}文字を超えています'
                f'（{len(ruby)}文字）: {_clip(m.group(0))}'
            )

    stripped = RUBY_ANY_RE.sub('', t)
    # ｜《 は 《 をそのまま表示するカクヨムのエスケープ記法
    if re.search(r'(?<!｜)《|》', stripped):
        warnings.append(
            '対応の取れない山括弧 《 または 》 が残っています'
            '（傍点は改行をまたげません。記号を表示する場合は ｜《 と記述）'
        )

    if re.search(r'\{[^}\n]*\|[^}\n]*\}', text):
        warnings.append('未変換のルビ記法 {…|…} が残っています')

    return warnings


# ============================================================
# CLI エントリポイント
# ============================================================

def main():
    """コマンドラインインターフェース。

    使用法:
        python3 vfm_to_kakuyomu.py input.md [-o output.txt]
    """
    parser = argparse.ArgumentParser(
        description='VFM (Vivliostyle Flavored Markdown) をカクヨム記法に変換する'
    )
    parser.add_argument(
        'input',
        help='入力VFMファイルのパス'
    )
    parser.add_argument(
        '-o', '--output',
        help='出力ファイルのパス（省略時は標準出力）',
        default=None
    )
    parser.add_argument(
        '--scene-break', default=DEFAULT_SCENE_BREAK, metavar='TEXT',
        help=f'改ページ記号 === の変換先（既定: {DEFAULT_SCENE_BREAK}。空文字で除去）'
    )
    args = parser.parse_args()

    # 入力ファイルを読み込む
    with open(args.input, 'r', encoding='utf-8') as f:
        text = f.read()

    # 変換を実行
    warnings: list[str] = []
    title = extract_title(text)
    result = convert(text, warnings=warnings, scene_break=args.scene_break)
    warnings.extend(validate_kakuyomu(result))

    # 情報と警告は stderr（stdout は変換結果だけにする）
    if title:
        print(f'[INFO] エピソードタイトル候補: {title}', file=sys.stderr)
    print(f'[INFO] 文字数: {len(result):,}', file=sys.stderr)
    for w in warnings:
        print(f'[WARN] {w}', file=sys.stderr)

    # 出力
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
    else:
        sys.stdout.write(result)


if __name__ == '__main__':
    main()
