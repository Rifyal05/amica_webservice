"""allow_null_password

Revision ID: 363082d5666c
Revises: f7f99f3b0608
Create Date: 2025-12-18 06:38:03.426589

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '363082d5666c'
down_revision: Union[str, None] = 'f7f99f3b0608'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Perintah untuk menghapus kewajiban NOT NULL (jadi boleh NULL)
    op.alter_column('users', 'password_hash',
               existing_type=sa.String(length=255),
               nullable=True)

def downgrade():
    # Perintah untuk mengembalikan jadi NOT NULL (jika ingin di-revert)
    op.alter_column('users', 'password_hash',
               existing_type=sa.String(length=255),
               nullable=False)
