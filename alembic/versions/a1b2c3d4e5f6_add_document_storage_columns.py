"""Add document storage columns

Revision ID: a1b2c3d4e5f6
Revises: 49f7ddf9c13c
Create Date: 2026-09-19 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '49f7ddf9c13c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns safely
    op.add_column('documents', sa.Column('extracted_text', sa.Text(), nullable=True, comment='Extracted plaintext cached in DB'))
    op.add_column('documents', sa.Column('file_data', sa.LargeBinary(), nullable=True, comment='Raw file bytes cached in DB'))


def downgrade() -> None:
    op.drop_column('documents', 'file_data')
    op.drop_column('documents', 'extracted_text')
