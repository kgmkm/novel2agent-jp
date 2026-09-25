# 挿絵生成ガイド（Illustration Guide）

小説完成後の挿絵・イメージビジュアル生成ワークフロー。画像生成ツールは問わない（ComfyUI 中心、代替ツール対応）。

本手順はエージェント非依存。設定の取得は `pack.py` の文脈パック＋TOMLで行う。

---

## 1. シーン選定（小説完成後）

本文・プロットを読み返し、**印象的なシーンを 5〜10 点列挙**する。選定基準:

- 感情曲線の山（クライマックス、決断の瞬間。`proposal.md` の感情曲線と照合）
- 読者の記憶に残るビジュアルがある場面
- 物語の転換点（出会い、別れ、覚醒、敗北）
- 各章から最低 1 シーン

一次資料は対象章の `.context/chNN.md`（集め方は §3-1）。ユーザに候補を提示し、採用シーンを確定する。

---

## 2. 画像生成ツールの確認

ユーザに以下の順で確認する:

### 2-1. ComfyUI を使えるか？

```
「画像生成に ComfyUI をお使いですか？
  1. インストール済み（ローカル / API 経由）
  2. 使っていない」
```

**使っていない場合**: 代替ツールを提案:

- **GPT Image** (OpenAI): シンプルなプロンプトで高品質
- **Nano Banana** (Google): 無料枠あり、日本語プロンプト対応
- **FAL / Replicate**: API 経由で様々なモデル利用可能

この場合、代替ツール用に**シーン別プロンプト表**を作成し（後述 3-3）、ユーザが手動で投入できるようにする。

### 2-2. ComfyUI ユーザの場合: ワークフロー確認

ユーザが ComfyUI をインストール済みの場合:

```
「普段お使いのワークフロー（workflow.json）はありますか？
  もしあれば、ComfyUI メニュー > Workflow > Export で
  JSON ファイルをエクスポートして、パスを教えてください。
  なければ、公式デフォルトワークフローを使います。」
```

ワークフロー JSON を入手後、API 投入形式を解析:

- Prompt ノードの ID と入力 `prompt` フィールドを特定
- KSampler の `latent_image` 接続を確認（EmptyLatentImage or VAEEncode）
- 画像サイズ（例: 832×1216 縦長）

> **ComfyUI API 送信形式の注意点**: `/prompt` エンドポイントには `{"prompt": workflow_dict, "client_id": "..."}` 形式が必要。workflow だけを生で送ると `400 Bad Request: no_prompt` になる。

### 2-3. 品質向上プロンプトの確認

```
「普段使っている品質向上プロンプト（クオリティアッププロンプト）はありますか？
  ComfyUI ワークフローに組み込まれている場合は、そのまま使ってよいですか？
  なければ、こちらで提案します。」
```

ユーザが持っている場合: そのプロンプト文字列を抽出し、変数 `quality_prefix` として全シーン共通で使用。

ユーザが持っていない場合: 以下を提案:

```
masterpiece, best quality, good quality, awesome top artist,
score_9, anime screencap, anime style, 8K high resolution detailed,
subtle ambient glow, global illumination
```

### 2-4. 共通設定の確定

ユーザと以下の設定を合意:

| 項目 | デフォルト値 | 備考 |
|------|------------|------|
| 画像サイズ | 832×1216 (縦長) | ワークフロー依存 |
| サンプラー | lcm / 6 steps | 同上 |
| CFG | 1.0 | 同上 |
| ネガティブプロンプト | `worst quality, low quality, ...` | 要確認・調整 |
| 生成ツール | ComfyUI / GPT-Image / Nano Banana | 2-1 で決定 |

---

## 3. シーン別プロンプト作成

### 3-1. 設定・プロット・本文の収集

各シーンのプロンプトを作る前に、関連情報をパック＋TOMLから集める:

```bash
# 1. 対象章のパック（キャラ・世界観制約・伏線・established・制作ログが一束）
python scripts/pack.py --project-dir <project> --chapter N
# → .context/chNN.md を読む

# 2. 本文の該当箇所（演出の原文確認）
# → novel/chNN.md の該当シーンを読む

# 3. 外見の厳密な指定が必要な場合のみ、キャラTOMLの [appearance] を読む
# → character/chara-NNN.toml（packに出るのは執筆に効くキーのみ。髪色コード等はTOML原文を参照）
```

プロットの演出指示は章 TOML の `scenes[].content`（本文ではない）。`scenes.content` は演出指示であり本文の複製にしない（schema/toml-schema.md §3 の規則）。

> **古いパックに注意**: TOML を更新した後は `pack.py` を再生成してからプロンプトを作る。古いパックは古い外見のまま画像を量産させる。

### 3-2. プロンプト設計方針

シーンの性質に応じて **2 方向のアプローチ** を切り替える:

#### タイプ A: 情景重視（背景・空気感を重視）

- **適用**: 旅立ち、風景描写が重要なシーン、静かな余韻の場面
- **要素**: `場所`, `時間・天候`, `光源`, `季節感`, `カメラアングル`
- **プロンプト例**:
  ```
  tall woman with long black hair wearing black kimono carrying
  young sleeping girl in blue kimono on her back, piggyback style,
  seen from behind walking away, misty mountain path at dawn,
  soft morning light, atmospheric fog, distant mountains
  ```

#### タイプ B: キャラクター重視（心情・動きにフォーカス）

- **適用**: 感情の山場、決断の瞬間、戦闘、別れ
- **要素**: `表情`, `手の動き`, `光源（下から/横から）`, `VFX（炎・光・火花）`, `シンプル背景`
- **背景**: 黒一色または単色でキャラの感情を浮き立たせる
- **プロンプト例**:
  ```
  close-up portrait of young exorcist woman with short black hair,
  face shows fierce resolve mixed with deep sorrow, hand trembling,
  holding last burning paper talisman with red-orange flames at tip,
  flame light illuminating face from below, golden amber eyes with tears,
  simple pure black background, cinematic chiaroscuro lighting
  ```

#### 感情曲線に応じた演出マッピング

| 感情ピーク | 推奨タイプ | 色調 | 光源 |
|-----------|-----------|------|------|
| クライマックス | B | 暖色系（朱・橙） | 下から / 爆発光 |
| 静かな別れ | A + B | 寒色系（青・紫） | 月明かり / 朝靄 |
| 覚醒 / 変身 | B | 対比色（青 vs 朱） | 逆光 / 粒子エフェクト |
| 旅立ち | A | 中間色（朝焼け・黄昏） | 自然光 |
| 戦闘 | B | 強対比（赤 vs 青） | 火花 / 魔法光 |

感情曲線の数値は `proposal.md` の表と plot TOML の `peak_intensity` を正とする。

### 3-3. 非 ComfyUI ユーザ用プロンプト表

ComfyUI 以外を使う場合は、以下の表形式でプロンプトを提示:

| シーン | タイプ | プロンプト（日本語 / English） | 備考 |
|--------|--------|------------------------------|------|
| S1 狐火の渓谷 | A | `6歳の少女、焦げ茶のおかっぱ、藍染め着物、後ろ姿、夜の渓谷、無数の青い狐火` | 九十九の影は不要 |
| S2 山を下りる | A | `背の高い女が少女をおんぶ、後ろ姿、朝靄の山道、黒着物、藍染め着物` | おんぶ必須、後ろ姿 |
| S5 焔札 vs 狐火 | B | `短髪の退魔師が朱い焔札を投げる、長髪の女が青い狐火を纏う、夜の神社、石段` | 属性逆転禁止 |

---

## 4. サンプル生成とビジョンチェック

### 4-1. 2 枚テスト生成

全シーンのプロンプトが確定したら、まず **各シーン 2 枚ずつ** テスト生成:

```python
# ComfyUI API 経由の投入例
# 事前準備: 必要なベース画像を upload/image で ComfyUI input にアップロード
# curl -X POST http://localhost:8188/upload/image -F "image=@base.png"

for scene_key, prompt in prompts.items():
    wf["Prompt"]["inputs"]["prompt"] = quality_prefix + ", " + prompt
    for i in range(2):
        seed = random.randint(100000000, 999999999)
        # API 送信（client_id 必須 — raw workflow は 400）
        payload = {"prompt": wf, "client_id": str(uuid.uuid4())}
        # 完了待ち → history から出力ファイル名取得 → view?filename=&type= でダウンロード
```

> **画像サイズ変更時の注意**: ワークフロー内の EmptyLatentImage や Slider2D 等のサイズ指定ノードを変更してから API 送信すること（例: 832×1216 → 1280×670）。生成後は元のサイズに戻す。

### 4-2. ビジョンチェック

生成画像をエージェントの画像読解機能で評価する（Hermes なら `vision_analyze`）。チェック項目:

- [ ] キャラクターの外見（髪型・服装・年齢）が設定と一致しているか
- [ ] 場所・時間・光源がプロンプト通りか
- [ ] 役割の逆転がないか（「短髪=焔札、長髪=狐火」などの属性バインド）
- [ ] 余計なキャラクター・オブジェクトが映り込んでいないか
- [ ] 品質（破綻・指の崩れ・テキストの文字化け）

外見の正誤判定はキャラTOMLの `[appearance]`（厳密にはTOML原文）が正本。パックは執筆用に抜粋されているため、髪色コード等の細部はTOMLで照合する。

### 4-3. 失敗時の対応

| 問題 | 対処 |
|------|------|
| キャラ外見の誤り | プロンプトに具体的特徴を追加（`short brown bob haircut (okappa style)`） |
| 属性逆転 | プロンプト内で明示的にバインド（`short hair woman = talismans, long hair woman = foxfire`） |
| 構図の誤り | プロンプトの先頭に構図指定を移動（`piggyback style, seen from behind` を冒頭に） |
| AI がどうしても再現できない | シーンの表現方針を変更（例: 切断動作→感情クローズアップに切り替え） |
| 複数要素の同時再現困難 | 要素を削減して単純化（例: 2人の対峙→主人公のみのクローズアップ） |

### 4-4. 8 枚バッチ生成の提案

2 枚が合格したら:

```
「このシーン、問題なさそうです。同じプロンプトで 8 枚生成し、
  その中からベストな 1 枚を選びますか？」
```

ユーザの同意を得て 8 枚生成し、ユーザ自身の目視で最終選定を依頼する。

> **注意**: 一度 OK を出した画像はビジョンチェック不要。新規バッチのみを評価対象とすること。

---

## 5. 最終ラインナップ確定

全シーンの最終画像が決まったら、テーブルにまとめてユーザに提示:

```
### 挿絵最終ラインナップ

| # | シーン | ファイル |
|---|--------|---------|
| S1 | 狐火の渓谷 | scene1_remake_v2_783827809.png |
| S2 | 山を下りる | s2_batch_3_727197612.png |
| ... | ... | ... |
```

### pixiv投稿との接続

`pixiv_export.py` は本文中の画像タグを `[※挿絵N]` に置換する。挿絵を入れる位置には、本文中に `![...](...)` か `<!-- 挿絵: シーン説明 -->` を**必ず記載**しておく（記載がないとプレースホルダーが想定より少なくなる。詳細は `pixiv-export.md` Pitfall 6）。

---

## 6. トラブルシューティング

| 問題 | 対処 |
|------|------|
| ComfyUI に接続できない | `curl http://localhost:8188/system_stats` で稼働確認。WSL の場合は Mirrored Networking 有効確認 |
| API 400 `no_prompt` | ペイロードが `{"prompt": wf, "client_id": "..."}` 形式か確認（`wf` 直送りは不可） |
| 画像ダウンロード 404 | history API で `type` を確認（`temp` / `output`）。URL の `type=` パラメータを合わせる |
| ベース画像がない/400 | ComfyUI の `upload/image` エンドポイントでアップロードし、ワークフローの LoadImage ノードでそのファイル名を指定する |
| 画像サイズを変えたい | ワークフロー内の EmptyLatentImage / Slider2D 等のノード入力（`width`, `height`）を変更。縦長(832×1216)から横長(1280×670)への変更時は `Xi/Xf` と `Yi/Yf` の両方を更新 |
| メモリ不足 | 画像サイズを縮小、または `--lowvram` オプション |

---

## 関連リファレンス

- **pixiv投稿**: `pixiv-export.md` — プレースホルダー置換・投稿手順
- **キャラ外見の正本**: `character-template.md` — TOML `[appearance]` の項目定義
- **感情曲線**: `proposal.md` の表＋ plot TOML の `peak_intensity`
