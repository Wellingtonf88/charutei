"""Testes do Recommendation Engine v1: pontuação, exclusão, ranking, corte."""

from charutei_recommendation import CigarProfile, recommend


def _cigar(id_: str, label: str, brand: str, country: str, strength: str) -> CigarProfile:
    return CigarProfile(cigar_id=id_, label=label, brand=brand, country=country, strength=strength)


def test_scores_by_brand_country_strength_affinity() -> None:
    catalog = [
        _cigar("a", "A", "Cohiba", "Cuba", "medium"),  # marca + país + força = 4
        _cigar("b", "B", "Cohiba", "Nicaragua", "full"),  # só marca = 2
        _cigar("c", "C", "Montecristo", "Cuba", "medium"),  # país + força = 2
        _cigar("d", "D", "Padron", "Honduras", "mild"),  # nada = 0, excluído do resultado
    ]
    results = recommend(
        catalog,
        liked_brands={"Cohiba"},
        liked_countries={"Cuba"},
        liked_strengths={"medium"},
        exclude_cigar_ids=set(),
    )
    by_id = {r.cigar_id: r for r in results}
    assert by_id["a"].score == 4
    assert by_id["b"].score == 2
    assert by_id["c"].score == 2
    assert "d" not in by_id  # score 0 não aparece
    assert results[0].cigar_id == "a"  # maior score primeiro


def test_reasons_explain_the_score() -> None:
    catalog = [_cigar("a", "A", "Cohiba", "Cuba", "medium")]
    results = recommend(
        catalog,
        liked_brands={"Cohiba"},
        liked_countries={"Cuba"},
        liked_strengths=set(),
        exclude_cigar_ids=set(),
    )
    assert "mesma marca: Cohiba" in results[0].reasons
    assert "mesmo país: Cuba" in results[0].reasons
    assert not any("força" in r for r in results[0].reasons)


def test_excludes_already_owned_or_tasted() -> None:
    catalog = [_cigar("a", "A", "Cohiba", "Cuba", "medium")]
    results = recommend(
        catalog,
        liked_brands={"Cohiba"},
        liked_countries=set(),
        liked_strengths=set(),
        exclude_cigar_ids={"a"},
    )
    assert results == []


def test_no_signal_means_no_recommendations() -> None:
    catalog = [_cigar("a", "A", "Cohiba", "Cuba", "medium")]
    results = recommend(
        catalog,
        liked_brands=set(),
        liked_countries=set(),
        liked_strengths=set(),
        exclude_cigar_ids=set(),
    )
    assert results == []  # sem sinal, sem fallback de popularidade nesta v1


def test_limit_caps_results() -> None:
    catalog = [_cigar(str(i), f"Cigar {i}", "Cohiba", "Cuba", "medium") for i in range(20)]
    results = recommend(
        catalog,
        liked_brands={"Cohiba"},
        liked_countries=set(),
        liked_strengths=set(),
        exclude_cigar_ids=set(),
        limit=5,
    )
    assert len(results) == 5


def test_tie_break_is_deterministic_by_label() -> None:
    catalog = [
        _cigar("z", "Zebra", "Cohiba", "x", "x"),
        _cigar("a", "Alpha", "Cohiba", "x", "x"),
    ]
    results = recommend(
        catalog,
        liked_brands={"Cohiba"},
        liked_countries=set(),
        liked_strengths=set(),
        exclude_cigar_ids=set(),
    )
    assert [r.label for r in results] == ["Alpha", "Zebra"]  # mesmo score → ordem alfabética
