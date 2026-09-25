"""scripts/tests/test_vfm_to_kakuyomu.py — vfm_to_kakuyomu.py の変換テスト"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE.parent.parent / "scripts" / "vfm_to_kakuyomu.py"
WORK = HERE / ".work"
PY = sys.executable

sys.path.insert(0, str(SCRIPT.parent))
from vfm_to_kakuyomu import convert, extract_title, validate_kakuyomu  # noqa: E402


def run_cli(src: Path, *extra):
    proc = subprocess.run(
        [PY, str(SCRIPT), str(src), *extra],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------
# ルビ
# ---------------------------------------------------------------------

def test_ruby_single():
    assert convert("{灯|あかり}は六つだった。") == "｜灯《あかり》は六つだった。"


def test_ruby_group():
    assert convert("{日本語|にほんご}を学ぶ。") == "｜日本語《にほんご》を学ぶ。"


def test_ruby_compound_per_char():
    out = convert("{電子出版|でん|し|しゅっ|ぱん}")
    assert out == "｜電《でん》｜子《し》｜出《しゅっ》｜版《ぱん》"


def test_existing_kakuyomu_ruby_passthrough():
    # 原稿に既にカクヨム記法が書かれている場合はそのまま
    src = "冴えない彼女《ヒロイン》の育てかた。あいつの｜etc《えとせとら》。"
    assert convert(src) == src


def test_ruby_before_emphasis_order():
    # 傍点の中にルビが入った場合はルビ優先（傍点を外す）+ 警告
    warnings = []
    out = convert("《《｜漢字《かんじ》だ》》", warnings=warnings)
    assert out == "｜漢字《かんじ》だ"
    assert any("併用できません" in w for w in warnings)


# ---------------------------------------------------------------------
# 傍点
# ---------------------------------------------------------------------

def test_emphasis_dots_kept():
    assert convert("山へ《《柴刈り》》に出かけた。") == "山へ《《柴刈り》》に出かけた。"


def test_emphasis_html_converted():
    out = convert('灯は<em class="emphasis-dot">ただ、ひとりで</em>歩いた。')
    assert out == "灯は《《ただ、ひとりで》》歩いた。"


def test_emphasis_across_newline_not_matched():
    warnings = validate_kakuyomu("《《前の行\n次の行》》")
    assert any("山括弧" in w for w in warnings)


# ---------------------------------------------------------------------
# 構造・見出し・ページ区切り
# ---------------------------------------------------------------------

def test_title_extracted_and_removed():
    src = "# 第一章　宵闇の剣姫\n\n朝の稽古は、いつもと同じ時間に始まった。\n"
    assert extract_title(src) == "第一章　宵闇の剣姫"
    out = convert(src)
    assert "第一章" not in out
    assert "朝の稽古" in out


def test_section_heading_kept_as_text():
    # 原稿先頭の見出しはタイトルとして除去、2つ目以降は # を外して本文に残す
    src = "# 第一章　宵闇の剣姫\n\n## 一\n\n蝉が啼いていた。"
    assert extract_title(src) == "第一章　宵闇の剣姫"
    out = convert(src)
    assert out == "一\n\n蝉が啼いていた。"


def test_frontmatter_removed():
    src = "---\ntitle: 妖狐は、嗤う\n---\n\n# 妖狐は、嗤う\n\n本文。"
    out = convert(src)
    assert "title:" not in out
    assert out == "本文。"


def test_page_break_to_scene_marker():
    out = convert("前の場面。\n\n===\n\n次の場面。")
    assert out == "前の場面。\n\n◇\n\n次の場面。"


def test_page_break_collapsed():
    out = convert("A\n\n===\n\n\n===\n\nB")
    assert out == "A\n\n◇\n\nB"


def test_page_break_removable():
    out = convert("A\n\n===\n\nB", scene_break="")
    assert "◇" not in out and "===" not in out
    assert "A" in out and "B" in out


def test_footnote_inlined():
    src = "古社[^1]の境内。\n\n[^1]: 古社（こしゃ）—— 古い神社。"
    out = convert(src)
    assert "[^1]" not in out
    assert "古社（古社（こしゃ）—— 古い神社。）の境内。" in out


# ---------------------------------------------------------------------
# 除去・テキスト化
# ---------------------------------------------------------------------

def test_bold_italic_textified_with_warning():
    warnings = []
    out = convert("**震えて**いた。*怖いとは思わなかった*。", warnings=warnings)
    assert out == "震えていた。怖いとは思わなかった。"
    assert any("太字" in w for w in warnings)
    assert any("斜体" in w for w in warnings)


def test_image_becomes_placeholder():
    warnings = []
    out = convert("前。\n\n![狐火の夜](image/序章2.webp)\n\n後。", warnings=warnings)
    assert "[※挿絵1]" in out
    assert "image/序章2.webp" not in out
    assert any("画像" in w for w in warnings)


def test_images_numbered_in_order():
    out = convert("![a](1.png)\n\n![b](2.png)")
    assert "[※挿絵1]" in out and "[※挿絵2]" in out


def test_links_keep_url():
    out = convert("[著者サイト](https://example.com)も見てね。")
    assert out == "著者サイト（https://example.com）も見てね。"


def test_html_comment_removed():
    out = convert("本文。\n\n<!-- 挿絵: シーン説明 -->\n\n続き。")
    assert "<!--" not in out and "シーン説明" not in out


def test_strikethrough_and_quote():
    out = convert("~~打ち消し~~の行。\n\n> 狐の嫁入りを見てはならぬ。")
    assert out == "打ち消しの行。\n\n狐の嫁入りを見てはならぬ。"


def test_code_block_and_table_and_list():
    src = "```\n碑文\n```\n\n| 名前 | 種族 |\n|------|------|\n| 灯 | 人間 |\n\n- 項目1\n- 項目2"
    out = convert(src)
    assert out == "碑文\n\n名前 種族\n灯 人間\n\n項目1\n項目2"


def test_page_jump_removed():
    warnings = []
    out = convert("前。[%2]後。", warnings=warnings)
    assert out == "前。後。"
    assert any("ページジャンプ" in w for w in warnings)


# ---------------------------------------------------------------------
# validate_kakuyomu
# ---------------------------------------------------------------------

def test_validate_ruby_limits():
    long_parent = "あ" * 21
    warnings = validate_kakuyomu(f"｜{long_parent}《よみ》")
    assert any("親文字" in w for w in warnings)

    long_ruby = "よ" * 51
    warnings = validate_kakuyomu(f"｜漢字《{long_ruby}》")
    assert any("ルビ文字" in w for w in warnings)


def test_validate_catches_unconverted_ruby():
    warnings = validate_kakuyomu("そのままの{漢字|かんじ}記法")
    assert any("未変換のルビ記法" in w for w in warnings)


def test_validate_ok_on_clean_text():
    src = "｜灯《あかり》は、山へ《《柴刈り》》に出かけた。"
    assert validate_kakuyomu(convert(src)) == []


def test_validate_escape_display():
    # ｜《 は記号を表示させるカクヨムのエスケープなので警告しない
    assert validate_kakuyomu("記号｜《を表示") == []


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def test_cli_roundtrip(tmp_path=None):
    WORK.mkdir(exist_ok=True)
    src = WORK / "kaku_cli_in.md"
    out = WORK / "kaku_cli_out.txt"
    src.write_text(
        "# 第一章\n\n{灯|あかり}は歩いた。\n\n===\n\n続き。\n",
        encoding="utf-8",
    )
    code, stdout, stderr = run_cli(src, "-o", str(out))
    assert code == 0, stderr
    text = out.read_text(encoding="utf-8")
    assert "｜灯《あかり》は歩いた。" in text
    assert "第一章" not in text
    assert "◇" in text
