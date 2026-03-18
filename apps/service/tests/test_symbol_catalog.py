from smap_service.core.symbol_catalog import infer_sector, merged_symbol_universe


def test_merged_symbol_universe_includes_curated_and_dynamic_symbols() -> None:
    symbols = merged_symbol_universe(["RELIANCE-FUT", "ZOMATO-FUT", "  tcs-fut  "])
    assert "RELIANCE-FUT" in symbols
    assert "TCS-FUT" in symbols
    assert "ZOMATO-FUT" in symbols
    assert symbols == sorted(symbols)


def test_infer_sector_from_symbol() -> None:
    assert infer_sector("RELIANCE-FUT") == "energy"
    assert infer_sector("UNKNOWN-FUT") is None
