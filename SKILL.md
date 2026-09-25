---
name: novel2agent-jp
description: "Use when writing Japanese novels with AI coding agents (Hermes, Claude Code, opencode, goose). File-based, agent-agnostic workflow: settings in TOML, deterministic context packs, validation scripts."
version: 0.4.7
---

# novel2agent-jp

日本語小説制作のためのエージェント非依存ワークフロースキル。

## 発火条件

日本語小説の制作・執筆・推敲を AI コーディングエージェントに依頼するとき。

## 仕組み

```
TOML（設定・プロット・キャラ・世界観）
  ↓ scripts/validate.py（機械検証）
  ↓ scripts/pack.py（文脈パック生成）
.context/chNN.md（LLM に渡す Markdown・再生成可能）
```

- 設定はすべて TOML。本文は `novel/chNN.md` にのみ書く
- フェーズ境界は停止する：proposal 承認（`proposal_status`）→ 世界観・キャラ・プロット各承認 → 企画承認（`plan_status`＋Phase A-4・A-5・C-1・MoAプロット診断）→ 章ごと確認が既定。承認なしに次へ進まない。詳細は planning §7・writing 執筆実行 8
- 属性変更はキャラ TOML の `[[versions]]`、出来事は章 TOML の `[[established]]` に一元化
- LLM の未確定事実は `status = "proposed"` で追記し、人間が `"confirmed"` に変える
- 伏線の回収実績は `[[foreshadowing]]` の `resolved_at` に一本化

## 執筆セッション開始時の固定手順

手順の本体は `references/writing-workflow.md` 冒頭。validate → pack --check → 必要なら再生成 → `.context/chNN.md` を読んで執筆。

## 参照

| ファイル | 読むとき |
|---|---|
| `schema/toml-schema.md` | TOML の必須キー・検証項目・pack.py 出力仕様 |
| `references/planning-workflow.md` | 企画フェーズ（proposal / worldbuilding / character / plot の TOML 作成手順） |
| `references/writing-workflow.md` | 執筆セッションの手順（pack 生成 → 執筆 → TOML 反映） |
| `references/revision-workflow.md` | 推敲フェーズ（Phase A/B/C + MoA 4 視点 + proposed 確定手順） |
| `references/moa-manual-orchestration.md` | 4 視点の横並び比較推敲（MoA）の実行手順。エージェント非依存（推敲で複数モデルを使うとき） |
| `references/character-template.md` | キャラ TOML の全項目テンプレートと記入例 |
| `references/toml-formatting.md` | TOML リテラルの機械整形（改行位置を AI に判断させない。TOML 修正後に読む） |
| `references/character-design-guide.md` | キャラの発想手順（欠点先行・三層・配置。テンプレを埋める前に） |
| `references/sensory-rotation.md` | 五感ローテーション（シーンごと視覚以外 2 つ以上） |
| `references/metaphor-guide.md` | 比喩の選び方（クリシェ回避・1〜2 個/シーン） |
| `references/pixiv-export.md` | pixiv投稿用変換の手順（エクスポート時に読む） |
| `references/illustration-guide.md` | 挿絵生成ワークフロー（挿絵を作るときに読む） |
| `references/vfm-to-pixiv-workflow.md` | 縦読み記法→pixiv変換の記法対比（VFMを使うときに読む） |
| `references/vfm-to-kakuyomu-workflow.md` | 縦読み記法→カクヨム変換の記法対比（カクヨム投稿時に読む） |
| `references/hermes-setup.md` | Hermes 固有の環境セットアップ（他エージェントでは不要） |

## 本文保存の鉄則（事故対策）

詳細は `references/writing-workflow.md`「執筆実行」。段落頭の全角空白禁止。保存直後に `check_prose.py`。

## Scripts

CLI の詳細は各参照先。ここは用途の索引。

| スクリプト | 用途 | 詳細 |
|---|---|---|
| `scripts/validate.py` | 設定検証（`--index` / `--log`） | `schema/toml-schema.md` §5 |
| `scripts/format_toml.py` | TOML リテラル整形（`--check` あり） | `references/toml-formatting.md` |
| `scripts/pack.py` | 文脈パック生成（`--chapter` / `--check` / `--budget`） | `schema/toml-schema.md` §6 |
| `scripts/check_prose.py` | 本文品質（空本文・全角空白・禁止語彙） | `references/writing-workflow.md` |
| `scripts/init.py` | プロジェクト雛形生成 | `references/planning-workflow.md` §0 |
| `scripts/pixiv_export.py` | pixiv 投稿用変換（レガシー `NNN-タイトル.md` も受理） | `references/pixiv-export.md` |
| `scripts/vfm_to_pixiv.py` | 縦読み記法 → pixiv タグ | `references/vfm-to-pixiv-workflow.md` |
| `scripts/vfm_to_kakuyomu.py` | 縦読み記法 → カクヨム記法 | `references/vfm-to-kakuyomu-workflow.md` |
