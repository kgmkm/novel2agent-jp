# pixiv小説エクスポート（pixiv Export）

novel2hermes_jp で執筆した作品を **pixiv小説** に投稿するための標準変換手順です。

---

## 設計原則

| # | 原則 | 意味 |
|---|------|------|
| 1 | **Pure Conversion** | 本文（地の文・台詞・擬音・喘ぎ声）は改変しない。記法のみ変換する |
| 2 | **Reproducibility** | 同じソースから同じ出力を得られる（決定論的） |
| 3 | **Non-destructive** | `novel/` 配下のソースファイルを変更しない |
| 4 | **Metadata Separation** | pixiv固有のメタデータ（タイトル・あらすじ・タグ・R-18）は本文と分離する |
| 5 | **Upstream Fix** | 変換時に発生した矛盾（重複・誤字等）はソース側で修正する。変換スクリプトで隠蔽しない |

## pixiv小説の仕様制約

| 項目 | 制約 |
|------|------|
| 投稿字数 | 最大 **50,000字 / 1投稿**（超過時はシリーズ分割） |
| ルビ記法 | `｜漢字《るび》` |
| 挿絵 | pixivエディタで別途挿入（本文中はプレースホルダーのみ） |
| R-18指定 | 投稿時に pixiv 側で設定（本文に書かない） |
| 見出しレベル | `## `（h2）推奨。`# `（h1）はpixivのタイトル欄と衝突するため本文では使用しない |
| 太字 | `**テキスト**` |
| イタリック | `*テキスト*` |
| 改行 | 1行空ける（pixiv推奨） |

> **注意**: pixiv小説のマークダウン対応は2024年以降順次拡張されています。`# `（h1）が本文先頭にあると、pixiv側でタイトルとして再解釈されるケースがあるため、本文での使用は避けます。

---

## ファイル構造

```
project_root/
├── novel/                   # ソース（変換元。絶対に変更しない）
│   ├── 00-プロローグ.md
│   ├── 01-第一章_覚醒.md
│   ├── 02-第二章_変態魔女テスティ.md
│   └── ...
├── plot/                    # 既存（プロット・伏線管理）
├── character/               # 既存
├── worldbuilding/           # 既存
├── export/                  # 出力先（新規ディレクトリ）
│   └── pixiv.md             # pixiv投稿用完成版
└── scripts/
    └── pixiv_export.py      # 変換スクリプト
```

### ソースファイル名の規約

章ファイルは `{連番}-{章タイトル}.md` の形式を推奨。連番はゼロパディング2桁（`00`, `01`, `02`...）。

例：
- `00-プロローグ.md`
- `01-第一章_覚醒.md`
- `02-第二章_変態魔女テスティ.md`

連番順にソートして出力順を決定する。

---

## 変換ステップ

### Step 1: ソース読込

`novel/` 配下の `.md` ファイルを章順に読み込む。

```python
from pathlib import Path
import re

def load_novel_chapters(novel_dir: Path) -> list[dict]:
    """novel/配下の.mdファイルを章順にソートして読み込む"""
    chapters = []
    for f in sorted(novel_dir.glob("*.md")):
        m = re.match(r"^(\d+)-(.+)\.md$", f.name)
        if not m:
            continue
        order = int(m.group(1))
        raw_title = m.group(2).replace("_", "　")  # _を全角スペースに
        content = f.read_text(encoding="utf-8")
        # 本文先頭のH1/H2を章タイトルとして優先（ファイル名より優先）
        title_match = re.match(r"^#+\s+(.+)$", content.split("\n")[0])
        if title_match:
            raw_title = title_match.group(1).strip()
        # H1/H2行は本文から除去（pixivで再付与するため）
        body = re.sub(r"^#+\s+.+\n", "", content, count=1).strip()
        chapters.append({
            "order": order,
            "title": raw_title,
            "body": body,
            "filename": f.name,
        })
    return chapters
```

### Step 2: 記法変換

#### 2-1. ルビ記法

| 入力形式 | 出力形式 | 備考 |
|---------|---------|------|
| `｜漢字《るび》` | `｜漢字《るび》` | 変換不要（pixiv記法） |
| `{漢字\|るび}` | `｜漢字《るび》` | 独自記法 |
| `《るび》漢字` | `｜漢字《るび》` | JIS規格（曖昧なケースあり、注意） |
| `[[rb: 漢字 > るび]]` | `｜漢字《るび》` | 別の独自記法 |

```python
def normalize_ruby(text: str) -> str:
    # {漢字|るび} → ｜漢字《るび》
    text = re.sub(r"\{([^|}]+)\|([^}]+)\}", r"｜\1《\2》", text)
    # [[rb: 漢字 > るび]] → ｜漢字《るび》
    text = re.sub(r"\[\[rb:\s*([^>]+?)\s*>\s*([^\]]+?)\s*\]\]", r"｜\1《\2》", text)
    # 《るび》漢字 → ｜漢字《るび》（曖昧なので注意。本当に必要な箇所のみ）
    # ※自動変換は誤検知のリスクが高いため、必要なら手動で実施
    return text
```

#### 2-2. 画像プレースホルダー

| 入力形式 | 出力形式 | 備考 |
|---------|---------|------|
| `![alt](URL)` | `[※挿絵N]` | Markdown標準 |
| `![img](filename.png)` | `[※挿絵N]` | 独自記法 |
| `[[image:N]]` | `[※挿絵N]` | 独自記法 |
| `（※挿絵）` | `[※挿絵N]` | 日本語プレースホルダー |

```python
import re

def normalize_images(text: str) -> tuple[str, int]:
    """画像タグをプレースホルダーに置換。戻り値: (変換後テキスト, 挿絵数)"""
    counter = [0]
    def replacer(m):
        counter[0] += 1
        return f"[※挿絵{counter[0]}]"
    text = re.sub(r"!\[.*?\]\([^)]+\)", replacer, text)
    return text, counter[0]
```

#### 2-3. 章見出し

```python
def render_chapter(order: int, title: str, body: str) -> str:
    """章をpixiv用のh2見出し付きで出力"""
    return f"## 第{order}章　{title}\n\n{body}"
```

**重要**: サブタイトル等を **独自に追加しない**。ソースの章タイトルをそのまま使う。サブタイトルが必要な場合は **novel/ 側のファイル名または H1 を編集する**。

#### 2-4. 改行・空行の正規化

```python
def normalize_whitespace(text: str) -> str:
    """連続空行を1つに統一。末尾改行を確保"""
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.rstrip() + "\n"
```

### Step 3: ヘッダー・フッター生成

pixiv小説のタイトル・あらすじ・タグは投稿画面で別途入力する。本文中には **HTMLコメント** として「pixiv側で入力する情報」を明記するだけに留める。

#### 3-1. ヘッダー（ファイル先頭）

```html
<!--
pixiv設定メモ（投稿時に pixiv 側で入力）
==========================================
タイトル: <proposal.md の ## タイトル から取得>
あらすじ: <proposal.md の ## 概要 から取得>
R-18:    <はい / いいえ>
タグ:     <カンマ区切りで5〜10個>
文字数:   <変換後の文字数>
挿絵数:   <プレースホルダー数>
==========================================
-->
```

#### 3-2. フッター（ファイル末尾）

```html

---

<!--
変換ログ
==========================================
ソース:    <novel/*.md ファイル一覧>
章数:     <N章>
変換日時: <YYYY-MM-DD HH:MM>
変換者:    pixiv_export.py v1.0.0
==========================================
このフッターは pixiv 投稿時に削除してください。
-->
```

> **HTMLコメントを使う理由**: pixiv小説のMarkdownレンダラはHTMLコメントを無視するため、本文には表示されないが、編集中の目印・投稿者への引き継ぎメモとして機能する。

### Step 4: 出力

```python
def export_pixiv(project_dir: Path, output_path: Path) -> dict:
    """プロジェクトディレクトリを受け取り、export/pixiv.md を生成"""
    novel_dir = project_dir / "novel"
    proposal = project_dir / "proposal.md"

    chapters = load_novel_chapters(novel_dir)

    parts = []
    total_chars = 0
    total_images = 0
    for ch in chapters:
        ch["body"], n = normalize_images(ch["body"])
        ch["body"] = normalize_ruby(ch["body"])
        ch["body"] = normalize_whitespace(ch["body"])
        total_images += n
        total_chars += len(ch["body"])
        parts.append(render_chapter(ch["order"], ch["title"], ch["body"]))

    metadata = build_metadata(proposal, len(chapters), total_chars, total_images)
    body_text = "\n\n".join(parts)

    output = f"{metadata['header']}\n\n{body_text}\n{metadata['footer']}\n"
    output_path.write_text(output, encoding="utf-8")
    return {
        "chapters": len(chapters),
        "chars": total_chars,
        "images": total_images,
        "output": str(output_path),
    }
```

---

## 変換チェックリスト

実装したスクリプトで変換後、以下を必ず確認する：

- [ ] **本文差分なし** — `diff <(normalize novel/00-*.md) <(normalize export/pixiv.md から章部分のみ抽出)` で本文が同一か検証
- [ ] **ルビ統一** — `grep -E "\{[^|}]*\|" export/pixiv.md` が 0 件
- [ ] **画像プレースホルダー** — `grep -c "※挿絵" export/pixiv.md` が期待値と一致
- [ ] **章見出し連番** — `grep -E "^## 第[0-9]+章" export/pixiv.md` が章数と一致
- [ ] **字数制限** — `wc -m export/pixiv.md` が 50,000 字以内（コメント除く）
- [ ] **H1不在** — `grep -E "^# [^#]" export/pixiv.md` が 0 件（H1はpixivタイトルと衝突するため）

### 差分検証スクリプト例

```python
import subprocess
from pathlib import Path

def verify_no_modification(project_dir: Path, export_path: Path) -> bool:
    """novel/本文とexport/pixiv.mdの本文部分が完全一致するか検証"""
    novel_dir = project_dir / "novel"

    # exportから章本文を抽出（コメント・見出しを除去）
    export_text = export_path.read_text(encoding="utf-8")
    export_body = re.sub(r"<!--.*?-->", "", export_text, flags=re.DOTALL)
    export_body = re.sub(r"^## .+\n", "", export_body, flags=re.MULTILINE)
    # 画像プレースホルダーを元に戻す
    export_body = re.sub(r"\[※挿絵\d+\]", "", export_body)
    # ルビを逆変換
    export_body = re.sub(r"｜([^《]+)《([^》]+)》", r"\1", export_body)
    export_body = normalize_whitespace(export_body)

    # novel配下の結合
    novel_body = ""
    for f in sorted(novel_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        text = re.sub(r"^#+\s+.+\n", "", text, count=1)
        text = re.sub(r"!\[.*?\]\([^)]+\)", "", text)
        novel_body += normalize_whitespace(text)

    return normalize_whitespace(export_body) == novel_body
```

---

## pixiv投稿時の追加作業

1. **タイトル・あらすじ** — 投稿画面で `<!-- pixiv設定メモ -->` の内容を転記
2. **R-18設定** — R-18タグと年齢確認をチェック
3. **タグ設定** — 5〜10個を推奨：
   - **必須タグ**: 作品内容を直接表すもの（ジャンル・カップリング・舞台等）
   - **集客タグ**: 検索されやすいキーワード
   - **R-18タグ**: pixiv公式の R-18 用タグ体系に従う
4. **挿絵のアップロード** — `[※挿絵N]` の位置に pixiv エディタで画像をアップロード
5. **フッター削除** — ファイル末尾の `<!-- 変換ログ -->` を削除
6. **プレビュー** — スマホ・PC両方の表示で確認

### 推奨タグ例（エロライトノベル）

```
#ふたなり  #女体化  #魔女  #淫堕ち  #変態  #百合
#催淫  #調教  #洗脳  #TSF  #おねショタ
#おっぱい  #爆乳  #母乳  #アナル  #フェラ
#中出し  #顔射  #足コキ  #髪コキ
```

タグ選定は作品内容と照らし合わせて手動で。自動選定はしない（誤検知リスクが高い）。

---

## シリーズ投稿への拡張

50,000字を超える場合は章単位で分割投稿する：

1. 変換スクリプトに `--split` フラグを追加（章ごとにファイル分割）
2. 出力例：
   ```
   export/
   ├── pixiv_01.md   # 第一話
   ├── pixiv_02.md   # 第二話
   └── ...
   ```
3. 各ファイルに「シリーズ第N話」ヘッダーを付与
4. タイトル・あらすじは第1話に集約、シリーズ機能を活用

---

## エラーハンドリング

| 状況 | 対応 |
|------|------|
| 50,000字超過 | 警告。`--force` で続行可、デフォルトでは分割を提案 |
| 章ファイルに H1/H2 がない | ファイル名を章タイトルに使用。警告ログ |
| ルビ記法の混在（複数形式が同一ファイル内） | すべて pixiv 記法に統一。混在箇所をログ出力 |
| 画像プレースホルダーが極端に多い（章あたり 20+） | 警告。pixivの1投稿あたり推奨は10枚以下 |
| `novel/` ディレクトリが存在しない | エラー終了。プロジェクト構造を確認 |
| ソースファイルが 0 件 | エラー終了。`novel/00-*.md` があるか確認 |

---

## 関連スキル / リファレンス

- **ComfyUI連携**: 挿絵の自動生成には `comfyui` スキル（`../creative/comfyui/`）
- **イラストガイド**: `illustration-guide.md` — シーン別プロンプト作成
- **プロジェクト初期化**: `project-init.md` — ディレクトリ構造のセットアップ
- **執筆フェーズ**: `writing-workflow.md` — ソース `novel/*.md` の作成手順
- **推敲**: `revision-workflow.md` — pixiv投稿前の最終チェックリストとして流用可

## 実行スクリプト

実装は `scripts/pixiv_export.py` を参照。コマンド例：

```bash
# 単一プロジェクトの変換
python scripts/pixiv_export.py --project-dir ~/novel-project

# 章ごとに分割
python scripts/pixiv_export.py --project-dir ~/novel-project --split

# 差分検証のみ
python scripts/pixiv_export.py --project-dir ~/novel-project --verify

# 文字数チェックのみ
python scripts/pixiv_export.py --project-dir ~/novel-project --check-length
```

---

## 実装時の落とし穴（Pitfalls）

`pixiv_export.py` を改造・再実装する際に **実際に踏んだ7つのバグ** を記録する。次のセッションで同じ罠を踏まないために：

### Pitfall 1: 画像プレースホルダーの再マッチバグ

```python
# ❌ NG: re.sub を二回呼ぶとプレースホルダーがマッチされる
text = re.sub(r"!\[.*?\]\([^)]+\)", "[※挿絵N]", text)
text = re.sub(r"!\[.*?\]\([^)]+\)", "[※挿絵N]", text)  # ← 既に置換済みなので空振り or 過剰

# ❌ NG: 後段で挿絵番号を再カウントすると番号がずれる
images_after = re.findall(r"\[※挿絵(\d+)\]", text)  # ← これが偽陽性

# ✅ OK: 内部マーカーで一度切り出し、出力時に [※挿絵N] に再変換
INTERNAL_MARKER = "\x00IMG{}\x00"  # NUL文字を含むので本文と衝突しない
placeholders = []
def replacer(m):
    placeholders.append(m.group(0))
    return INTERNAL_MARKER.format(len(placeholders))
text = re.sub(r"!\[.*?\]\([^)]+\)", replacer, text)
# ... 他の変換処理 ...
# 最後に: text = text.replace(INTERNAL_MARKER, ...) でプレースホルダー化
```

### Pitfall 2: 段落区切りの正規化忘れ

novel/*.md 内の `---`（HR）や `## ` 見出しが変換で除去されると、直前段落の末尾改行が孤立して「段落間に意図しない空行が2行」になる。`--verify` で差分が出続ける原因第一位。

```python
# ✅ OK: 全変換後に段落区切りを単一改行に統一
def normalize_paragraphs(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.rstrip() + "\n"
```

### Pitfall 3: novel/*.md 側に独自ルビ記法が残っている

変換スクリプトは `{漢字|るび}` → `｜漢字《るび》` を処理するが、**novel/*.md 側で既に pixiv 記法のルビを混入しているケース**がある。`--verify` が「独自記法がないこと」をチェックするなら、**両方** を正規化して比較する必要がある。

```python
# ✅ OK: 比較時は両方を「親文字」に逆変換
def normalize_for_diff(text: str) -> str:
    text = re.sub(r"｜([^《]+)《([^》]+)》", r"\1", text)  # pixiv
    text = re.sub(r"\{([^|}]+)\|([^}]+)\}", r"\1", text)  # 独自
    text = re.sub(r"\[\[rb:\s*([^>]+?)\s*>\s*([^\]]+?)\s*\]\]", r"\1", text)  # 別形式
    return text
```

### Pitfall 4: 末尾 HR（`---`）の除去忘れ

変換後のファイル末尾に `---` が残っていると pixiv プレビューで「水平線」が1本余計に表示される。スクリプトのフッター組み立てで `---` を使う場合、本文側の `---` を全て除去する：

```python
HR_RE = re.compile(r"^\s*---\s*$", re.MULTILINE)
text = HR_RE.sub("", text)
```

### Pitfall 5: 章番号付与とファイル名連番の不一致

ファイル名が `00-プロローグ.md` の場合、出力の見出しは `## 第0章　プロローグ` となる（0始まり）。これに抵抗がある場合、`--zero-based` フラグで制御可能にする。**デフォルト動作を `proposal.md` または `pixiv-export.md` 設計書で明示する**こと（実装と運用の不整合が頻発する）。

### Pitfall 6: 挿絵カウントの「ずれ」

プロローグに挿絵があるのに、章ファイル名 `00-プロローグ.md` の本文に画像タグがない場合、プレースホルダーが期待より1〜2個少なくなる。**画像挿入位置を必ず本文に記載する**（`<!-- 挿絵: まこが図書室で本を見つけるシーン -->` 等）か、章ごとに「想定挿絵数」を `proposal.md` に明記して変換後に差分チェックする。

### Pitfall 7（環境）: `rm -rf` を含む cleanup コマンド

テスト用の一時ディレクトリを `rm -rf` で消そうとすると、git-bash 環境では **確認プロンプトで timed out → blocked** になる場合がある。テストディレクトリは残置しても害がない（`%TEMP%` 配下）ことが多いため、無理に消さず次回に持ち越す方が安全。

---

## 関連スキル / リファレンス（再掲）
