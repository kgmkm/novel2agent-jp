# プロジェクト初期化ガイド

Hermes Agent + vecmemori-plus で小説プロジェクトを始めるための環境セットアップ手順です。

**vecmemori-plus** は [iwaan10000vr/vecmemori](https://github.com/iwaan10000vr/vecmemori) のフォーク
([kgmkm/vecmemori-plus](https://github.com/kgmkm/vecmemori-plus))。コア設計は上流のまま、
**MCPサーバー(マルチエージェント共有メモリ)** と日本語検索改善を追加している。
import モジュール名は `vecmemori` のまま(互換)、pip パッケージ名は `vecmemori-plus`。

---

## Step 1: vecmemori-plus のクローンとインストール

```bash
cd ~
git clone https://github.com/kgmkm/vecmemori-plus.git
cd vecmemori-plus

# Hermes 用環境(ネイティブプロバイダ)に入れる場合:
uv pip install -e ".[hermes,ja]" --python ~/.hermes/hermes-agent/venv/bin/python3

# MCPサーバー用の独立環境(他エージェント共有)を作る場合:
uv venv ~/.venvs/vecmemori
uv pip install -e ".[ja]" --python ~/.venvs/vecmemori/bin/python
```

> Windows の場合: パス区切りは `C:/Users/<you>/...`。venv は `Scripts/python.exe`。

## Step 2: 日本語埋め込みモデルのダウンロード

```bash
cd ~/vecmemori-plus
bash scripts/download_model.sh
# ruri-v3-310m (768次元, ~1.2GB) が ~/.cache/vecmemori/models/ に入る
```

埋め込みなし(FTSキーワード検索のみ)で使う場合はスキップ可能。
MCPサーバーでは `VECMEMORI_FTS_ONLY=1` でモデル読み込みを回避できる。

## Step 3: Hermes プラグインのリンク(ネイティブプロバイダを使う場合のみ)

```bash
mkdir -p ~/.hermes/plugins
ln -sf ~/vecmemori-plus/src/vecmemori/hermes ~/.hermes/plugins/vecmemori
```

## Step 4: プロバイダの有効化と設定(Hermes ネイティブ)

```bash
hermes config set memory.provider vecmemori
hermes config set plugins.vecmemori.embedding_model "$HOME/.cache/vecmemori/models/ruri-v3-310m"
hermes config set plugins.vecmemori.fact_storage_language ja
hermes config set plugins.vecmemori.auto_extract false
hermes config set plugins.vecmemori.retrieval_planner false
```

## Step 5: 確認

```bash
hermes memory status
# Provider: vecmemori, Status: available
```

---

## Step 6: MCPサーバーの設定(他エージェントと記憶を共有)

Hermes 以外のエージェント(opencode / goose / OpenClaw、接続テスト済み)から
**同じ記憶DB** を参照するには、各エージェントに MCP サーバーとして登録する。

共通の環境変数:

| 変数 | 値(例) | 意味 |
|---|---|---|
| `VECMEMORI_DB` | `~/.vecmemori/memory.db` | **全エージェントで同一パスにする** |
| `VECMEMORI_FACT_LANGUAGE` | `ja` | 保存言語ガード(小説なら ja) |
| `VECMEMORI_EMBEDDING_MODEL` | `~/.cache/vecmemori/models/ruri-v3-310m` | 意味検索に必要 |
| `VECMEMORI_FTS_ONLY` | (設定しない) | `1` で埋め込み無効 |

> **Hermes と DB を共有する場合**: Hermes ネイティブプロバイダの DB
> (`$HERMES_HOME/memory_store.db`)とは**別に**共有DBを置くのが安全。
> プロファイル破損時の影響を分離できる。設定は Step 4 の
> `plugins.vecmemori.db_path` と MCP の `VECMEMORI_DB` を同じ値にする。

### opencode (`~/.config/opencode/opencode.json`)

```jsonc
{
  "mcp": {
    "vecmemori": {
      "type": "local",
      "command": ["C:/Users/<you>/.venvs/vecmemori/Scripts/python.exe", "-m", "vecmemori.mcp_server"],
      "enabled": true,
      "environment": {
        "VECMEMORI_DB": "C:/Users/<you>/.vecmemori/memory.db",
        "VECMEMORI_FACT_LANGUAGE": "ja",
        "VECMEMORI_EMBEDDING_MODEL": "C:/Users/<you>/.cache/vecmemori/models/ruri-v3-310m"
      }
    }
  }
}
```

### goose (`%APPDATA%/Block/goose/config/config.yaml`)

```yaml
GOOSE_PROVIDER: openrouter
GOOSE_MODEL: nvidia/nemotron-3.5-lightning:free
extensions:
  vecmemori:
    name: vecmemori-plus
    cmd: "C:/Users/<you>/.venvs/vecmemori/Scripts/python.exe"
    args: ["-m", "vecmemori.mcp_server"]
    enabled: true
    envs:
      VECMEMORI_DB: "C:/Users/<you>/.vecmemori/memory.db"
      VECMEMORI_FACT_LANGUAGE: "ja"
      VECMEMORI_EMBEDDING_MODEL: "C:/Users/<you>/.cache/vecmemori/models/ruri-v3-310m"
    type: stdio
    timeout: 300
```

> goose は `goose configure` の対話UIでも追加できる(CLI Extension / Standard IO)。

### OpenClaw (`~/.openclaw/openclaw.json` / `openclaw mcp add`)

```bash
openclaw mcp add vecmemori \
  --command "C:/Users/<you>/.venvs/vecmemori/Scripts/python.exe" \
  --arg "-m" --arg "vecmemori.mcp_server" \
  --env "VECMEMORI_DB=C:/Users/<you>/.vecmemori/memory.db" \
  --env "VECMEMORI_FACT_LANGUAGE=ja" \
  --env "VECMEMORI_EMBEDDING_MODEL=C:/Users/<you>/.cache/vecmemori/models/ruri-v3-310m" \
  --connect-timeout 120
```

> **`--connect-timeout 120` は必須。** デフォルト5秒では埋め込みモデルの初回ロード(~20秒以上)に
> タイムアウトする。確認は `openclaw mcp probe vecmemori`(2 tools と出ればOK)。

### 接続テスト

> **実機検証済み(2026-09-07)**: opencode 1.18 / goose 1.49 / OpenClaw 2026.9 で
> 書き込み・クロスエージェント読み取り(probe/reason)・fact_feedback(trust累積)を確認。
> プロバイダは無料モデル(opencode: mimo-v2.5-free / goose・OpenClaw: OpenRouter nemotron free)で動作。



同じ stdio コマンド(`python -m vecmemori.mcp_server`)を MCP サーバーとして登録。
goose は `goose configure`、OpenClaw は Control UI → Settings → MCP
(または config の `mcp.servers`)。

### 接続テスト

```bash
# サーバー単体の疎通(stdioで停止するまで待機すれば起動OK)
VECMEMORI_FTS_ONLY=1 python -m vecmemori.mcp_server

# E2E(リポジトリ同梱)
python tests/test_mcp_e2e.py
```

---

## Step 7: 小説執筆に必要なツールの有効化(Hermes)

小説執筆プロジェクトでは、デフォルト無効の以下のツールを有効化します。

```bash
# 動画解析（YouTube等の資料調査に使用）
hermes tools enable video

# 動画生成（小説のプロモーション動画・PV等に使用）
hermes tools enable video_gen
```

有効化後、`/reset` または新規セッション開始で反映されます。

```bash
# 有効化状態の確認
hermes tools list
```

### ツール一覧（小説プロジェクト推奨）

| ツール | 用途 |
|--------|------|
| `video` | YouTube 等の動画資料の解析・字幕抽出。時代考証や文化調査に有用 |
| `video_gen` | AI 動画生成。作品 PV・プロモーション用 |
| `web` | 時代考証・語彙検証のための web 検索（デフォルト有効） |
| `browser` | 参考資料サイトの閲覧（デフォルト有効） |
| `image_gen` | ComfyUI 連携による挿絵・表紙生成（デフォルト有効） |

> **注意**: ビルトインMoA（集約型）は小説推敲には不適です。各エージェントの独立回答を比較するため `hermes-fake-moa` を使用します（`references/moa-manual-orchestration.md` 参照）。

---

## 技術詳細

| 項目 | 値 |
|------|-----|
| メモリプロバイダ | vecmemori(モジュール) / vecmemori-plus(配布名) |
| リポジトリ | https://github.com/kgmkm/vecmemori-plus (fork of iwaan10000vr/vecmemori) |
| 検索方式 | FTS5 (0.40) + ニューラル埋め込み (0.60) |
| 埋め込みモデル | cl-nagoya/ruri-v3-310m (768次元, ~1.2GB) |
| 分かち書き | fugashi + MeCab + UniDic |
| ストレージ | SQLite（ローカル） |
| MCP | `python -m vecmemori.mcp_server`（stdio、fact_store 9アクション + fact_feedback） |
| ライセンス | MIT（上流 vecmemori、Hermes Agent holographic 由来。詳細は各リポジトリの謝辞参照） |
