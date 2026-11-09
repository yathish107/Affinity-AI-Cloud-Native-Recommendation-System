from alembic import op
from app.storage import metadata,versions
revision='001_postgres'
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    metadata.create_all(op.get_bind())
    op.get_bind().execute(versions.insert().values(id=1,version=0))
def downgrade():
    raise RuntimeError('Destructive downgrade disabled. Restore a verified backup into a separate database.')
