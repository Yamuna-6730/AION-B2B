-- Business DNA Results Table
-- Stores deep intelligence profiles produced by the Business DNA Agent.
-- One row per (mission_id, website) pair.

CREATE TABLE IF NOT EXISTS business_dna_results (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id                      UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    company_name                    TEXT NOT NULL,
    website                         TEXT NOT NULL,
    industry                        TEXT,
    company_type                    TEXT,
    country                         TEXT,
    business_summary                TEXT,
    estimated_company_size          TEXT,
    estimated_ai_maturity           TEXT,
    technology_signals              TEXT[]  DEFAULT '{}',
    digital_transformation_signals  TEXT[]  DEFAULT '{}',
    buying_personas                 TEXT[]  DEFAULT '{}',
    likely_use_cases                TEXT[]  DEFAULT '{}',
    business_strengths              TEXT[]  DEFAULT '{}',
    business_risks                  TEXT[]  DEFAULT '{}',
    confidence                      FLOAT   DEFAULT 0.0,
    reasoning                       TEXT,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_business_dna_mission_website UNIQUE (mission_id, website)
);

-- Index for fast lookup by mission
CREATE INDEX IF NOT EXISTS idx_business_dna_mission_id ON business_dna_results (mission_id);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_business_dna_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_business_dna_updated_at
BEFORE UPDATE ON business_dna_results
FOR EACH ROW EXECUTE FUNCTION update_business_dna_updated_at();


-- ============================================================
-- Recommendation Results Table
-- Stores scored and ranked companies produced by the Recommendation Agent.
-- One row per (mission_id, website) pair.

CREATE TABLE IF NOT EXISTS recommendation_results (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id              UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    company_name            TEXT NOT NULL,
    website                 TEXT NOT NULL,
    priority_score          FLOAT   DEFAULT 0.0,
    priority                TEXT    DEFAULT 'MEDIUM',
    rank                    INTEGER DEFAULT 0,
    confidence              FLOAT   DEFAULT 0.0,
    why_selected            TEXT,
    strengths               TEXT[]  DEFAULT '{}',
    risks                   TEXT[]  DEFAULT '{}',
    recommended_personas    TEXT[]  DEFAULT '{}',
    recommended_use_cases   TEXT[]  DEFAULT '{}',
    next_action             TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_recommendation_mission_website UNIQUE (mission_id, website)
);

-- Index for fast lookup by mission
CREATE INDEX IF NOT EXISTS idx_recommendation_mission_id ON recommendation_results (mission_id);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_recommendation_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_recommendation_updated_at
BEFORE UPDATE ON recommendation_results
FOR EACH ROW EXECUTE FUNCTION update_recommendation_updated_at();
