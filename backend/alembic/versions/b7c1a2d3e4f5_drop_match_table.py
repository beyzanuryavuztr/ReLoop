"""drop unused match table

Eşleşmeler kalıcı tutulmuyor; motor (reloop.py) istek anında hesaplıyor.
Kullanılmayan 'match' tablosu şemadan kaldırılır (ölü tablo temizliği).

Revision ID: b7c1a2d3e4f5
Revises: 17212ceae133
Create Date: 2026-09-03 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1a2d3e4f5'
down_revision: Union[str, Sequence[str], None] = '17212ceae133'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Kullanılmayan 'match' tablosunu düşür."""
    op.drop_table('match')


def downgrade() -> None:
    """Geri al: 'match' tablosunu yeniden oluştur (baseline şemasıyla aynı)."""
    op.create_table(
        'match',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('demand_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('components', sa.JSON(), nullable=False),
        sa.Column('distance_km', sa.Float(), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['batch.id']),
        sa.ForeignKeyConstraint(['demand_id'], ['demand.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('batch_id', 'demand_id', name='uq_match_pair'),
    )
