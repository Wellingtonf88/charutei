"""Testes do Km de Fumaça: EXPERIENCE_SCORE/KNOWLEDGE_SCORE/CONSUMER_STATUS/badges/streak."""

from datetime import date, timedelta

from charutei_scoring import (
    STATUS_NAMES,
    compute_badges,
    compute_consumer_status,
    compute_experience_score,
    compute_knowledge_score,
    compute_streak,
)


def test_experience_score_rewards_diversity_and_streak_not_just_quantity() -> None:
    # dois usuários com a mesma quantidade de degustações/humidor, mas diversidade diferente
    narrow = compute_experience_score(
        humidor_size=5,
        total_tastings=5,
        distinct_countries=1,
        distinct_brands=1,
        streak_days=0,
    )
    diverse = compute_experience_score(
        humidor_size=5,
        total_tastings=5,
        distinct_countries=4,
        distinct_brands=3,
        streak_days=2,
    )
    assert diverse > narrow  # diversidade/recorrência pesam, não só quantidade


def test_experience_score_streak_bonus_saturates() -> None:
    at_cap = compute_experience_score(
        humidor_size=0, total_tastings=0, distinct_countries=0, distinct_brands=0, streak_days=10
    )
    past_cap = compute_experience_score(
        humidor_size=0, total_tastings=0, distinct_countries=0, distinct_brands=0, streak_days=100
    )
    assert at_cap == past_cap  # bônus de streak satura em 10 dias


def test_knowledge_score_rewards_written_notes_not_star_count() -> None:
    with_notes = compute_knowledge_score(tastings_with_notes=5, distinct_flavors=3)
    without_notes = compute_knowledge_score(tastings_with_notes=0, distinct_flavors=3)
    assert with_notes > without_notes


def test_consumer_status_needs_both_scores_not_just_raw_activity() -> None:
    # muita atividade (experience alto) mas zero documentação (knowledge zero)
    status_low_knowledge = compute_consumer_status(experience_score=39, knowledge_score=0)
    # menos atividade, mas documentação rica o suficiente para cruzar o próximo threshold
    status_high_knowledge = compute_consumer_status(experience_score=20, knowledge_score=20)
    assert status_high_knowledge.combined_score > status_low_knowledge.combined_score
    assert STATUS_NAMES.index(status_high_knowledge.name) >= STATUS_NAMES.index(
        status_low_knowledge.name
    )


def test_consumer_status_thresholds_and_progress() -> None:
    novato = compute_consumer_status(experience_score=0, knowledge_score=0)
    assert novato.name == "Novato"
    assert novato.index == 0
    assert novato.next_threshold == 15
    assert novato.progress == 0.0

    mestre = compute_consumer_status(experience_score=100, knowledge_score=0)
    assert mestre.name == "Mestre Charuteiro"
    assert mestre.index == 3
    assert mestre.next_threshold is None
    assert mestre.progress == 1.0


def test_streak_counts_consecutive_days_until_today_or_yesterday() -> None:
    today = date.today()
    dates = [today, today - timedelta(days=1), today - timedelta(days=2)]
    assert compute_streak(dates) == 3


def test_streak_breaks_on_gap() -> None:
    today = date.today()
    dates = [today, today - timedelta(days=5)]  # sem degustação ontem/anteontem → quebra
    assert compute_streak(dates) == 1


def test_streak_zero_when_no_recent_activity() -> None:
    stale = [date.today() - timedelta(days=10)]
    assert compute_streak(stale) == 0
    assert compute_streak([]) == 0


def test_badges_earned_flags() -> None:
    badges = compute_badges(
        total_tastings=5,
        humidor_size=10,
        distinct_countries=3,
        distinct_flavors=5,
        streak_days=3,
    )
    assert all(b.earned for b in badges)

    none_earned = compute_badges(
        total_tastings=0,
        humidor_size=0,
        distinct_countries=0,
        distinct_flavors=0,
        streak_days=0,
    )
    assert not any(b.earned for b in none_earned)
