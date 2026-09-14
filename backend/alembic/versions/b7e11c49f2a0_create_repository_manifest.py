"""create repository manifest

Revision ID: b7e11c49f2a0
Revises: a43677706ad4
Create Date: 2026-09-14 09:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e11c49f2a0'
down_revision: Union[str, Sequence[str], None] = 'a43677706ad4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('repository_manifest',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('repository_id', sa.Integer(), nullable=False),
    sa.Column('file_path', sa.String(), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('index_status', sa.String(), nullable=False),
    sa.Column('skip_reason', sa.String(), nullable=True),
    sa.Column('indexed_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('repository_id', 'file_path', name='uq_repository_manifest_repository_file')
    )
    op.create_index(op.f('ix_repository_manifest_id'), 'repository_manifest', ['id'], unique=False)
    op.create_index(op.f('ix_repository_manifest_repository_id'), 'repository_manifest', ['repository_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_repository_manifest_repository_id'), table_name='repository_manifest')
    op.drop_index(op.f('ix_repository_manifest_id'), table_name='repository_manifest')
    op.drop_table('repository_manifest')
