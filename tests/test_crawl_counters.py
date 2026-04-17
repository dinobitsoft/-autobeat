"""
Tests for the brands_left / pages_left counter behaviour in the crawl loop.

Semantics:
- pages_left: number of pages not yet fetched (decrements every step)
- brands_left: number of brands not yet STARTED (decrements when first page of a brand is encountered)

Both counters are decremented BEFORE the log line, so the log reflects the
state AFTER this entry is consumed.
"""

import random
from typing import Dict, List, Tuple, Set


def simulate_crawl(brands: Dict[str, int], shuffle: bool = False, seed: int = 0) -> List[Tuple[str, int, int, int]]:
    """
    Simulates the counter logic from daily_check.
    brands: {brand_title: page_count}
    Returns list of (brand_title, page, brands_left, pages_left) as logged.
    """
    work_queue: List[Tuple[str, int]] = []
    for brand_title, page_count in brands.items():
        for p in range(1, page_count + 1):
            work_queue.append((brand_title, p))

    if shuffle:
        random.seed(seed)
        random.shuffle(work_queue)

    pages_left = sum(brands.values())
    brands_seen: Set[str] = set()
    brands_left = len(brands)
    log: List[Tuple[str, int, int, int]] = []

    for brand_title, page in work_queue:
        pages_left -= 1
        if brand_title not in brands_seen:
            brands_seen.add(brand_title)
            brands_left -= 1
        log.append((brand_title, page, brands_left, pages_left))

    return log


def test_pages_left_decrements_every_step():
    brands = {"audi": 3, "bmw": 2}
    log = simulate_crawl(brands)
    total = sum(brands.values())
    for i, (_, _, _, pages_left) in enumerate(log):
        assert pages_left == total - (i + 1)


def test_pages_left_reaches_zero():
    brands = {"audi": 3, "bmw": 2, "honda": 1}
    log = simulate_crawl(brands)
    assert log[-1][3] == 0


def test_brands_left_reaches_zero():
    brands = {"audi": 3, "bmw": 2, "honda": 1}
    log = simulate_crawl(brands)
    assert log[-1][2] == 0


def test_brands_left_decrements_on_first_page_only():
    """brands_left decrements exactly once per brand — on its first page."""
    brands = {"audi": 3, "bmw": 2}
    log = simulate_crawl(brands, shuffle=False)
    # sequential: audi 1,2,3 then bmw 1,2
    # audi page 1 (index 0): first encounter → brands_left = 1
    assert log[0][2] == 1
    # audi page 2 (index 1): already seen → brands_left still 1
    assert log[1][2] == 1
    # audi page 3 (index 2): already seen → brands_left still 1
    assert log[2][2] == 1
    # bmw page 1 (index 3): first encounter → brands_left = 0
    assert log[3][2] == 0
    # bmw page 2 (index 4): already seen → brands_left still 0
    assert log[4][2] == 0


def test_single_page_brand_decrements_immediately():
    """A brand with 1 page should show brands_left already decremented when logged."""
    brands = {"cupra": 1, "opel": 3}
    log = simulate_crawl(brands, shuffle=False)
    # cupra page 1/1 is first — brands_left goes from 2 to 1
    assert log[0][0] == "cupra"
    assert log[0][2] == 1
    # opel page 1 — brands_left goes from 1 to 0
    assert log[1][2] == 0
    # opel page 2, 3 — stays at 0
    assert log[2][2] == 0
    assert log[3][2] == 0


def test_brands_left_never_shows_same_count_for_different_brand_starts():
    """
    Core regression: two different brands starting should each decrement brands_left.
    Skoda and peugeot both starting should show different brands_left values.
    """
    brands = {"skoda": 3, "peugeot": 3, "cupra": 1}
    log = simulate_crawl(brands, shuffle=False)
    # first page of each brand must have a strictly lower brands_left than the previous first page
    first_pages = [(bt, bl) for bt, pg, bl, _ in log if pg == 1]
    brand_left_values = [bl for _, bl in first_pages]
    assert brand_left_values == sorted(brand_left_values, reverse=True)
    assert len(set(brand_left_values)) == len(brand_left_values), \
        f"brands_left not unique at first-page encounters: {first_pages}"


def test_brands_left_correct_with_shuffled_pages():
    """After brand X's first page is seen, brands_left must not go back up."""
    brands = {"audi": 5, "bmw": 3, "honda": 2, "cupra": 1}
    for seed in range(30):
        log = simulate_crawl(brands, shuffle=True, seed=seed)
        seen: Set[str] = set()
        prev_brands_left = len(brands)
        for brand_title, page, brands_left, pages_left in log:
            is_first = brand_title not in seen
            if is_first:
                seen.add(brand_title)
                assert brands_left == prev_brands_left - 1, (
                    f"seed={seed} brand={brand_title} page={page}: "
                    f"expected brands_left={prev_brands_left - 1}, got={brands_left}"
                )
                prev_brands_left = brands_left
            else:
                assert brands_left == prev_brands_left, (
                    f"seed={seed} brand={brand_title} page={page}: "
                    f"brands_left changed unexpectedly to {brands_left}, expected {prev_brands_left}"
                )


def test_brands_left_never_negative():
    brands = {"audi": 2, "bmw": 1}
    for seed in range(10):
        log = simulate_crawl(brands, shuffle=True, seed=seed)
        for _, _, brands_left, pages_left in log:
            assert brands_left >= 0
            assert pages_left >= 0
