import pytest

from cbj_sentinel import net


@pytest.mark.parametrize("url", [
    "https://www.nhl.com/bluejackets/news",
    "https://www.1stohiobattery.com/columbus-blue-jackets-news/2026/09/x",
    "HTTPS://WWW.NHL.COM/x",
])
def test_browser_allows_known_https(url):
    assert net.is_safe_browser_url(url)


@pytest.mark.parametrize("url", [
    "http://www.nhl.com/",                       # plain http
    "file:///C:/Windows/System32/calc.exe",       # local file
    "C:\\Windows\\System32\\calc.exe",            # bare path -> os.startfile
    "\\\\evil-server\\share\\payload.exe",        # UNC path
    "javascript:alert(1)",
    "https://evil.example.com/",                 # unknown host
    "https://www.nhl.com.evil.com/",             # suffix trick
    "https://user:pw@www.nhl.com/",              # credentials
    "https://www.nhl.com:8443/",                 # odd port
    "https://www.nhl.com/\r\nInjected",          # control chars
    "",
    None,
    123,
])
def test_browser_blocks_unsafe(url):
    assert not net.is_safe_browser_url(url)


def test_fetch_rejects_disallowed_host():
    with pytest.raises(net.UnsafeURLError):
        net.fetch_bytes("https://example.com/data.json", 1024)


def test_fetch_rejects_http():
    with pytest.raises(net.UnsafeURLError):
        net.fetch_bytes("http://api-web.nhle.com/v1/score/now", 1024)


def test_open_in_browser_blocks_without_launching(monkeypatch):
    called = []
    monkeypatch.setattr(net.webbrowser, "open", lambda *a, **k: called.append(a) or True)
    assert net.open_in_browser("file:///C:/evil.exe") is False
    assert called == []
