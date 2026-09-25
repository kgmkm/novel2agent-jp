# Hermes 固有セットアップ

このファイルは Hermes Agent で novel2agent-jp を使うときの環境固有の話だけを扱う。
ワークフロー本体（planning / writing / revision）はエージェント非依存のため、これらのページは他エージェント（Claude Code / opencode / goose 等）でもそのまま使える。

## scripts の実行に使う Python

- スクリプトは Python 3.11+ 標準の `tomllib` のみに依存する（外部パッケージ不要）
- 任意の Python 3.11+ で動く：

```bash
python scripts/validate.py --project-dir <project>
python scripts/pack.py --project-dir <project> --chapter N
```

- Hermes に同梱の venv Python を使う場合（作者環境 Windows の例）：

```bash
env -u PYTHONHOME PYTHONPATH= \
  "C:/Users/narukami/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe" \
  scripts/validate.py --project-dir <project>
```

> Windows + Git Bash ではシステム `python` / `py` / uv 由来の Python が SRE mismatch を起こすことがある。その場合は venv Python を env 経由で呼ぶ。

## Hermes での推奨ツール

| ツール | 用途 |
|--------|------|
| `video` | YouTube 等の資料解析。時代考証・文化調査（デフォルト無効 → `hermes tools enable video`） |
| `video_gen` | 作品 PV・プロモーション動画生成（同上） |
| `web` / `browser` | 時代考証・語彙検証（デフォルト有効） |
| `image_gen` | 挿絵・表紙生成（ComfyUI 連携。デフォルト有効） |

有効化後、新規セッション開始（または `/reset`）で反映。

## 会話圧縮 / セッション検索について

- 会話圧縮: Hermes は `/compress`。エージェント別対応表は `references/revision-workflow.md` 冒頭を参照
- 過去セッション検索（`session_search`）は**本スキルのワークフローでは不要**。プロジェクトの状態は TOML ＋ `.context` がすべて保持するため、セッションを跨いでも pack 再生成だけで復元できる

## 他エージェントでの使用

- 生成物（`.context/`）が Markdown のため、どのエージェントでも同じ原稿を扱える
- `AGENTS.md`（作品の憲法）は Hermes / opencode / Codex が自動読込。Claude Code は `CLAUDE.md` に「Read AGENTS.md」の 1 行、goose は `.goosehints` に同様の 1 行を置く運用
- `skill_view` 等のスキル読込 API に依存しない。このディレクトリを参照下に置いて本文書群を読めば動作する
