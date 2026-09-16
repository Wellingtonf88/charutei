"""Km de Fumaça — EXPERIENCE_SCORE / KNOWLEDGE_SCORE / CONSUMER_STATUS.

Puro e determinístico, sem I/O e sem LLM — degrau 0 da cascata (mais barato que qualquer
consulta). O chamador (services/api) busca os dados via OltpRepository/KnowledgeGraphRepo e
agrega os números primitivos que estas funções recebem.

REPUTATION_SCORE e INFLUENCE_SCORE (pedidos no prompt mestre) não têm dado real ainda — dependem
de sinal social (follow/like/aceitação de recomendação) que só existe a partir da Fase 7
(Community Intelligence). Não calculados aqui — não inventar número sem dado por trás.

Pesos e thresholds nomeados aqui, num único lugar — "não hardcode regras de negócio espalhadas
pela aplicação" (CLAUDE.md). v1, deliberadamente simples; revisitar com dado real de produção.
"""

from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel

STATUS_NAMES = ["Novato", "Aficionado", "Conhecedor", "Mestre Charuteiro"]
# Score combinado (experience + knowledge) — por isso pura quantidade de registros não é
# suficiente sozinha para subir de status (requisito explícito do prompt mestre).
STATUS_THRESHOLDS = [0, 15, 40, 80]

_STREAK_CAP = 10  # bônus de recorrência satura em 10 dias — evita recompensar streaks infinitos


def compute_experience_score(
    *,
    humidor_size: int,
    total_tastings: int,
    distinct_countries: int,
    distinct_brands: int,
    streak_days: int,
) -> int:
    """Bagagem acumulada: atividade (humidor + degustações) + diversidade (países/marcas) +
    recorrência (streak). Diversidade e recorrência evitam que o score seja só quantidade bruta."""
    return (
        humidor_size
        + total_tastings * 2
        + distinct_countries * 3
        + distinct_brands * 2
        + min(streak_days, _STREAK_CAP)
    )


def compute_knowledge_score(*, tastings_with_notes: int, distinct_flavors: int) -> int:
    """Profundidade do conhecimento documentado: prioriza nota escrita de verdade (não só
    estrelas) e vocabulário de sabores usado — não a contagem de degustações."""
    return tastings_with_notes * 3 + distinct_flavors * 2


class ConsumerStatus(BaseModel):
    name: str
    index: int
    next_threshold: int | None
    progress: float  # 0..1 até o próximo status (1.0 = status máximo)
    combined_score: int


def compute_consumer_status(*, experience_score: int, knowledge_score: int) -> ConsumerStatus:
    combined = experience_score + knowledge_score
    index = 0
    for i in range(len(STATUS_THRESHOLDS) - 1, -1, -1):
        if combined >= STATUS_THRESHOLDS[i]:
            index = i
            break
    is_max = index == len(STATUS_THRESHOLDS) - 1
    if is_max:
        next_threshold = None
        progress = 1.0
    else:
        next_threshold = STATUS_THRESHOLDS[index + 1]
        progress = min(1.0, combined / next_threshold)
    return ConsumerStatus(
        name=STATUS_NAMES[index],
        index=index,
        next_threshold=next_threshold,
        progress=progress,
        combined_score=combined,
    )


def compute_streak(tasting_dates: list[date]) -> int:
    """Dias consecutivos (até hoje ou ontem) com ao menos uma degustação registrada. Porta
    `computeStreak` de apps/mobile/src/features/insights.ts para o servidor."""
    days = set(tasting_dates)
    if not days:
        return 0
    today = date.today()
    yesterday = today - timedelta(days=1)
    cursor = today if today in days else yesterday if yesterday in days else None
    if cursor is None:
        return 0
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


class Badge(BaseModel):
    id: str
    label: str
    icon: str
    earned: bool
    hint: str


def compute_badges(
    *,
    total_tastings: int,
    humidor_size: int,
    distinct_countries: int,
    distinct_flavors: int,
    streak_days: int,
) -> list[Badge]:
    """Os mesmos 6 badges de insights.ts (mesmos ids/labels/hints — continuidade visual no app),
    agora calculados no servidor: consistentes entre dispositivos, não manipuláveis pelo cliente."""
    return [
        Badge(
            id="first",
            label="Primeira tragada",
            icon="flame",
            earned=total_tastings >= 1,
            hint="Registre sua 1ª degustação",
        ),
        Badge(
            id="collector",
            label="Colecionador",
            icon="albums",
            earned=humidor_size >= 10,
            hint="10 charutos no humidor",
        ),
        Badge(
            id="traveler",
            label="Viajante",
            icon="earth",
            earned=distinct_countries >= 3,
            hint="Charutos de 3 países",
        ),
        Badge(
            id="critic",
            label="Crítico",
            icon="star",
            earned=total_tastings >= 5,
            hint="5 degustações registradas",
        ),
        Badge(
            id="palate",
            label="Paladar amplo",
            icon="color-palette",
            earned=distinct_flavors >= 5,
            hint="5 sabores diferentes",
        ),
        Badge(
            id="streak",
            label="Ritual",
            icon="calendar",
            earned=streak_days >= 3,
            hint="3 dias seguidos degustando",
        ),
    ]
