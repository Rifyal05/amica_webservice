"""baseline

Revision ID: a3539fb9ebd2
Revises: 
Create Date: 2025-11-27 07:17:12.169827

"""
from typing import Sequence, Union

from alembic import op # type: ignore
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3539fb9ebd2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
