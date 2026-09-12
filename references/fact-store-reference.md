# vecmemori-plus 操作リファレンス（fact_store）

> ツールは Hermes ネイティブプロバイダでも MCPサーバー経由でも同一。
> マルチエージェント共有の運用規約は [multi-agent-memory.md](multi-agent-memory.md)。

## 保存

```python
fact_store(action="add",
    content="ヒロイン: 桜井美咲。年齢19歳。身長158cm。黒髪ロングストレート。大学生。性格は真面目で思いやりがあるが内面は好奇心旺盛。一人称「私」。口調は丁寧語。",
    category="character", tags="character,ヒロイン,美咲")

fact_store(action="add",
    content="世界観: 舞台は近未来の東京。2045年、第三次世界大戦後の復興都市。AIが社会インフラを管理。",
    category="worldbuilding", tags="world,設定,近未来,東京")
```

## 検索

```python
fact_store(action="search", query="翔太のトラウマについて")   # セマンティック検索
fact_store(action="probe", entity="桜井美咲")                # エンティティ全件
fact_store(action="related", entity="桜井美咲")              # 関連探索
fact_store(action="reason", entities=["桜井美咲", "佐藤翔太"])  # 横断検索
fact_store(action="list")                                    # 全件一覧
fact_store(action="contradict", statement="美咲は一人っ子である")  # 矛盾検出
```

## 確度管理

```python
fact_feedback(action="helpful", fact_id=1)      # 確定設定 → trust +0.05
fact_feedback(action="unhelpful", fact_id=2)     # 仮設定/古い → trust -0.10
```

> 使った事実に必ずフィードバックを返すこと。trust スコアが検索順位に反映され、
> 共有DBでは全エージェントのフィードバックが蓄積される。

## 全アクション

| アクション | 用途 | 小説での活用 |
|-----------|------|-------------|
| add | 新規記憶追加 | 新キャラ・設定・伏線の登録 |
| search | 日本語セマンティック検索 | 自然文で検索 |
| probe | エンティティ全件取得 | キャラの全情報を一括確認 |
| related | エンティティ関連探索 | 関連キャラを横断検索 |
| reason | 複数エンティティ横断 | AとBの関係性を検索 |
| contradict | 陳述と類似する記憶を検出 | 書く前に「断定前チェック」。返った候補を人間/エージェントが比較判断（recallベースのヒューリスティック） |
| update | 既存記憶更新 | 設定変更の反映 |
| remove | 記憶削除 | 没設定の削除 |
| list | 全件一覧 | 全体の棚卸し |
| fact_feedback | 信頼スコア | 確定/仮設定の区別 |
