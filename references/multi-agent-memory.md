# マルチエージェント共有メモリ(vecmemori-plus MCP)

複数のAIエージェントから **同じ記憶** を使う運用手順。
Hermes 内ではネイティブプロバイダ(自動prefetch+LLMプランナ)、
他エージェント(opencode / goose / OpenClaw、接続テスト済み)からは
MCPサーバー経由。すべて同じ SQLite DB を指す。

```
                    ┌─ Hermes Agent ──── ネイティブプロバイダ(自動prefetch)
                    │
~/.vecmemori/memory.db ─ opencode ───── MCP (stdio)
                    │
                    ├─ goose ─────────── MCP (extensions)
                    ├─ OpenClaw ──────── MCP (mcp.servers)
                    ├─ OpenClaw / goose MCP
                    └─ すべて同じ ruri-v3-310m 埋め込み
```

---

## なぜ共有するのか(小説プロジェクトの場合)

1エージェント1DBだと、プロット検証を別エージェントでやった設定が執筆時の
Hermes に届かない。共有DBなら:

- **企画で確定したキャラ・世界観・伏線**がどのエージェントからも検索可能
- **矛盾チェック**(`fact_store` action=`contradict`)をどのエージェントでも実行
- **trust スコア**(fact_feedback)が横断的に蓄積 — 一度「確定」と評価した設定は全エージェントで優先表示
- 埋め込みモデル(ruri-v3)が1つで済む(RAM/ディスクの節約)

## ツールの使い方(全エージェント共通)

MCPツールは2つのみ。アクション駆動:

### fact_store

| アクション | 用途 | 必須引数 |
|-----------|------|---------|
| `add` | 新規記憶追加 | `content`(カテゴリ`category`/タグ`tags`推奨) |
| `search` | セマンティック検索 | `query` |
| `probe` | エンティティ全件 | `entity` |
| `related` | 関連探索 | `entity` |
| `reason` | 複数エンティティ横断 | `entities`(配列) |
| `contradict` | 陳述と類似する記憶を検出 | `statement` |
| `update` | 既存記憶の更新 | `fact_id` |
| `remove` | 削除 | `fact_id` |
| `list` | 全件一覧 | (なし) |

### fact_feedback

使った後に `helpful` / `unhelpful` を返す。trust スコアが変動し
(±0.05/−0.10)、検索順位に反映される。

### 小説執筆での実例

```
# 保存
fact_store(action="add",
  content="ヒロイン: 桜井美咲。年齢19歳。黒髪ロング。大学生。",
  category="character", tags="美咲,ヒロイン")

# 執筆前の確認
fact_store(action="probe", entity="美咲")

# 書く前に矛盾チェック
fact_store(action="contradict", statement="美咲は一人っ子である")

# 横断確認(関係性)
fact_store(action="reason", entities=["美咲", "翔太"])
```

`contradict` は**recallベースのヒューリスティック**(類似ファクトを返すだけ)。
返ってきた候補を人間またはエージェントが比較判断する。論理矛盾の自動判定ではない。

## 分散ルール(マルチエージェント運用の規約)

- **書き込みは1エージェントに寄せる**: 企画/設定の確定は Hermes(または
  任意の1つ)が行い、他エージェントは読み取り+検証中心にする。
  複数同時書き込みは重複ファクトが生まれる。
- **確定/仮設定は category で区切る**: `category=confirmed`(確定)と
  `category=draft`(仮)を分け、確定したら `update` で category を移す。
- **fact_feedback は使った側が返す**: 検索して本文に反映したら helpful、
  古かったら unhelpful。この積み重ねが検索品質になる。
- **ジャンル別の使い分け** は `references/fact-store-reference.md` を参照。

## トラブルシュート

| 症状 | 原因と対処 |
|------|-----------|
| 日本語検索が 0 件 | fugashi 未インストール → `pip install "vecmemori-plus[ja]"`。FTS専用モードは OR 展開で緩和済みだが、意味検索には埋め込みが有効 |
| 検索が当たらない | 埋め込みモデル未設定 → `VECMEMORI_EMBEDDING_MODEL` を確認。`scripts/download_model.sh` 実行 |
| サーバーが起動しない | `VECMEMORI_DB` の親ディレクトリが存在しない/権限不足。stdioログは `<DBのdir>/mcp_server.log` |
| trust が低いまま検索に出ない | `fact_feedback` で helpful を返していない。または `min_trust` を下げる |
| DB が壊れた疑い | SQLite なので `$ sqlite3 <db> ".recover"`。バックアップは `backup_paths` 参照(Hermes設定) |

## 仕様メモ

- MCPサーバー識別名: `vecmemori-plus`(クライアントUI上の表示名)
- ツールスキーマは Hermes アダプタのものと整合(probe/related/reason の
  挙動も同一方針: probe/related はエンティティ検索のエイリアス)
- `python -m vecmemori.mcp_server` で stdio 起動。HTTP(SSE)は非対応
  (必要になったら `mcp.server.mcpserver` の `run(transport=...)` を拡張)
