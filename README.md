# novel2hermes_jp

このスキルは後継の **[novel2agent-jp](https://github.com/kgmkm/novel2agent-jp)** へ開発を移行中です。後継は現在テスト調整中のため、**テスト完了までの間、本リポジトリは通常どおり利用できます**（アーカイブ化は行われていません）。

## 後継スキルへの移行

novel2hermes_jp は vecmemori（ベクトルメモリ）による設定同期を前提とした旧設計です。後継の novel2agent-jp は設計を全面刷新しています。

- **設定を TOML ファイルに正規化** — Markdown 二重管理・メモリ同期を廃止し、ファイルを単一情報源に
- **Python スクリプト（validate.py / pack.py）で決定論的に検証・文脈パック生成** — LLM に「探させる」のではなく「最初から全部渡す」
- **エージェント非依存** — Hermes だけでなく、Claude Code / opencode / goose など、どの AI コーディングエージェントでも利用可能

**セットアップ方法**: 以下のリポジトリをスキルとしてインストールしてください。

```
以下のGitHubリポジトリをスキルとしてインストールしてください：
https://github.com/kgmkm/novel2agent-jp
```

## このリポジトリについて

- 後継スキル novel2agent-jp のテスト完了後に、本リポジトリを **アーカイブ（read-only）** 化する予定です（時期未定）
- それまでの間は、閲覧・clone・pull・push とも通常どおり可能です
- 旧版の手順書・スクリプトはそのまま残しています
- 旧版で作成した小説プロジェクトの移行方法は、後継リポジトリのドキュメントを参照してください

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE) を参照。
