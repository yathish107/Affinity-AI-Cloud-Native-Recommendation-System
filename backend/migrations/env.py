import os
from alembic import context
from sqlalchemy import create_engine
from app.storage import metadata
with create_engine(os.environ['DATABASE_URL']).connect() as connection:
    context.configure(connection=connection,target_metadata=metadata)
    with context.begin_transaction():context.run_migrations()
