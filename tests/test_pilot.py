# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

import hashlib

from kannada_ocr.pilot import Page, image_path, read_pages, sha256_file, write_pages

URL = "https://archive.org/download/x/x_images.zip/X%2FX_0656.jpg"


def test_the_page_list_round_trips(tmp_path):
    pages = [Page("kittel-1894", "tuebingen", "600", URL, "ab" * 32)]
    write_pages(tmp_path / "pages.tsv", pages)
    assert read_pages(tmp_path / "pages.tsv") == pages


def test_an_image_is_named_by_its_printed_page(tmp_path):
    page = Page("kittel-1894", "google", "600", URL.replace(".jpg", ".jp2"), "")
    assert image_path(tmp_path, page) == tmp_path / "kittel-1894" / "google" / "600.jp2"


def test_the_checksum_is_sha256(tmp_path):
    path = tmp_path / "a.jpg"
    path.write_bytes(b"page")
    assert sha256_file(path) == hashlib.sha256(b"page").hexdigest()
