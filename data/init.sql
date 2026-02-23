-- CATERYA Database Initialization
-- Author: Ary HH (Caterya Tech)

CREATE TABLE IF NOT EXISTS agent_runs (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) NOT NULL,
    task TEXT NOT NULL,
    result TEXT,
    ethics_verdict VARCHAR(20),
    duration_ms FLOAT,
    audit_hash VARCHAR(32),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    invoice_id VARCHAR(100) UNIQUE,
    chain VARCHAR(20),
    amount DECIMAL(20, 8),
    currency VARCHAR(10),
    to_address VARCHAR(100),
    memo TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    tx_hash VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    verified_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50),
    verdict VARCHAR(20),
    flags JSONB,
    audit_hash VARCHAR(32),
    context JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_agent_runs_agent_id ON agent_runs(agent_id);
CREATE INDEX idx_agent_runs_created_at ON agent_runs(created_at);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_audit_log_verdict ON audit_log(verdict);
