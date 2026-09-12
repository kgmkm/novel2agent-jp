# ⚠️ DEPRECATED — 後継は novel2agent-jp

本リポジトリの開発は終了しました。**後継： [kgmkm/novel2agent-jp](https://github.com/kgmkm/novel2agent-jp)** へ移行してください。

## 移行理由

思想の転換（バージョンアップではなく全面転換）のため、別リポジトリとして新規公開しました。

| 旧（本リポジトリ） | 新（novel2agent-jp） |
|---|---|
| vecmemori 依存のデュアルストレージ（.md + fact_store） | TOML 一元化 + Python による決定論的コンテキスト生成 |
| Hermes Agent 専用 | エージェント非依存（Hermes / Claude Code / opencode / goose） |
| session_search によるプロジェクト復元 | pack.py 再生成で代替 |
| 1 バージョン 1 キャラ .md | `[[versions]]` に一本化 |

詳細は新リポジトリの `docs/novel2hermes-jp_アップデート計画_v2.md` に記載しています。

## 既存プロジェクトの扱い

vecmemori DB の fact は検索用に断片化しているため、自動変換ツールは提供しません。
既存プロジェクトは「手で TOML に書き直す＝設定見直し」を推奨します。`novel/`（本文 Markdown）はそのまま新構造で使えます。

## 本リポジトリについて

- 本リリース（DEPRECATED）が最終リリースです
- リポジトリは Archive（read-only）化しています。clone / fork / ZIP ダウンロードは可能です
- 旧版を参照・利用したい場合はこのままお使いいただけます（今後更新はありません）
