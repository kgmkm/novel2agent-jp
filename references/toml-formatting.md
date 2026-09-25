# TOML リテラル整形（機械化・正本）

AI に「50文字くらいで改行して」と頼む運用は、TOML 修正指示のたびに崩れる。
判断を AI にさせない。`scripts/format_toml.py` で直すのが正本。

## 形式規則（schema §0-3）

`'''` リテラルはキー不問で次の形に統一する。1行リテラル（改行なし）は正規形のまま触らない。

```toml
core_wound = '''
自宅の開発室で過労死した。
隣室に音が漏れない電気マッサージ器の仕様を詰めている最中だった。
'''
```

- 開き `'''` の直後は必ず改行（TOML 仕様でこの1改行は無視されるため値の先頭は変わらない）
- 閉じ `'''` の前も必ず改行（値の末尾に `\n` が1つ付く。plot 例と同形）
- 中身は1文1行・1行は全角40字（半角80字相当）目安。超える行は読点・開き括弧の前で折る。ただし全角10字以内の短文は孤立行にせず前後の文と同行に畳む。文末句読点なしの行は文の途中で折れた断片として次行と結合してから折り直す（単語途中分割・数文字の尻尾を作らない）
- `"..."` の1行もの（flaw / quirk 等の短い事実）は触らない。`'''` に変えると値に改行が混入するため、変換の要否は人間が判断する

## 使い方

```bash
python scripts/format_toml.py --project-dir <project>           # その場で直す
python scripts/format_toml.py --project-dir <project> --check   # 検査のみ（修正が必要なら exit 1）
python scripts/validate.py --project-dir <project>              # 直後に再確認（§5-19 の警告が消えること）
```

TOML を書いた・直した後は `format_toml.py` → `validate.py` の順に回す。
`validate.py` は形式違反を警告するだけ（エラーにしない）。直すのは formatter の仕事。

## エージェント別対応表

| エージェント | 自動化 | やり方 |
|---|---|---|
| Hermes | 任意 | プロジェクトの AGENTS.md に「TOML 編集後は format_toml.py → validate.py」と追記する |
| Claude Code | hooks 可 | `~/.claude/settings.json` の PostToolUse で `*.toml` 編集後に `format_toml.py --project-dir <project>` を回す（フラグは各ツールの `--help` で確認） |
| opencode / goose | 指示で代用 | hooks がなければ会話の区切り（§0.5・writing 執筆実行）に上記2コマンドを固定手順として置く |
| mcode (MiniMax Code) | 未確認・指示で代用 | 公式ドキュメントに hooks 機構の記載を確認できず（2026-09 時点）。AGENTS.md への追記＋手動コマンドで運用する。hooks の有無は `mcode --help` で確認できたら本表を更新する |

mcode に hooks がない場合の定型文（そのまま貼る）:

```
TOML を編集したら、次を実行してから報告すること:
python scripts/format_toml.py --project-dir <project>
python scripts/validate.py --project-dir <project>
```
