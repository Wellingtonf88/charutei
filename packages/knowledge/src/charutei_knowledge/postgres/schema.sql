-- CHARUTEI — schema da fundação (OLTP + KG relacional + vetor).
-- Fonte de verdade do DDL; espelhado pela migração Alembic 0001_initial.
-- KG é relacional (kg_nodes/kg_edges) por decisão de arquitetura: AGE não roda no Supabase
-- gerenciado. A API de grafo (neighbors/harmonizations) é servida por CTE recursivo e fica
-- atrás de KnowledgeGraphRepo — swap p/ AGE/Neo4j na escala sem reescrita.

CREATE EXTENSION IF NOT EXISTS vector;

-- ---------- OLTP ----------
CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY,
    email        TEXT NOT NULL UNIQUE,
    display_name TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bands (
    id           TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_ref    TEXT NOT NULL,
    cigar_id     TEXT,                       -- kg_nodes.id de um nó type='cigar'
    confidence   DOUBLE PRECISION,
    needs_human  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS collections (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       TEXT NOT NULL DEFAULT 'Meu humidor',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS collection_items (
    id            TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    cigar_id      TEXT NOT NULL,
    quantity      INTEGER NOT NULL DEFAULT 1
);
-- Aging (F2.5): quando o charuto entrou no humidor. IF NOT EXISTS mantém apply_schema idempotente.
ALTER TABLE collection_items ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- Degustações (F2.5): rating/sabores/nota por usuário e charuto.
CREATE TABLE IF NOT EXISTS tasting_notes (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cigar_id   TEXT NOT NULL,
    rating     INTEGER NOT NULL,
    flavors    JSONB NOT NULL DEFAULT '[]',
    occasion   TEXT NOT NULL DEFAULT '',
    note       TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tasting_notes_user_cigar ON tasting_notes (user_id, cigar_id);

-- Idempotency-Key de escritas HTTP (ex.: POST /collection/items). Durável e multi-réplica —
-- substitui o `set` em memória que não sobrevivia a restart (débito da Fase 1 do upgrade).
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key        TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Location Intelligence (Fase 4). OLTP, não KG — campos operacionais mutáveis (endereço,
-- confiança), não fatos estáveis do domínio de charutos.
CREATE TABLE IF NOT EXISTS establishments (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    lat        DOUBLE PRECISION NOT NULL,
    lng        DOUBLE PRECISION NOT NULL,
    address    TEXT NOT NULL DEFAULT '',
    city       TEXT NOT NULL DEFAULT '',
    state      TEXT NOT NULL DEFAULT '',
    country    TEXT NOT NULL DEFAULT '',
    est_type   TEXT NOT NULL DEFAULT 'tabacaria',
    source     TEXT NOT NULL DEFAULT '',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Disponibilidade de produto — entidade própria, nunca inferida da mera existência do
-- estabelecimento (prompt mestre §10: "estabelecimento existe" ≠ "produto disponível").
CREATE TABLE IF NOT EXISTS product_availability (
    id               TEXT PRIMARY KEY,
    establishment_id TEXT NOT NULL REFERENCES establishments(id) ON DELETE CASCADE,
    cigar_id         TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'unknown',
    source           TEXT NOT NULL DEFAULT '',
    confidence       DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    price            DOUBLE PRECISION,
    quantity         INTEGER,
    observed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_product_availability_cigar ON product_availability (cigar_id);

-- ---------- Knowledge Graph (relacional) ----------
CREATE TABLE IF NOT EXISTS kg_nodes (
    id    TEXT PRIMARY KEY,            -- canônico: '<type>:<slug>'
    type  TEXT NOT NULL,
    label TEXT NOT NULL,
    props JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_type ON kg_nodes(type);

CREATE TABLE IF NOT EXISTS kg_edges (
    src   TEXT NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,
    dst   TEXT NOT NULL REFERENCES kg_nodes(id) ON DELETE CASCADE,
    rel   TEXT NOT NULL,
    props JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (src, dst, rel)
);
CREATE INDEX IF NOT EXISTS idx_kg_edges_src_rel ON kg_edges(src, rel);

-- Versão do KG: incrementa a cada mudança; invalida o cache semântico (S2).
CREATE TABLE IF NOT EXISTS kg_version (
    id      INTEGER PRIMARY KEY DEFAULT 1,
    version BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT kg_version_singleton CHECK (id = 1)
);
INSERT INTO kg_version (id, version) VALUES (1, 0) ON CONFLICT (id) DO NOTHING;

-- ---------- Vetorial (pgvector) ----------
-- Namespaces por `kind` (ex.: 'cigar_text', 'band_image'). dim flexível: usamos vector
-- sem dimensão fixa aqui e validamos no app; índice HNSW criado por kind quando a dim consolidar.
CREATE TABLE IF NOT EXISTS embeddings (
    kind      TEXT NOT NULL,
    item_id   TEXT NOT NULL,
    embedding vector NOT NULL,
    metadata  JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (kind, item_id)
);
