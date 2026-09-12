---
name: novel2hermes
description: "Use when writing Japanese novels with Hermes Agent. Covers fantasy, SF, mystery, romance, literary fiction, and all genres. Load this skill when the user mentions novel writing, character design, worldbuilding, plot planning, story continuation, or wants to continue a novel project."
version: 3.0.0
tags: [novel, writing, creative, japanese, fiction, file-based]
---

# Japanese Novel Writing Skill (Hermes Agent)

This skill provides a framework for planning and writing Japanese novels using Hermes Agent with file-based workflow.

## Quick Reference

- GitHub repo: https://github.com/kgmkm/novel2hermes_jp

## Key Workflow

1. **企画フェーズ**: proposal → worldbuilding → character design → plot
2. **プロット検証**: pre-writing consistency checks (see references/revision-workflow.md Phase A)
3. **執筆フェーズ**: write with scene template, emotion curve, five senses rotation
4. **推敲（revision）**: 整合性検証（ミクロ／Phase B）→ 読者視点評価（マクロ／Phase C）
5. **エクスポート**: 投稿プラットフォーム別の変換（pixiv等）

**フェーズ移行時および会話が長くなった際は、必ず `/compress` を提案・実行すること。**（詳細: `references/revision-workflow.md` 冒頭「コンテキスト管理」）

## 前提スキル

推敲（MoA）のモデル選択・並列実行には **`hermes-fake-moa`** が必要です。

- GitHub: https://github.com/kgmkm/hermes-fake-moa

```bash
# インストール
git clone https://github.com/kgmkm/hermes-fake-moa.git ~/.hermes/skills/hermes-fake-moa
```

`hermes-fake-moa` は複数 LLM への並列プロンプト送信を汎用化したスキル。小説以外の用途でも使えます。

## MoA Quick Reference

推敲は 4 つの異なる視点を持つ LLM による合議（Mixture of Agents）が有効。
**モデル一覧の取得・選択・並列実行は `hermes-fake-moa` を使用する。**
手動オーケストレーションの詳細は `references/moa-manual-orchestration.md` を参照。

| # | 視点 | 役割 |
|---|------|------|
| 1 | 論理整合性 | 時間軸、設定数値、因果関係、未回収伏線 |
| 2 | 文体・表現技法 | 比喩、五感、リズム、文体一貫性 |
| 3 | 時代考証・語彙 | 外来語、俗語、度量衡、学術用語 |
| 4 | 読者視点評価 | 没入感、感情曲線、余韻、テーマ深化 |

## ZIP / アーカイブ状態からの復旧

スキルが一覧に表示されていても SKILL.md が空（内容が読み込めない）場合、ZIPに圧縮されたまま展開されていない可能性がある。

```bash
# novel2hermes スキルのディレクトリを確認
ls -la "$HERMES_HOME/skills/novel2hermes/"

# ZIPが存在する場合
unzip -o "$HERMES_HOME/skills/novel2hermes.zip" -d "$HERMES_HOME/skills/novel2hermes/"

# 二重ネスト( novel2hermes/novel2hermes/ ) が発生した場合
mv "$HERMES_HOME/skills/novel2hermes/novel2hermes/"* "$HERMES_HOME/skills/novel2hermes/"
rmdir "$HERMES_HOME/skills/novel2hermes/novel2hermes/"
```

展開後は skill_view(name='novel2hermes') で再読み込みすること。参照ファイルも同様に確認する。

See `references/` subdirectory for detailed workflow guides.

### ワークフローガイド
- `project-init.md` — プロジェクトディレクトリ構造のセットアップ
- `planning-workflow.md` — 企画フェーズ（proposal / worldbuilding / character / plot）
- `writing-workflow.md` — 執筆フェーズ（正規原典の再読込 → 執筆 → メモリ更新）
- `revision-workflow.md` — 推敲フェーズ（Phase A: プロット検証 / B: 整合性検証 / C: 読者視点評価）
- `moa-manual-orchestration.md` — 4視点 LLM による MoA 推敲の手動オーケストレーション

### 表現・技法
- `character-template.md` — キャラクター設定ファイルのテンプレート
- `metaphor-guide.md` — 比喩の選び方（クリシェ回避）
- `sensory-rotation.md` — 五感ローテーション（視覚以外 2 つ以上/シーン）

### 制作・運用
- `illustration-guide.md` — 挿絵生成ワークフロー（ComfyUI 中心）
- `fact-store-reference.md` — 設定の永続化（旧 fact_store 廃止予定・履歴参照用）
- **`pixiv-export.md`** — pixiv小説へのエクスポート手順（pure conversion / メタデータ分離 / 差分検証 / 実装時の落とし穴7件）

## Scripts

### 実行環境（重要）

この環境の **Windows + Git Bash** では、システム `python` / `py` ランチャー / uv-managed `python` は **SRE mismatch** で本スキルのスクリプトを実行できない。必ず **hermes-agent venv の Python を env 経由で呼ぶ**：

```bash
env -u PYTHONHOME PYTHONPATH= \
  "C:/Users/narukami/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" \
  "C:/Users/narukami/AppData/Local/hermes/skills/novel2hermes/scripts/<script>.py" \
  --project-dir "C:/Users/narukami/Box/.../プロジェクト名"
```

`hermes-fake-moa` 等の他スキルも同様。venv パスは共通。

### `scripts/pixiv_export.py`

pixiv小説投稿用の変換スクリプト。詳細は `references/pixiv-export.md` を参照。

```bash
# プロジェクト全体の変換
python scripts/pixiv_export.py --project-dir ~/novel-project

# 章ごとに分割（50,000字超過時）
python scripts/pixiv_export.py --project-dir ~/novel-project --split

# 差分検証（本文が改変されていないか確認）
python scripts/pixiv_export.py --project-dir ~/novel-project --verify

# 文字数チェック
python scripts/pixiv_export.py --project-dir ~/novel-project --check-length

# 単一ファイル変換（novel/構造を持たない場合）
python scripts/pixiv_export.py --input 01-第一章.md 02-第二章.md
```

MoA モデル管理スクリプトは `hermes-fake-moa` スキルに集約されています。
詳細は `hermes-fake-moa` の SKILL.md を参照。
