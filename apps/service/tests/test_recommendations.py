from smap_service.core.recommendations import RecommendationService


def test_recommendations_default_sort_is_confidence_desc() -> None:
    service = RecommendationService()
    items = service.list()
    confidences = [item.confidence for item in items]
    assert confidences == sorted(confidences, reverse=True)


def test_recommendations_search_filters_symbol() -> None:
    service = RecommendationService()
    items = service.list(query="tcs")
    assert len(items) == 1
    assert items[0].symbol == "TCS-FUT"
