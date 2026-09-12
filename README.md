# novel2hermes_jp（開発終了 / DEPRECATED）

このスキルは **開発終了** しました。後継は **[novel2agent-jp](https://github.com/kgmkm/novel2agent-jp)** です。

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

- 本リポジトリは開発終了に伴い **アーカイブ（read-only）** 化されています。閲覧・clone・pull・fork は引き続き可能です
- 旧版の手順書・スクリプトは履歴として残していますが、今後メンテナンスは行われません
- 旧版で作成した小説プロジェクトの移行方法は、後継リポジトリのドキュメントを参照してください

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE) を参照。
