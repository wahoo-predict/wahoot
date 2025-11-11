"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create miners table
    op.create_table(
        'miners',
        sa.Column('miner_id', sa.String(), nullable=False),
        sa.Column('display_name', sa.Text(), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('miner_id')
    )
    op.create_index(op.f('ix_miners_miner_id'), 'miners', ['miner_id'], unique=False)
    
    # Create events table
    op.create_table(
        'events',
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('lock_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolution_type', sa.String(), nullable=False, server_default='binary'),
        sa.Column('truth_source', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('rule', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index(op.f('ix_events_event_id'), 'events', ['event_id'], unique=False)
    op.create_index(op.f('ix_events_lock_time'), 'events', ['lock_time'], unique=False)
    
    # Create submissions table
    op.create_table(
        'submissions',
        sa.Column('submission_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('miner_id', sa.String(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('prob_yes', sa.Numeric(6, 5), nullable=False),
        sa.Column('manifest_hash', sa.String(), nullable=False),
        sa.Column('sig', sa.Text(), nullable=False),
        sa.CheckConstraint('prob_yes >= 0 AND prob_yes <= 1', name='submissions_prob_yes_check'),
        sa.ForeignKeyConstraint(['event_id'], ['events.event_id'], ),
        sa.ForeignKeyConstraint(['miner_id'], ['miners.miner_id'], ),
        sa.PrimaryKeyConstraint('submission_id')
    )
    op.create_index(op.f('ix_submissions_event_id'), 'submissions', ['event_id'], unique=False)
    op.create_index(op.f('ix_submissions_miner_id'), 'submissions', ['miner_id'], unique=False)
    op.create_index('idx_submissions_event_submitted', 'submissions', ['event_id', 'submitted_at'], unique=False)
    op.create_index('idx_submissions_event_miner_submitted', 'submissions', ['event_id', 'miner_id', 'submitted_at'], unique=False)
    op.create_unique_constraint('uq_submissions_event_manifest', 'submissions', ['event_id', 'manifest_hash'])
    
    # Create resolutions table
    op.create_table(
        'resolutions',
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('outcome', sa.Boolean(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('source', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.event_id'], ),
        sa.PrimaryKeyConstraint('event_id')
    )
    
    # Create brier_archive table
    op.create_table(
        'brier_archive',
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('miner_id', sa.String(), nullable=False),
        sa.Column('brier', sa.Double(), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.event_id'], ),
        sa.ForeignKeyConstraint(['miner_id'], ['miners.miner_id'], ),
        sa.PrimaryKeyConstraint('event_id', 'miner_id')
    )
    
    # Create miner_stats table
    op.create_table(
        'miner_stats',
        sa.Column('miner_id', sa.String(), nullable=False),
        sa.Column('ema_brier', sa.Double(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['miner_id'], ['miners.miner_id'], ),
        sa.PrimaryKeyConstraint('miner_id')
    )
    
    # Create weights table
    op.create_table(
        'weights',
        sa.Column('miner_id', sa.String(), nullable=False),
        sa.Column('weight', sa.Double(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('weight >= 0', name='weights_weight_check'),
        sa.ForeignKeyConstraint(['miner_id'], ['miners.miner_id'], ),
        sa.PrimaryKeyConstraint('miner_id')
    )
    
    # Create submission_alerts table
    op.create_table(
        'submission_alerts',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('miner_id', sa.String(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_submission_alerts_event_id'), 'submission_alerts', ['event_id'], unique=False)
    op.create_index(op.f('ix_submission_alerts_miner_id'), 'submission_alerts', ['miner_id'], unique=False)
    
    # Create ingest_wahoo_buffer table
    op.create_table(
        'ingest_wahoo_buffer',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('inserted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('ingest_wahoo_buffer')
    op.drop_table('submission_alerts')
    op.drop_table('weights')
    op.drop_table('miner_stats')
    op.drop_table('brier_archive')
    op.drop_table('resolutions')
    op.drop_table('submissions')
    op.drop_table('events')
    op.drop_table('miners')

