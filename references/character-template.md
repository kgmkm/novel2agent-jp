# キャラクター TOML テンプレート

キャラクターの解像度が小説の質と画像生成の安定性を直接決定する。仕様が曖昧なキャラは書くたびに性格がブレ、生成するたびに顔が変わる。

ルール：

- 各キャラ 1 ファイル（`character/chara-NNN[-サフィックス].toml`、id = ファイル名先頭。例：`chara-001-瀬川匠.toml`）
- **章またぎ変化は `[[versions]]` に「変更されるキーのみ」書く**
- 必須キーのみ validate が検証。追加キーは自由（toml-schema §1）
- pack に出力されるのは執筆に効くキーだけ（`height_cm` / `birthday` などは出力外）
- 決められない項目は省略ではなく、comment で事由を残す（`# 伏線のため不明` 等）

## テンプレート

```toml
id = "chara-001"                    # 必須・ファイル名先頭と一致（例: chara-001-瀬川匠.toml）
name_ja = "桜井美咲"                # 必須。固まる前は候補を先に出す（発想ガイド参照）
name_ruby = "さくらい みさき"        # 必須（初出ふりがな検証用）
role = "protagonist"                # 必須。protagonist / antagonist / support のいずれか
flaw = "頼ることが苦手で一人で抱え込む"  # lead必須・support任意・minor禁止。作中で一度は判断を誤らせる欠点
quirk = "学者なのに部屋に漫画が二冊だけある"  # 同上。「〜のとき、〜する」の条件形で書く
heat = "母の死に意味を見出したい"    # 同上。この人物が必死になる対象

[basic]                             # 必須セクション
gender = "female"                   # 必須
age = 19                            # 必須。versions で章ごとに変えられる
first_person = "私"                 # 必須（一人称検証用）
speech_style = "丁寧語"              # 推奨。口調のルール
height_cm = 158                     # 任意（pack 対象外。画像・成長管理用）
second_person = "あなた"             # 任意。誰にどの二人称かはコメントで
birthday = "3月15日"                # 任意（pack 対象外。イベント管理用）
species = "人間"                    # 任意。ファンタジーでは必須

[appearance]                        # 画像生成と執筆の両方の安定性を左右する
hair = "黒髪ロングストレート、ぱっつん前髪"
hair_color = "漆黒 #1a1a2e"
eyes = "ダークブラウン #4a3228、やや大きめ丸目"
skin = "陶器のように白い"
outfit = "白と金のロングドレス型聖女服、金糸刺繍コルセット、白レース手袋"
outfit_special = "戦闘時: 黒い戦闘服、銀の聖杖"
accessory = "銀の聖杖（最重要識別子）"    # 首から上・手持ちの装飾はキャラ識別の鍵

[personality]                       # 任意（執筆には強く効く）
keywords = ["真面目", "好奇心旺盛", "短気"]
front = "真面目で礼儀正しい"          # 表の性格
back = "実は承認欲求が強い"           # 裏の内面。自覚していない場合も
strengths = "思いやりがある"
weaknesses = "やや内向的。頼ることが苦手"

[motivation]                        # 行動原理（任意だが物語の核になるので埋めること）
core_wound = '''幼少期に母親を病気で亡くした。'''  # 2文以上になったら複数行にし、開き直後・閉じ直前に改行（toml-formatting.md）
false_belief = "努力すれば必ず報われる"   # lead必須・support任意・minor禁止。本人は正しいと信じているが物語中で崩される考え（一行）
principle = "他人を守りたい"          # 意思決定の最優先基準
goal_external = "魔法公安の捜査官になる"
desire_hidden = "母の死に意味を見出したい"   # 自覚していない欲求
fears = "再び大切な人を失うこと"      # 突かれると判断を誤る
habits = "困ると髪をいじる"
catchphrase = "……そうですか"
likes = ["苺ミルク", "雨天の図書室"]
dislikes = ["電話"]

[design]                            # 任意。作劇上の設計（発想の手順は character-design-guide.md）
screen_time = "lead"                # lead(主軸) / support(脇) / minor(端役)。他の値は validate エラー。minor に物語装置キー（flaw/quirk/heat/false_belief）を書くと警告

[[relations]]                       # 0 件以上。target は存在チェック対象
target = "chara-002"                # 必須 # 佐藤太郎
kind = "学友"                       # 関係の名前（兄弟/師弟/恋愛/敵対 等）
function = "contrast"               # 任意。作劇上の役割（contrast=対照 / outsider=部外者 等）。kind と混ぜない
call = "太郎"                       # どう呼ぶか（任意）
emotion = "信頼"                    # 好意/尊敬/恐怖/嫉妬 等
no_compromise = "謝罪がない限り和解しない"  # 任意。この関係で妥協できない理由（敵対関係では必ず書く）

[[versions]]                        # 章またぎ変化（属性変更の唯一の記録場所）
from_chapter = 3                    # 必須
to_chapter = 4                      # 任意。省略で「未来永劫」
age = 20                            # [basic] 配下キーは basic に反映される
affiliation = "魔法公安"
note = "覚醒後。制服が黒い戦闘服に"

# versions 同士の章範囲重複は validate エラー。
# 変化しないキーは書かない（ルートの値がそのまま使われる）。
```

## 埋める順番と対話の進め方

1. proposal.md の登場人物一覧から全キャラを列挙（id 採番）
2. 各キャラをユーザと対話しながら埋める。**特に appearance / personality / motivation** は、ユーザの頭にあるイメージを引き出す質問を重ねる。「たぶんこれでいいだろう」と決め打ちした箇所が、後の執筆と画像生成のブレになる
3. `[basic]` → `[appearance]` → `[personality]` → `[motivation]` → `[[relations]]` → `[[versions]]` の順に書く
4. 書けたものから随時 validate → エラー 0 を確認
5. ユーザ承認後にプロットへ進む

## 章またぎ変化の例（悪堕ちなど大変化）

```toml
# ルートは「不変の基礎」
id = "chara-001"
name_ja = "セシリア"
[basic]
first_person = "私"
speech_style = "丁寧語"

[[versions]]
from_chapter = 5
first_person = "わたくし"           # 一人称の変化も basic に反映される
outfit = "黒と紫の堕落後の法衣"
note = "堕落後。口調は丁寧だが粘着質に"
```

大変化でも 1 ファイル。`[[versions]]` の note に変化の要旨を書けば、pack.py がその章のパックに反映する（ルート＋該当 version の合成結果）。

## 記入例（高解像度の参考）

```toml
id = "chara-004"
name_ja = "セシリア"
name_ruby = "せしりあ"
role = "protagonist"

[basic]
gender = "female"
age = 19
first_person = "私"
height_cm = 162

[appearance]
skin = "陶器のように白くきめ細かい。青白いほどの透明感"
hair = "腰まで届く漆黒ロングストレート。背中に流す。眉の上で切り揃えたぱっつん前髪"
hair_color = "漆黒（参考 #1a1a2e）"
eyes = "深みのあるダークブラウン（参考 #4a3228）。やや大きめ丸目、伏せると長い睫毛が影を落とす"
face = "卵形の輪郭、すっと通った鼻筋、小さめの唇。清楚な美人"
outfit = "白と金のロングドレス型聖女服。ハイネック。腰に金糸刺繍コルセット。白レース手袋"
accessory = "銀の聖杖（最重要識別子）"
```

この解像度があると、長編で何章も跨る身体変化を一貫して描写でき、画像生成でも一貫再現できる。
