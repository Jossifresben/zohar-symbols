import pytest
from pipeline.hebnum import heb_to_int, int_to_heb

@pytest.mark.parametrize("s,n", [
    ("א", 1), ("ט", 9), ("י", 10), ("טו", 15), ("טז", 16), ("כ", 20),
    ("כא", 21), ("צט", 99), ("ק", 100), ("קיז", 117), ("קמז", 147),
    ("ריט", 219), ("רכא", 221), ("רצו", 296), ("ש", 300),
])
def test_round_trip(s, n):
    assert heb_to_int(s) == n
    assert int_to_heb(n) == s

def test_bad_input():
    with pytest.raises(ValueError):
        heb_to_int("abc")
    with pytest.raises(ValueError):
        heb_to_int("")
