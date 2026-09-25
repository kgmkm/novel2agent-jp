"""novel2agent-jp 統合テスト用のサンプルプロジェクトを生成する (3章構成)"""
from pathlib import Path
import shutil


def build(root: Path) -> Path:
    if root.exists():
        shutil.rmtree(root)
    novel = root / "novel"
    novel.mkdir(parents=True)

    (root / "meta.toml").write_text("""[work]
title = "サンプル作品"
genre = "現代ファンタジー"
status = "writing"
plan_status = "confirmed"

[[chapters]]
number = 1
plot = "plot/plot-ch01.toml"
novel = "novel/ch01.md"
status = "written"

[[chapters]]
number = 2
plot = "plot/plot-ch02.toml"
novel = "novel/ch02.md"
status = "written"

[[chapters]]
number = 3
plot = "plot/plot-ch03.toml"
status = "draft"
""", encoding="utf-8")

    c = root / "character"
    c.mkdir()
    (c / "chara-001.toml").write_text("""id = "chara-001"
name_ja = "桜井美咲"
name_ruby = "さくらい みさき"
role = "protagonist"

[basic]
gender = "female"
age = 18
first_person = "私"
speech_style = "丁寧語"

[appearance]
hair = "黒髪ロング"
outfit = "大学の私服"

[[relations]]
target = "chara-002"
kind = "学友"
emotion = "信頼"

[[versions]]
from_chapter = 3
to_chapter = 4
age = 19
note = "覚醒後"

[[versions]]
from_chapter = 5
to_chapter = 6
age = 20
""", encoding="utf-8")
    (c / "chara-002.toml").write_text("""id = "chara-002"
name_ja = "佐藤太郎"
name_ruby = "さとう たろう"
role = "support"

[basic]
gender = "male"
age = 20
first_person = "俺"
""", encoding="utf-8")

    w = root / "worldbuilding"
    w.mkdir()
    (w / "world-001.toml").write_text("""id = "world-001"
title = "基本設定"
kind = "core"
content = '''架空の街・臼井市が舞台。'''

[[constraints]]
kind = "forbidden_words"
words = ["スマホ", "SNS"]
note = "舞台は1998年"
""", encoding="utf-8")

    p = root / "plot"
    p.mkdir()
    (p / "plot-ch01.toml").write_text("""id = "plot-ch01"
chapter = 1
title = "導入"
pov = "chara-001"
summary = "美咲が臼井市に引っ越してくる。"
summary_status = "confirmed"

[[scenes]]
title = "引っ越し"
location = "臼井駅"
pov = "chara-001"
characters = ["chara-001", "chara-002"]
content = '''荷物の中から古い日記帳が出てくる。'''

[[established]]
content = "美咲が臼井市に引っ越した"
status = "confirmed"

[[foreshadowing]]
id = "fs-001"
content = "荷物から出た古い日記"
resolve_chapter = 3
""", encoding="utf-8")
    (p / "plot-ch02.toml").write_text("""id = "plot-ch02"
chapter = 2
title = "接触"
summary = "美咲が商店街で不審な老婦人に出会う。"
summary_status = "confirmed"

[[scenes]]
title = "商店街"
location = "臼井商店街"
pov = "chara-001"
characters = ["chara-001"]
content = '''老婦人が美咲の名を知らずに呼ぶ。'''

[[established]]
content = "老婦人は美咲の祖母の名を口にした"
status = "proposed"

[[established]]
content = "美咲の部屋の鏡が一瞬曇った"
status = "confirmed"

[[foreshadowing]]
id = "fs-002"
content = "老婦人の「203号室へは戻るな」"
resolve_chapter = 3
""", encoding="utf-8")
    (p / "plot-ch03.toml").write_text("""id = "plot-ch03"
chapter = 3
title = "覚醒"
pov = "chara-002"

[[scenes]]
title = "夜の学校"
location = "臼井高校・旧校舎"
pov = "chara-002"
characters = ["chara-001", "chara-002"]
content = '''日記の最後の頁が空白ではない。美咲が気を失う。'''
""", encoding="utf-8")

    (novel / "ch01.md").write_text("""第1章 導入

引っ越しのトラックが去ったあと、美咲は段ボールの山を前にしてため息をついた。
（…中略…）
湯上がりの髪を乾かしながら、美咲は窓の外を見た。臼井の夜は静かだった。
""", encoding="utf-8")
    (novel / "ch02.md").write_text("""第2章 接触

商店街のアーケード下、美咲は人波を縫って歩いていた。
（…中略…）
「——美咲さん、でしょう？」と老婦人は言った。初対面のはずなのに。
""", encoding="utf-8")
    return root


if __name__ == "__main__":
    import sys
    root = build(Path(sys.argv[1] if len(sys.argv) > 1 else ".work/sample"))
    print("built:", root)
