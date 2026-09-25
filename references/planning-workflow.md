# 企画フェーズ

企画 → 世界観 → キャラ → プロットの順に作る。すべての構造化データは TOML に書き、本文は `novel/` にのみ書く。

## 0. プロジェクト初期化

雛形は `scripts/init.py` で生成する（手作業でのディレクトリ作成は省略ミスの元）:

```bash
python scripts/init.py --project-dir <path>
```

既存 `meta.toml` がある場合は上書きしない（エラーで停止）。生成物:

```
project/
├── proposal.md        # 企画書（Markdown のまま・雛形）
├── meta.toml          # 章の唯一の目次・雛形
├── AGENTS.md          # 文体規則・禁止事項（作品の憲法）・雛形
├── .gitignore         # .context/ を除外
├── production-log.toml # 制作ログ（追記専用。なぜ変えたか・却下した案）
├── character/         # chara-NNN.toml
├── worldbuilding/     # world-NNN.toml
├── plot/              # plot-chNN.toml
├── novel/             # chNN.md（本文のみ）
└── .context/          # pack.py 生成物（.gitignore）
```

必ずこの順で作る。スキーマの必須キーは `schema/toml-schema.md` を正とする。

## 0.5 最初に一度 validate を回す

空の `meta.toml` を作ったら、まず検証を通して雛形の形を確認する。

```bash
python scripts/validate.py --project-dir <project>
```

構造エラーはこの段階で潰す。以後、ファイルを増やすたびに随時回す。
TOML を書いた・直した後は `format_toml.py` → `validate.py` の順（形式は `references/toml-formatting.md`）。

## 1. proposal.md（Markdown のまま）

項目：タイトル（仮）／ターゲット層／ジャンル／想定プラットフォーム／長さ／あらすじ 300〜500 字／テーマ・モチーフ／登場人物一覧／章構成のアウトライン／**感情曲線**（章ごとのピーク強度・支配的感情・曲線形状）。

作成後にユーザへ全文提示し、承認を得てから次へ。数値は目安であり、シーン要求に応じて調整可。

### proposal の承認状態（必須）

`proposal.md` 冒頭に状態行を置く（YAML front matter 相当）:

```
proposal_status: proposed
```

- **`proposed` の間は TOML 進行（worldbuilding 以降）に入らない**
- 全文提示 → ユーザが明示的に承認 → `proposal_status: confirmed` に更新
- **企画書を後から変更した場合は同期チェック**: ジャンル・登場人物・舞台・関係性など変更前の要素を proposal.md 全文から検索し、古い表現を削除/書き換える（例: 当初「淡い恋愛」だったものを友情ものに変更したら、その表現が残っていないか確認する。未使用の舞台描写も同様）

感情曲線の記入例：

| 章 | ピーク強度 | 支配的感情 | 曲線形状 |
|----|-----------|-----------|---------|
| 第1章 | 40% | 緊張・抑圧 | 平坦な抑制→終盤で上昇 |
| 第2章 | 80% | 葛藤・悲しみ | 再会の衝撃(70%)→頂点(80%)→沈黙の下降 |
| 第3章 | 100% | 解放・希望 | 急上昇→カタルシス→静かな終幕 |

### 企画が定まらないときの提案材料

作りたい作品がない、または曖昧なときにだけ、次のどれかを一つ提案する。決まっているときは使わない。

- 二つの遠い素材の足し算。「もし〜だったら、しかも〜」の形で、離れた二つを組み合わせたものを企画の核にする。「さらに」で足すと説明的になるので「しかも」で足す
- テーマを後から見つける。テーマ欄を「（仮）執筆後に確定」と注記して進め、七〜八割書いた時点で「この作品の人物たちは皆〜している」という一文が浮かんだらそれをテーマとし、寄与しない場面を削る。`proposal_status` は通常どおり confirmed にしてよい（テーマの確定と企画の確定は別）
- 制約から始める。想定プラットフォーム、文字数、章数、締切、扱える題材の範囲を先に固定し、制約を起点に発想する。自由に書いてよい、が最も書きにくい
- 梗概を人に試す。ユーザに「一、二文で人に話せますか」と聞く。話した反応が薄ければ捨てる提案をする。「つまらない」と言われたら「どこが」を聞くよう促す（エージェントはユーザの代わりに反応を作らない）

## 2. 世界観（worldbuilding/world-NNN.toml）

世界設定が土台。キャラの所属・能力・服装はここから導かれるため必ず先に作る。

- 基本設定は `content` の散文（`'''`複数行リテラル）
- 構造化できる部分（組織一覧・年表等）はテーブル/配列で併用可
- **制約リスト `[[constraints]]` を必ず作る**：この世界に「存在しない語彙」「キャラの知識範囲外」を明示する。推敲フェーズ（Phase B）の照合対象になる

```toml
id = "world-001"
title = "基本設定"
kind = "core"                       # core / geography / rules / glossary
content = '''大正12年〜昭和8年の日本が舞台。魔法は存在しない。'''

[[constraints]]
kind = "forbidden_words"
words = ["スマホ", "SNS", "オッケー", "ググる"]
note = "大正〜昭和初期のため使用禁止"

[[constraints]]
kind = "unknown_to"
target = "chara-003"
words = ["化学用語", "英語"]
note = "山育ちのため知らない"
```

世界観ができたらユーザに全文提示し、承認を得てからキャラ（§3）へ。承認なしにキャラファイルを作らない。

## 3. キャラ（character/chara-NNN[-サフィックス].toml）

テンプレートは `references/character-template.md`、発想の手順は `references/character-design-guide.md`。必須キーのみスキーマが検証し、追加キーは自由。記入例はテンプレート側。ファイル名の末尾に名前を付けるとエクスプローラで見分けやすい（例：`chara-001-瀬川匠.toml`。書式は `schema/toml-schema.md` §0）。

### 3-0. 名前を先に決める

キャラを書き始める前に、全キャラの `name_ja` / `name_ruby` の候補を先に出す。

- 候補を 2〜3 ずつ出してユーザに選ばせる。名前が決まると `first_person` / `speech_style`（口調）が安定し、後の修正が減る
- 未決の間は `name_ja = "TBD 桜井"` のように書き、**TBD が残ったままプロット（§4）へ進まない**。validate が警告する
- 強い却下理由があった名前は `production-log.toml` に `kind = "reject"` で残す（同じ案を再提案しないため）

規則：

- 1 キャラ 1 ファイル。章またぎの変化（悪堕ち・所属変更）は `[[versions]]` に変更キーのみ書く。全項目の再記述はしない
- `[basic]` 配下のキー（age 等）を versions に書くと pack.py が `[basic]` に反映する（schema §1）

全キャラができたらユーザに一覧提示（`validate.py --index` の出力）し、承認を得てからプロット（§4）へ。承認なしに plot ファイルを作らない。

## 4. プロット（plot/plot-chNN[-サフィックス].toml）

1 章 1 ファイル。シーン本文は**ここに書かない**（`novel/` のみ本文）。ファイル名の末尾に副題を付けると見分けやすい（例：`plot-ch01-導入.toml`）。

```toml
id = "plot-ch01"
summary = ""                        # 執筆後に LLM が proposed で記入。summary は ID の次に置く（最頻編集のため）
summary_status = "proposed"
chapter = 1
title = "導入"
pov = "chara-001"
peak_intensity = 40                 # proposal.md の感情曲線と一致させる。機械参照が主のため後ろに置く

[[scenes]]
title = "引っ越し"
location = "臼井駅"
time = "夕方・秋"
pov = "chara-001"
characters = ["chara-001", "chara-002"]
content = '''
荷物の中から古い日記が出てくる。
美咲はページを開けず箱に戻す。
'''                                 # 演出指示。長文は §0 可読性ルール（1文1行・40字目安）で改行
emotion_peak = "静かな導入"

[[foreshadowing]]
id = "fs-001"
content = "荷物から出た古い日記"
resolve_chapter = 3                 # 回収予定章（必須）。実績は resolved_at = 3（未回収は省略）

[[established]]
content = "美咲が臼井市に引っ越した"
status = "proposed"                 # 推敲完了時に人間が confirmed へ
```

シーン雛形の必須：title / location / pov / characters / content（演出）。`time`・`emotion_peak`・キー台詞は推奨。

ルートキーは `id / summary / summary_status / chapter / title / pov / peak_intensity` の順に書く（キー順は機械の動作に影響しない。編集頻度順）。
`summary` / `content` の長文は `schema/toml-schema.md` §0 の可読性ルール（`'''` 複数行・1文1行・1行は全角40字目安、行数は無制限）で書く。LLM に summary を記入させる場合も同じ形で指示する。
改行位置の判断は LLM にさせない。書いた後は `references/toml-formatting.md` の手順（`format_toml.py` → `validate.py`）で機械的に直す。

## 5. meta.toml（章の唯一の目次）

```toml
[work]
title = "作品タイトル"
genre = "現代ファンタジー"
status = "planning"                 # planning / writing / revision / complete

[[chapters]]
number = 1
plot = "plot/plot-ch01.toml"        # validate が存在チェック
novel = "novel/ch01.md"             # 未執筆は省略
status = "draft"                    # draft / written / revised / confirmed
```

章順はこの `[[chapters]]` 記述順で決まる。ファイル名依存の探索はしない。`plot` パスはサフィックス付きの場合フル名で書く（例：`plot/plot-ch01-導入.toml`）。

## 6. AGENTS.md（作品の憲法）

文体規則・禁止事項・シリーズ注意点を 1 本にまとめる。キャラ初出時はふりがなを添える等の規則はここに。エージェント別の読込方法は `references/hermes-setup.md`。

## 7. 最終確認（企画承認ゲート）

1. `python scripts/validate.py --project-dir <project>` → エラー 0
2. `python scripts/validate.py --project-dir <project> --index` → ID↔名称の一覧が意図通り
3. ユーザに全ファイル一覧と `--index` 出力を提示し、**明示的な承認を得る**。承認があるまで `novel/chNN.md` を作らない（執筆フェーズに入らない）
4. 承認を得たら `meta.toml` の `plan_status` をユーザが `confirmed` に変更する（エージェントが自分で変えない）。`status` が writing 以降で未 confirmed は validate エラー（schema §5-18）
5. 企画段階で proposal.md の内容を変えた、または案を却下した場合、`production-log.toml` に記録したか
6. 構造診断を回したか（revision Phase A-4・A-5、C-1、MoA プロット診断）。未実施のまま承認しない。章を全部書いてから気づく事故を防ぐ

設定はすべて TOML に残る。
