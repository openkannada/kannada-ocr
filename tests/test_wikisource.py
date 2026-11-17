# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

from kannada_ocr import wikisource as ws

PAGE_HTML = """<div class="prp-page-content"><div class="mw-parser-output">
<div class="prp-page-qualityheader quality4">ಈ ಪುಟವನ್ನು ಪರಿಶೀಲಿಸಲಾಗಿದೆ</div>
<div class="pagetext"><div class="mw-parser-output"><style>.x{color:red}</style>
<div class="running-header"><span>ಪ್ರಕರಣ</span> <span>೧೫</span></div>
<p>ವಾಚಕರೇ! ಹಿಂದಿನ<sup class="reference"><a>[೧]</a></sup> ಪ್ರಕರಣದಲ್ಲಿ<br>ನಾವು
ನಿಮಗೆ</p><span style="display: none">hidden</span>
<ol class="references"><li><span class="mw-cite-backlink">↑</span> ಟಿಪ್ಪಣಿ</li></ol>
</div></div></div></div>
<div class="prp-page-image"><span><img src="//thumb.wikimedia.org/a/b.djvu/page40-1280px-b.djvu.jpg?utm_source=x&amp;y=1" width="1280"></span></div>"""

INDEX_HTML = """<table><tr><th class="ws-index-label">Year</th>
<td class="ws-index-value"><a>1920</a></td></tr></table>
<a href="/wiki/%E0%B2%AA%E0%B3%81%E0%B2%9F:Book_x.djvu/%E0%B3%A7" class="prp-pagequality-4 x">1</a>
<a href="/wiki/%E0%B2%AA%E0%B3%81%E0%B2%9F:Book_x.djvu/%E0%B3%A7%E0%B3%A8" class="prp-pagequality-3">12</a>
<a href="/wiki/%E0%B2%AA%E0%B3%81%E0%B2%9F:Other.djvu/%E0%B3%A9" class="prp-pagequality-4">3</a>"""


class FakeClient:
    def __init__(self, pages):
        self.pages = pages

    def get_text(self, url):
        return self.pages[url]


def test_kannada_page_numbers_round_trip():
    assert ws.kannada_number(240) == "೨೪೦"
    assert ws.parse_number("೨೪೦") == 240
    assert ws.parse_number("ಅ") is None


def test_page_text_keeps_visible_text_in_printed_order():
    assert ws.page_text(PAGE_HTML) == "ಪ್ರಕರಣ ೧೫\nವಾಚಕರೇ! ಹಿಂದಿನ ಪ್ರಕರಣದಲ್ಲಿ\nನಾವು ನಿಮಗೆ\nಟಿಪ್ಪಣಿ"


def test_page_image_url_is_absolute_without_tracking_query():
    assert (
        ws.page_image_url(PAGE_HTML)
        == "https://thumb.wikimedia.org/a/b.djvu/page40-1280px-b.djvu.jpg"
    )


def test_read_index_reads_fields_and_only_this_books_pages():
    url = ws.wiki_url("ಪರಿವಿಡಿ:Book x.djvu")
    index = ws.read_index(FakeClient({url: INDEX_HTML}), "ಪರಿವಿಡಿ:Book x.djvu")
    assert index.year == 1920
    assert index.pages == {1: 4, 12: 3}


def test_sample_pages_skips_front_matter_and_spreads_out():
    index = ws.IndexInfo("t", "f", {}, {n: 4 for n in range(1, 101)})
    picked = ws.sample_pages(index, 4)
    assert picked == [17, 39, 62, 84]
    assert ws.sample_pages(ws.IndexInfo("t", "f", {}, {1: 0, 2: 3}), 4) == [2]
