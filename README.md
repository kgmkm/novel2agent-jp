# novel2agent-jp

AIコーディングエージェントと一緒に日本語の小説を作るためのスキルです。旧 [`novel2hermes_jp`](https://github.com/kgmkm/novel2hermes_jp_archive) から改名し、設計を全面刷新したものです。

企画・執筆・推敲の全工程を、エージェントへの指示として使えます。設定はすべて人間が読めるファイルに書かれるので、AIと人間が同じものを見ながら進められます。Hermes / Claude Code / opencode / goose など、どのエージェントでも使えます。

## 特徴

- **企画 → 執筆 → 推敲** — 編集者と小説家の分業体制を再現します
- **設定はファイルで一元管理** — キャラ・世界観・プロットはすべてファイルに書きます。AIも人間も同じファイルを見るので、認識のずれが起きにくくなっています
- **章をまたいでも設定がブレません** — 成長・悪堕ち・所属変更など、キャラの変化は1人1ファイルで追跡します
- **AIの提案は人間が承認してから確定します** — AIが書いた未確定の設定が、勝手に本決まりになることはありません
- **複数 LLM による推敲** — 論理・文体・時代考証・読者視点など多角的にチェックします。異なる LLM の回答を横並びで比べるので、単一モデルの偏りを避けられます
- **高解像度キャラクターシート** — キャラ設定のブレない小説づくりのための、40項目超の詳細テンプレート。ComfyUI 等の画像生成 AI との連携も可能です
- **キャラの作り方ガイド付き** — 欠点を先に決める・名前を先に決めるなど、発想の手順から支援します
- **制作ログが残ります** — 「なぜ変えたか・何を却下したか」を記録します。後から見返せます
- **挿絵の画像生成支援** — シーン選定からプロンプト提案まで対応します。ComfyUI なら生成からチェックまで半自動で進められます
- **pixiv投稿・カクヨム投稿・縦書きEPUB/PDF出力** — 投稿用への変換と、[novel2epub-jp](https://github.com/kgmkm/novel2epub-jp) によるA6文庫判の縦書きPDF・EPUB化に対応しています
- **ジャンル不問** — ファンタジー / SF / ミステリ / 恋愛 / 青春 / 歴史 / ホラーなど、どれでも使えます

## 作例

[【小説】妖狐は、嗤う](https://note.com/kagami_kami/n/n4a2a7b9f0d38) note.com 約18,000字 4章構成（※旧 [`novel2hermes_jp`](https://github.com/kgmkm/novel2hermes_jp_archive) で制作）

```
企画・執筆・ディレクションLLM: opencode/deepseek-v4-pro
推敲LLM: opencode/mimo-v2.5-pro, opencode/glm-5.1, nous-portal/deepseek-v4-flash
挿絵画像生成ツール: ComfyUI + anima_v10
表紙画像生成ツール: hailuo + GPT-Image-2
プロンプト生成・画像推敲LLM: opencode/qwen3.6-plus
```

## 導入

### 前提

- **AI コーディングエージェント** — Hermes / Claude Code / opencode / goose など、どれか1つをご用意ください
- **Python 3.11 以降** — 同梱スクリプトの実行に使います
- **LLM プロバイダ** — エージェントに最低1つ設定してください。推敲では複数のモデルを比べるため、複数プロバイダの併用をおすすめします
- [novel2epub-jp](https://github.com/kgmkm/novel2epub-jp) — 出版時（縦書きPDF/EPUB化）に使います

### インストール

このリポジトリをエージェントのスキル置き場に配置します。

```bash
# Hermes の場合
git clone https://github.com/kgmkm/novel2agent-jp ~/.hermes/profiles/<あなた>/skills/novel2agent-jp
```

Claude Code など他のエージェントでは、各エージェントのスキル置き場に配置してください。

スキルの安全性が気になる方は、エージェントに「外部通信の有無やセキュリティ懸念など安全性の評価をしてください」と伝えてください。

## 使い方

1. エージェントを起動し、スキル `novel2agent-jp` を読み込ませます
2. 「企画から始めて」と伝えます → 企画が始まります（企画書 → 世界観 → キャラ → プロットの順に作ります）
3. 「第1章を書いて」と伝えます → 執筆が始まります
4. 「推敲して」と伝えます → 複数の視点で整合性をチェックし、読者視点で評価します

詳しくは [SKILL.md](SKILL.md) をご覧ください。

## 人類側Tips

### 世界観・キャラ・プロットは納得いくまで編集しよう

だいたい上記の順にまとめてくれますが、ここは AI にまかせっぱなしにせず、必ず人間が確認しましょう。「あれ？」「ちょっとイメージ違う」が出た場合、その場で TOML を直すか、AI に違和感を伝えて変えてもらってください。プロットが固まってから遡って世界観やキャラを直すのも全然アリです。この3つの出来が、小説の品質を決定します。ここ一番の頑張りどころなのでちゃんと読め！なおせ！

TOML を直したら、下の【最重要】の手順で Agent に報告してください。

### 【最重要】TOML（設定）を人間が修正したら、Agentに報告しよう！

設定の正しい置き場所は TOML ファイルだけです。AIはこのファイルを読み書きして執筆します。

ただし、**人間が TOML を直接編集したことを AI は自動で察知できません**。キャラの年齢を直した、世界観を補強した、プロットを変えた——などの場合は、Agent に「TOML を更新したので次の執筆に反映してください」と報告してください。Agent が内容を確認して、次の執筆に反映します。

### 作業の切れ目に長文コンテキストを圧縮しよう

話のピンポンが長くなると LLM の性能が落ちます。作業の切れ目（例：キャラ設定が終わってプロットに入る手前）に、エージェントのコンテキスト圧縮機能を使いましょう（Hermes なら `/compress`、Claude Code なら `/compact`、goose なら `/summarize` 等）。スキル側にも、切れ目で圧縮を提案するよう伝えています。

### プロット完成後は、小説を……書かずに推敲を依頼しよう！

プロットが全部できた段階で、流れ的に矛盾が発生することがよくあります。AI が書いたからという話ではなく、人類が書いてても普通に起こります。人間そんなに頭よくねえもん。なので、ここで推敲を依頼してください。プロット段階に潜むバグが見つかるかも？

### 執筆中でもプロットなおそう！

執筆中に小説から微妙な臭いを感じたら、それは LLM が悪いというより、プロット・設定・企画を疑った方がいいです。執筆の途中でも意見を挟み、プロットの修正を提案しましょう。設定側に齟齬がある場合も直してください。表記の修正など単純なものは直して報告、プロットの変更など判断が要るものは先にエージェントに相談するのがオススメです（設定同士の整合確認はエージェントの方が正確です）。

### LLM にこだわろう！

とはいえ、LLM そのものが悪いケースもあります。安さだけで選ばない方がいいです。じゃあ何を選べばいいかというと……わからねえ……

が、それをエージェントに調べさせる方法があります。「小説など文章を書くのにオススメな LLM モデルを、直近6か月のネットの反応を検索して教えて」と聞いてみてください。X を検索させるのも効果的です。

### 小説の変更履歴を覚えておきます

設定を変えたとき、「なぜ変えたか・何を却下したか」を記録に残しています。長編になると「前にこう決めたはずなのに」というブレが起きがちなので、変更の理由を後から見返せるようになっています。

読みたいときは Agent に「これまでの変更履歴を教えて」と聞いてください。特定の章やキャラに絞ることもできます（例：「第3章に関する変更だけ教えて」）。

## このリポジトリのファイル構成

```
novel2agent-jp/
├── SKILL.md                     ← メインスキル定義
├── README.md                    ← このファイル
├── LICENSE                      ← MIT
├── schema/
│   └── toml-schema.md           ← TOML スキーマ定義（必須キー・検証項目・pack.py 仕様）
├── scripts/
│   ├── validate.py              ← 設定検証（構文・必須キー・ID・参照整合・制作ログ）
│   ├── format_toml.py           ← TOML リテラル整形（改行位置の機械修正）
│   ├── pack.py                  ← 文脈パック生成（章ごとの LLM 渡し用 Markdown）
│   ├── check_prose.py           ← 本文品質検査（空本文・禁止語彙・全角空白）
│   ├── init.py                  ← プロジェクト雛形生成
│   ├── pixiv_export.py          ← pixiv 小説投稿用変換
│   ├── vfm_to_pixiv.py          ← 縦読み記法 → pixiv 変換
│   ├── vfm_to_kakuyomu.py       ← 縦読み記法 → カクヨム変換
│   └── tests/                   ← スクリプトのテスト
├── references/
│   ├── planning-workflow.md     ← 企画フェーズ（世界観→キャラ→プロット）
│   ├── writing-workflow.md      ← 執筆フェーズ（pack → 執筆 → TOML 反映）
│   ├── revision-workflow.md     ← 推敲フェーズ（Phase A/B/C + MoA 4 視点）
│   ├── moa-manual-orchestration.md ← 4 視点 MoA の実行手順（エージェント非依存）
│   ├── character-template.md    ← キャラ TOML テンプレート（40 項目超）
│   ├── toml-formatting.md       ← TOML リテラルの機械整形（修正後に読む）
│   ├── character-design-guide.md ← キャラ発想ガイド（欠点先行・名前先決め）
│   ├── metaphor-guide.md        ← 比喩ガイド（クリシェ回避）
│   ├── sensory-rotation.md      ← 五感ローテーションガイド
│   ├── pixiv-export.md          ← pixiv 投稿用変換の手順
│   ├── illustration-guide.md    ← 挿絵生成ワークフロー
│   ├── vfm-to-pixiv-workflow.md ← 縦読み記法 → pixiv ワークフロー
│   ├── vfm-to-kakuyomu-workflow.md ← 縦読み記法 → カクヨムワークフロー
│   └── hermes-setup.md          ← Hermes 固有の環境セットアップ（他エージェントでは不要）
```

## 生成される小説プロジェクトの構成（ユーザが作る側）

企画フェーズと執筆フェーズを通じて、プロジェクトディレクトリ直下に以下が生成されます：

```
my-novel-project/
├── proposal.md            ← 企画書（Markdown のまま。あらすじ・テーマ・章構成）
├── meta.toml              ← 章の唯一の目次（章番号・plot/novel パス・status）
├── AGENTS.md              ← 作品固有ガイド（文体・トーン・禁止事項・初出ふりがな規則）
├── production-log.toml    ← 制作ログ（追記専用。なぜ変えたか・却下した案）
│
├── character/             ← キャラ TOML（1キャラ1ファイル）
│   ├── chara-001.toml
│   └── chara-002.toml
│
├── worldbuilding/         ← 世界観 TOML
│   ├── world-001.toml     ← 基本設定
│   └── world-002.toml     ← 制約リスト（存在しない語彙・キャラ知識範囲外）
│
├── plot/                  ← 章ごとのプロット TOML（シーン・伏線・established）
│   ├── plot-ch01.toml
│   └── plot-ch02.toml
│
├── novel/                 ← 小説本文（Markdown。本文はここにのみ書く）
│   ├── ch01.md
│   └── ch02.md
│
└── .context/              ← エージェントが使う作業ファイル（直接編集しないでください）
    ├── ch01.md
    └── ch02.md
```

## 旧スキルからの主な変更点

- **設定の置き場所を1つにしました** — AIと人間が同じファイルを見る方式に変わりました
- **Hermes以外のエージェントでも使えます** — Claude Code / opencode / goose などに対応しました
- **設定ファイルは人間が読んで直せる形式になりました** — 執筆に必要な設定はエージェントが自動でそろえます

## 更新履歴

### v1.0（2026-09-26）
- 旧 `novel2hermes_jp` を `novel2agent-jp` に改名。TOML 設計の現行内容をそのまま本体に載せ替え（旧内容は [`novel2hermes_jp_archive`](https://github.com/kgmkm/novel2hermes_jp_archive) に保存）。star・fork・issue は引き継ぎ

### v0.4.7
- 継続行の結合＋尻尾切り防止。文末句読点なしの行は次行と結合してから折り直す（単語途中分割の解消）。文末付近で幅超過したときは早い読点で折るか、尻尾が全角10字以下にならない位置まで切り位置を戻す（数文字孤立行の解消）。tests 1件追加（全90件緑）

### v0.4.6
- 短文結合を追加。全角10字以内（表示幅20）の文は単独行にせず前後の文と同行に畳む（長文＋長文は結合しない。1文1行・git diff 粒度を保つ）。`format_toml.py` の `group_sentences` が自動処理。結合しても80字相当以内

### v0.4.5
- TOML リテラルの機械整形を新設。改行位置の判断を AI にさせず `scripts/format_toml.py` で直す方式に（複数行 `'''` は開き直後・閉じ直前に改行、1文1行・全角40字目安で折り返し。1行リテラルは触らない）。`validate.py` は形式違反を警告（§5-19）。TOML 修正後は `format_toml.py` → `validate.py` の順に回す（`references/toml-formatting.md` が正本、エージェント別対応表つき）
- mcode（MiniMax Code）の hooks 機構は公式ドキュメントに記載を確認できず。AGENTS.md への追記＋手動コマンド運用とした（確認できたら対応表を更新する）

### v0.4.4
- プロット完成→執筆の間に構造診断の固定工程を新設。revision Phase A-5 全巻構造チェック（6問）・A-6 巻き戻し手順、MoA プロット診断（§6）、planning §7 承認条件に追加。コード変更なし

### v0.4.3
- フェーズ境界の承認ゲートを新設。世界観→キャラ→プロットの各承認文（planning §2末・§3末・§7 積極承認化）＋ `meta.toml plan_status` の機械ゲート（writing 以降で未 confirmed は validate エラー §5-18）＋執筆は次章前のユーザ確認を既定に（省略は一括指示のみ。writing 執筆実行 8）
- `init.py` の雛形に `plan_status = "draft"` を追加

### v0.4.2
- 物語装置キー（flaw / quirk / heat / false_belief）の適用範囲を規定（`schema/toml-schema.md` §1）。lead 必須・support 1件まで任意・minor 禁止。違反は validate が警告（§5-17）
- pack は物語装置キーを章視点キャラと各キャラの初出章にだけ出す（他章は出さない。弱い LLM の儀式化防止）。演技情報（fears / catchphrase / habits 等）は毎章据え置き
- `quirk` は条件形（〜のとき、〜する）で書く規則を design-guide・テンプレに追加

### v0.4.1
- plot TOML の可読性ルールを新設（`schema/toml-schema.md` §0）。長文は `'''` 複数行・1文1行・1行は全角40字目安（JLReq から最小抜粋）。ルートキーの推奨順を `id / summary / summary_status / chapter / title / pov / peak_intensity` に（編集頻度順。順序違いは検証・pack とも無視）
- `validate.py` が長文の1行超過を警告（§5-16。エラーにしない）。`planning-workflow.md` §4 の例も新順序・複数行に更新
- ファイル名に人間向けサフィックスを許可（`chara-001-瀬川匠.toml`・`plot-ch01-導入.toml`。ID が正本、サフィックスは表示専用）。使用禁止文字はエラー、スペース・長さは警告

### v0.4.0
- カクヨム投稿対応 — `references/vfm-to-kakuyomu-workflow.md`（縦読み記法→カクヨム記法の対比・投稿手順）と `scripts/vfm_to_kakuyomu.py`（VFM→カクヨム変換。ルビ・傍点・場面転換・検証）を新設。pixiv 版と同構造
- SKILL.md 参照表と README ファイル構成に両ファイルを追加

### v0.3.4
- schema 節番号を詰めた（production-log を §7 に。pack 6.4–6.6 を読み順に並べ替え）
- SKILL.md から手順・CLI の再掲を外し、参照表＋契約4行に縮小。詳細は references / schema へ
- revision の MoA プロンプト全文を `moa-manual-orchestration.md` に一本化。planning のキャラ TOML 例を template へ委譲
- writing 末尾の品質基準表を執筆実行へ畳む。挿絵 §1 の pack 再掲を §3-1 に一本化。AGENTS.md 読込は hermes-setup へ。vfm の投稿 UI 手順は pixiv-export へ

### v0.3.3
- README を人間向けに改訂（敬体化・開発者用語の除去・Key Workflow 削除。エージェント向け詳細は SKILL.md に集約）
- `example/` を削除（動作確認は `scripts/tests/` の pytest に一本化）。クイックスタート節を削除

### v0.3.2
- 旧スキルから `references/pixiv-export.md`（新構造 `novel/chNN.md`・新CLI対応、Pitfall 5 を無見出し重複見出し注意に書換）と `references/illustration-guide.md`（設定取得を pack＋TOML 方式に書換）を移植
- SKILL.md 参照表に `pixiv-export.md` / `illustration-guide.md` / `vfm-to-pixiv-workflow.md` を追加（vfm行の欠落も解消）

### v0.3.1（2026-09-16）
- キャラ発想ガイド `references/character-design-guide.md` を新設。設計キー `flaw` / `quirk` / `heat` / `[design].screen_time` / `[[relations]].function`・`no_compromise` / `[motivation].false_belief` を追加
- `role` を protagonist / antagonist / support の 3 値に固定（validate が検査）。仮名（TBD）残留の警告を追加
- 制作ログ `production-log.toml` を新設（当時 schema §8。現 §7。`validate.py --log`・pack 収録）
- 推敲 Phase C を縮小（C-1 の 6 問 → C-2 キャラ点検 → C-3 感想）。MoA 視点 4 は「はい/いいえ＋根拠」必須に
- MoA 手動オーケストレーション `references/moa-manual-orchestration.md` を新設（エージェント非依存の 5 実行パターン）
- README に Key Workflow を追加。`pack.py` の versions appearance 反映バグ修正・未使用コード削除

### v0.3.0（2026-09-13）
- `check_prose.py`（本文品質検査）・`init.py`（プロジェクト雛形生成）を新設
- `pack.py --check` が章単位の鮮度チェックに対応
- `validate.py` に本文パス存在チェック・proposal 照合・proposed 警告の改善

### v0.2.0（2026-09-13）
- references 5 本を TOML 版で全面改訂、README 全面改訂・example/sample-novel 同梱
- pixiv_export / vfm_to_pixiv を新構造（`novel/chNN.md`）に対応

### v0.1.0（2026-09-13）
- 新スキル骨格（SKILL.md / README / toml-schema）
- `validate.py` / `pack.py` の実装とテスト

## 注意

### AT YOUR OWN RISK: 自己責任で導入してください。

このリポジトリのスキルをインストールしたこと、およびこのスキルを使い生成したコンテンツにより発生した問題の責任所在は、リポジトリオーナーには存在せず、このスキルの使用者に限定されます。

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE) を参照。

## 謝辞

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research
- [ruri-v3](https://huggingface.co/cl-nagoya/ruri-v3-310m) by cl-nagoya（旧スキルの design 参考）
- [葦澤かもめ](https://note.com/ashizawakamome) — 比喩表現など SKILL.md 設計の参考
- [JLREQ（日本語組版処理の要件）](https://github.com/w3c/jlreq) by W3C — 日本語組版ルールの基盤資料。詳細: [novel2epub-jp](https://github.com/kgmkm/novel2epub-jp)
