from alembic import op
import sqlalchemy as sa
revision='002_quarantine'
down_revision='001_postgres'
branch_labels=None
depends_on=None
def upgrade():
    # Initial checkpoint imported live metadata; checkfirst also supports those fresh installs.
    from app.storage import dead_letters
    dead_letters.create(op.get_bind(),checkfirst=True)
def downgrade():raise RuntimeError('Preserve quarantine data; restore a separate verified backup for rollback.')
