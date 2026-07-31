"""Legacy landing-page redirects. Old marketing URLs (and any unlock links like
`/shaadi?pass=<tok>` already shared with buyers) must keep working via a 301 to
the new canonical path, WITH the query string preserved."""
import pytest

# (path, expected canonical target)
REDIRECTS = [
    ("/shaadi", "/en/marriage"),
    ("/milan", "/en/compatibility"),
    ("/padhai", "/career"),
]


@pytest.mark.parametrize("src,dst", REDIRECTS)
def test_legacy_path_301(client, src, dst):
    r = client.get(src, follow_redirects=False)
    assert r.status_code == 301, r.text
    assert r.headers["location"] == dst


@pytest.mark.parametrize("src,dst", REDIRECTS)
def test_legacy_path_preserves_pass_query(client, src, dst):
    r = client.get(f"{src}?pass=tok_abc123", follow_redirects=False)
    assert r.status_code == 301, r.text
    assert r.headers["location"] == f"{dst}?pass=tok_abc123"
