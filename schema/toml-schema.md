# novel2agent-jp TOML スキーマ定義書

## 0. 共通規則

- **文字コード**：UTF-8
- **ファイル名 = ID先頭**：ファイル名は `{ID}` または `{ID}-サフィックス.toml`。例：`chara-001-瀬川匠.toml` の `id` は `"chara-001"`。サフィックスは人間がエクスプローラで見分けるための表示専用（ID が正本。古くなっても動作に影響しない）。validator が先頭一致を強制する（§5-3）
  - サフィックスに使える文字：日本語・英数字・`_`・`-`。`\/:*?"<>|` と制御文字は不可（Windows/macOS で作れない。validate がエラーにする）
  - 半角・全角スペースは `_` にする（残っていたら警告）。長さは全角10字以内目安（超過で警告）
  - 既存のサフィックスなし名（`chara-001.toml`）もそのまま有効。移行不要
  - `meta.toml` の `plot` パス・本文 `novel/chNN.md` の命名は対象外（前者はフル名で書く。後者は pixiv-export の章順規約があるため変えない）
- **ID 命名**：`{prefix}-{3桁連番}`。prefix は `chara` / `fs` / `world`。シリーズ内で一意
- **plot 章ファイルの例外**：plot のみ章番号を ID に含む `plot-ch{2桁}.toml`（例：`plot-ch01.toml`、id も `"plot-ch01"`）。meta.toml から参照しやすくするための例外。validate.py は両形式でなくこの形式のみを検証する
- **章範囲**：`from_chapter = N`、`to_chapter = M`（整数。終端未定は `to_chapter` を省略）
- **status**：`"proposed"`（LLM提案・未確定）または `"confirmed"`（人間承認済）。省略時は confirmed 扱い。established / summary のみ使用
- **コメント**：ID 参照箇所には `# 桜井美咲` のような人間向けコメントを許可（機械は無視）
- **パーサ**：読込は `tomllib`（Python 3.11+ 標準）。書込が必要な場合のみ `tomli-w`
- **キー順序は人間が編集しやすい順にする**：TOML のキー記述順は機械の動作に影響しない（validate / pack は順序を見ない）ため、人間が編集しやすくなると判断するなら自由に入れ替えて良い。各ファイルの推奨順は §1〜§4 の例の通り
- **長文の改行（可読性ルール）**：plot の `summary` / `[[scenes]].content` / `[[foreshadowing]].content` / `[[established]].content` は `'''` 複数行リテラルで書き、次の2規則を守る（JLReq から最小抜粋。厳密な組版禁則は pack・投稿変換側の責務とし、ソースには持ち込まない）
  1. **1文1行**：`。！？…`＋閉じ括弧（`」』）〉`）の後ろで改行する。git diff が文単位になり推敲で差分が読める。ただし全角10字以内の短文は孤立行にせず前後の文と同行に畳む（機械整形が自動処理）
  2. **1行は全角40字（半角80字相当）目安**：文末なしで超える場合は読点・接続詞の前・開き括弧の前で折る。行頭に `」』）、。、？！…` を置かず、行末に `「『（［` を置かない
  - 空の `summary` だけは `summary = ""` のまま許す（未執筆のマーカー）。中身を書くときは `'''` にする
  - validate は1行超過を**警告**する（エラーにしない。§5-16）
- **リテラル形式（機械整形の対象）**：複数行の `'''` リテラルはキー不問で「開き直後・閉じ直前に改行」を付ける（1行リテラルは触らない）。AI に改行位置を判断させず `scripts/format_toml.py` で直す。詳細は `references/toml-formatting.md`（正本）

---

## 1. character（character/chara-NNN[-サフィックス].toml）

```toml
id = "chara-001"                    # 必須・ファイル名先頭と一致（例: chara-001-瀬川匠.toml）
name_ja = "桜井美咲"                # 必須。仮名の間は "TBD ……"（validate が警告）
name_ruby = "さくらい みさき"        # 必須（初出ふりがな検証用）
role = "protagonist"                # 必須。protagonist / antagonist / support のいずれか
flaw = "頼ることが苦手で一人で抱え込む"  # lead必須・support任意・minor禁止。作中で一度は判断を誤らせる欠点
quirk = "学者なのに部屋に漫画が二冊だけある"  # 同上。その人物だけのズレ。「〜のとき、〜する」の条件形で書く
heat = "母の死に意味を見出したい"    # 同上。必死になる対象（各章に一度は場面を）

[basic]                             # 必須セクション
gender = "female"
age = 19
height_cm = 158
first_person = "私"                 # 必須（一人称検証用）
speech_style = "丁寧語"

[appearance]
hair = "黒髪ロングストレート"
eyes = "ダークブラウン"
outfit = "大学の私服"

[personality]                       # 任意
keywords = ["真面目", "好奇心旺盛"]
strengths = "思いやりがある"
weaknesses = "やや内向的"

[motivation]                        # 任意（執筆に強く効く。設計は character-design-guide.md）
core_wound = '''幼少期に母親を病気で亡くし、医療文学を志す。'''
principle = "他人を守りたい"          # 意思決定の最優先基準
false_belief = "努力すれば必ず報われる"  # 本人は正しいと信じているが物語中で崩される考え

[[relations]]                       # 任意・0件以上
target = "chara-002"                # 必須・存在チェック対象 # 佐藤太郎
kind = "学友"                       # 関係の名前
function = "contrast"               # 任意・作劇上の役割（contrast / outsider 等）。kind と混ぜない
emotion = "信頼"
no_compromise = "謝罪がない限り和解しない"  # 任意・この関係で妥協できない理由（敵対関係では必ず書く）
note = "第1章で出会う"

[design]                            # 任意・作劇上の設計
screen_time = "lead"                # lead / support / minor のいずれか。他の値は validate エラー

[[versions]]                        # 任意・章またぎ変化（属性変更の唯一の記録場所）
from_chapter = 3                    # 必須
to_chapter = 4                      # 任意
age = 20                            # 変更されるキーのみ書く
affiliation = "魔法公安"
note = "覚醒後。制服が黒い戦闘服に"
```

**規則**：
- `[[versions]]` に書かれたキーは、その章範囲でルートの値を上書きする
- `[basic]` 配下のキー（`age` / `gender` / `first_person` / `speech_style` / `height_cm`）を versions で書いた場合、pack.py は `[basic]` の対応するキーに反映して出力する（例：`versions.age = 19` → 出力上は `basic.age = 19` として解決）
- versions 同士の章範囲が重複したら validate エラー
- `age` などキャラ固有の追加キーは自由（スキーマは必須キーのみ検証）
- キャラ設計の手順は `references/character-design-guide.md` を正とする（欠点 `flaw` を先に決める・名前を先に決める等）
- `role` は protagonist / antagonist / support の 3 値（validate 検査）。出番の重みは `[design].screen_time`（lead / support / minor）で表す
- 物語装置キー（`flaw` / `quirk` / `heat` / `[motivation].false_belief`）の適用範囲：**lead は必須、support は1件まで任意、minor は禁止**。minor は発想手順（design-guide）だけ使い TOML に書かない。違反は validate が警告（§5-17）。全員に書くと pack 経由で弱い LLM が毎章儀式化する
- `quirk` は「〜のとき、〜する」の条件形で書く（無条件形・頻度副詞は毎回発動と読まれる）。`flaw` は「作中で一度は判断を誤らせる」1回指定を守り、C-2 で達成確認する
- `flaw` / `quirk` / `heat` と `[design].screen_time` と `[[relations]].function` / `no_compromise` は任意キー。列挙値違い・仮名（TBD）残留は validate が検査
- pack のキャラ情報：`fears` / `catchphrase` / `habits` / `second_person` と `screen_time` は毎章出す。物語装置キー（flaw / quirk / heat / false_belief）は**章視点キャラと各キャラの初出章にだけ出す**（他章は出さない）。`height_cm` / `birthday` は出力しない（画像生成・イベント管理用のデータ）

---

## 2. worldbuilding（worldbuilding/world-NNN[-サフィックス].toml）

```toml
id = "world-001"
title = "世界観基本設定"
kind = "core"                       # core / geography / rules / glossary 等

content = '''魔法が科学と共存する現代日本。魔法は「術式」として体系化され、国家資格制度がある。'''

[[constraints]]                     # 任意・制約リスト（時代考証チェック用）
kind = "forbidden_words"            # forbidden_words / unknown_to / era
words = ["スマホ", "SNS", "コンビニ"]
note = "舞台は大正時代のため使用禁止"
target = "chara-003"                # unknown_to の場合のみ・誰の知識範囲外か
```

**規則**：
- 世界観系は `content` の散文 + 構造化可能な部分はテーブル/配列で、の併用を許可
- `[[constraints]]` は pack.py が全件コンテキストへ展開する

---

## 3. plot（plot/plot-chNN[-サフィックス].toml）

```toml
id = "plot-ch01"                    # 必須・ファイル名先頭と一致（例: plot-ch01-導入.toml）
summary = '''
美咲は窓の外を見ていた。
雨粒がガラスを伝い、遠くで雷が鳴っている。
'''                                 # 章要約。執筆後にLLMがproposedで記入。長文は§0可読性ルール（1文1行・40字目安）
summary_status = "proposed"         # summary の確定状態。summary と一体のため直後に置く
chapter = 1                         # 必須・章番号（整数）
title = "覚醒"                      # 必須
pov = "chara-001"                   # 推奨・基本視点キャラ # 桜井美咲
peak_intensity = 60                 # 任意・感情曲線のピーク(%)。機械参照が主のため後ろに置く

[[scenes]]                          # 必須・1件以上
title = "大学の廊下"                # 必須
location = "私立大学・1号館3階"      # 必須
time = "午後・雨"                   # 推奨
pov = "chara-001"                   # 必須・章povと異なる場合はこちら優先
characters = ["chara-001", "chara-002"]  # 必須・登場キャラID列
content = '''
美咲は窓の外を見ていた。
雨粒がガラスを伝い——
'''                                 # 必須・演出指示。長文は§0可読性ルールで改行
emotion_peak = "静かな導入"          # 任意

[[foreshadowing]]                   # 任意・伏線
id = "fs-001"                       # 必須
content = "太郎の机の古びた写真。裏に「M.T. 2018」の走り書き"
resolve_chapter = 3                 # 必須・回収予定章
resolved_at = 3                     # 回収済の場合の実績章。未回収は省略

[[established]]                     # 任意・この章で確定した出来事・関係変化
content = "美咲が魔法適性に覚醒した"
status = "confirmed"                # proposed / confirmed
characters = ["chara-001"]          # 関連キャラ（任意）
```

**規則**：
- ルートキーの推奨順は `id / summary / summary_status / chapter / title / pov / peak_intensity`。編集頻度順（summary を毎回触るため ID の次に）。順序違いは検証・pack とも無視する
- 長文は §0 可読性ルール（`'''` 複数行・1文1行・1行40字目安）で書く。LLM に生成させる場合もこの形を指示する（行数は無制限）
- 本文は `novel/chNN.md` にのみ書く。`scenes.content` はプロット（演出指示）であり本文の複製にしない
- 伏線の回収は `resolved_at` に一元化。established に伏線回収は書かない
- validate は `resolve_chapter` と `resolved_at` の整合（未回収のまま最終章を超えていないか等）をチェック

---

## 4. meta（meta.toml）

```toml
[work]
title = "作品タイトル"
genre = "現代ファンタジー"
status = "writing"                  # planning / writing / revision / complete
plan_status = "confirmed"           # draft / confirmed。企画承認は必ずユーザが行う（planning §7）。writing 以降で未 confirmed は validate エラー

[[chapters]]                        # 必須・章の唯一の目次。記述順が章順
number = 1                          # 必須
plot = "plot/plot-ch01.toml"        # 必須・存在チェック対象
novel = "novel/ch01.md"             # 本文ファイル。未執筆は省略
status = "draft"                    # draft / written / revised / confirmed
```

**規則**：
- 章順はファイル名ではなく本ファイルの `[[chapters]]` 記述順で決まる
- pack.py / validate.py はこの目次を起点に探索する
- `plan_status` は企画承認の機械ゲート。`draft`（init 既定）→ ユーザ承認で `confirmed`。`status` が writing / revision / complete の間に `confirmed` でなければ validate エラー。planning 中の未記入は許容（旧プロジェクト移行のため）

---

## 5. validate.py 検証項目一覧

| # | 検証 | 重要度 |
|---|------|--------|
| 1 | TOML 構文 | エラー（停止） |
| 2 | 必須キーと型 | エラー |
| 3 | ファイル名先頭 = id の一致（`{ID}-サフィックス.toml` 可） | エラー |
| 4 | ID 重複（プロジェクト全体） | エラー |
| 5 | 参照 ID の存在（relations.target / scenes.characters / pov） | エラー |
| 6 | meta.toml のファイルパス存在 | エラー |
| 7 | versions 章範囲の重複・逆転 | エラー |
| 8 | 伏線 resolve_chapter 存在・resolved_at との整合 | エラー |
| 9 | established / summary の status が proposed のまま | **警告** |
| 10 | novel 本文の禁止語彙（worldbuilding [[constraints]] と照合） | 警告 |
| 11 | 初出キャラのふりがな（本文との照合） | 警告 |
| 12 | 一人称の揺れ（本文 vs character.first_person） | 警告 |
| 13 | production-log の必須キー・kind/by 列挙値・id 形式/重複・date 形式 | エラー |
| 14 | production-log の affects 参照先の存在 | 警告 |
| 15 | character role の列挙値（protagonist / antagonist / support） | エラー |
| 16 | plot 長文（summary / scenes.content / foreshadowing.content / established.content）の1行超過（§0 可読性ルール・全角40字目安） | 警告 |
| 17 | screen_time=minor の物語装置キー（flaw / quirk / heat / false_belief）所持、support の2件以上所持（§1 適用範囲） | 警告 |
| 18 | work.status が writing / revision / complete なのに plan_status が confirmed でない（企画未承認の執筆。planning §7） | エラー |
| 19 | 複数行 `'''` リテラルの先頭・末尾に改行がない（§0 リテラル形式） | 警告 |

`validate.py --index`：全 ID と name_ja / title の対応一覧を出力。
`validate.py --log [--affects ID]`：制作ログを日付順の表で出力（§7）。

項目 10〜12 の本文検査は `scripts/check_prose.py`。planning 中（`work.status = "planning"`）の `[[chapters]]` 未記入は警告（許容）。

---

## 6. pack.py 出力仕様

入力：章番号 N。出力：`.context/chNN.md`

### 6.1 収録内容
1. meta.toml から対象章を特定
2. 登場キャラ = 対象章 scenes.characters の和集合 → 各キャラの `from_chapter ≦ N ≦ to_chapter` を満たす version で属性を解決。物語装置キー（flaw / quirk / heat / false_belief）は章視点キャラと各キャラの初出章にだけ出し、他章は出さない（§1。弱い LLM の儀式化防止）
3. worldbuilding の `[[constraints]]` 全件
4. 前章：`novel/chN-1.md` 全文。それ以前：各章の `summary`（confirmed のみ、未確定は established から代替）
5. 未回収伏線：`resolve_chapter ≦ N` かつ `resolved_at` なし
6. established：N 未満の章の全件。`status = "proposed"` は「【未確定】」を頭に付記
7. 制作ログ：§7 のエントリのうち `affects` に対象章 ID・対象章の登場キャラ ID を含む全件 + 直近 10 件。`- [date][kind] what — why の一行目` の一行

### 6.2 established のロールアップ（長編対策）
30章超で established 全件展開は budget を圧迫するため、次の規則で圧縮する。

- **直近2章分（N-1, N-2）の established は全件そのまま展開**
- **3章以上前（N-3 以前）の established は章単位で1行にロールアップ**（例：「第12章：甲野が離反、乙が負傷」）
- **`status = "proposed"` はロールアップせず全件残す**（未確定事項の取りこぼし防止）

### 6.3 budget 超過時の削り順
`--budget`（既定 100K トークン相当）超過時は、以下の順で削る。上位ほど優先的に残す。

1. 対象章メタデータ・登場キャラ（versions 解決済）— **削らない**
2. worldbuilding 制約
3. 未回収伏線 — **削らない**（§6.6 抽出漏れ禁止のため、budget 制御の対象外）
4. established（proposed 全件 → 6.2 ロールアップ後。章単位の block で落とす）
4b. 制作ログ（§7。1 block 単位で落とす）
5. それ以前の章 summary（古い章から順に落とす。章ごと 1 block）
6. 直前章本文（末尾から削る。削りきれない場合は block 丸ごと削除）

> 補足：実装上は「priority 1（対象章＋キャラ）と伏線を固定し、本文 → summary → 制作ログ → established → 制約の順で落とす」。budget に全く収まらない場合は priority 1 のみ残す。[OK/NOTE ログ](../scripts/pack.py)に削った内容を明示出力する。

### 6.4 established の budget 粒度
established は「章ごとに集約した 1 block」とする（直近2章分の全件行＋ロールアップ行を 1 block に束ねない。古い章から章単位で落とせる粒度を保つ）。

### 6.5 鮮度チェック（pack 忘れガード）
`pack.py --check`：`character/`・`worldbuilding/`・`plot/`・`novel/` の mtime が対象 `.context/chNN.md` より新しい場合に警告を出す。**`--chapter N` 付きの場合は第 N 章のパックを構成する原典だけを比較する**（対象章とそれ以前の章の plot/novel。後続章の本文更新で前章パックが誤判定されない）。章指定なしの場合は全パック一括。手順の本体は `references/writing-workflow.md` 冒頭。

### 6.6 テスト要件（P1 受け入れ条件）
pack.py は新構成における唯一の情報源（単一点）のため、以下は実装と同時にテストで担保する。

- versions の重複・逆転の解決が仕様通りであること
- 未回収伏線の抽出漏れがないこと（`resolved_at` 有無の境界）
- budget 制御（6.3 の削り順が守られること）
- established ロールアップで proposed が残ること

---

## 7. production-log（production-log.toml）

制作上の判断を記録する。作中の事実ではない（作中の事実は `[[established]]`、属性変化は `[[versions]]`）。追記専用で、過去のエントリは消さない。撤回も新しいエントリとして書く。初回の決定は書かない（proposal.md と TOML 自体が記録になる。変えた時、却下した時に書く）。

```toml
[[log]]
id = "log-004"                        # 必須・log-NNN 連番・重複不可
date = "2026-09-13"                   # 必須・YYYY-MM-DD
kind = "change"                       # 必須・change / reject / note
what = "第3章の結末を「父娘の和解」から「父が一人で焦げた飯を食べる」に変更"   # 必須・一行
why = '''元の結末は丸すぎ、proposal.md の悲観的な主題と矛盾した'''            # 必須・複数行可
affects = ["plot-ch03", "plot-ch04", "chara-001"]   # 任意・0件可。章ID / キャラID / "proposal" / "agents"
by = "human"                          # 必須・human / agent
```

**kind の意味**
- `change`: 既定の決定を変えた。proposal.md / TOML の内容を変更した時に書く
- `reject`: 検討して採用しなかった案。同じ案を後で再提案しないための記録。git には残らない情報なので、制作ログの中で最も価値が高い
- `note`: 判断ではないが残したい制作上の気づき。方針の確認など

**規則**
- `affects` に章 ID とキャラ ID を書く。proposal.md 全体に効く場合は `"proposal"`、AGENTS.md に効く場合は `"agents"`
- エージェントが書く場合は `by = "agent"`。人間の承認前でも書いてよい。人間が確認したら `by = "human"` に変える（または人間が書く）
- 参照先（affects）の存在チェックは validate が**警告**で行う（タイポで執筆を止めない）。id 形式・重複・kind/by 列挙値・date 形式はエラー
- 人間は生ファイルを通読しない。読むときは `validate.py --log` を使う
- pack.py は「対象章 / 登場キャラに関係するエントリ全件 + 直近 10 件」を収録（§6.1-7。budget 超過時は summary の次に落とされる、§6.3-4b）
