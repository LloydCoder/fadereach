"""Add webhook idempotency storage."""
from alembic import op
revision='002_webhook_idempotency'
down_revision='001_initial'
branch_labels=None
depends_on=None

def upgrade():
    op.execute("CREATE TABLE IF NOT EXISTS webhook_events (id BIGSERIAL PRIMARY KEY, provider TEXT NOT NULL, event_id TEXT NOT NULL, received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), payload JSONB NOT NULL, UNIQUE(provider,event_id));")

def downgrade():
    op.execute("DROP TABLE IF EXISTS webhook_events")
