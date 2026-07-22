"""enable_rls_on_all_tables

Revision ID: 0fcd29ee36ba
Revises: 45b017037299
Create Date: 2026-07-22 11:18:40.593753

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0fcd29ee36ba'
down_revision: Union[str, Sequence[str], None] = '45b017037299'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE topics ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE articles ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE article_topics ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE oil_prices ENABLE ROW LEVEL SECURITY;")

def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE topics DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE articles DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE article_topics DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE oil_prices DISABLE ROW LEVEL SECURITY;")
