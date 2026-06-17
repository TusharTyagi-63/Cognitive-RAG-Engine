import os

# Set all the environment variables BEFORE anything else
os.environ["POSTGRES_USER"] = "postgres.lneaumecnqrbywitjkya"
os.environ["POSTGRES_PASSWORD"] = "tyagitushar"
os.environ["POSTGRES_HOST"] = "aws-1-ap-southeast-1.pooler.supabase.com"
os.environ["POSTGRES_PORT"] = "5432"  # Session pooler port for migrations!
os.environ["POSTGRES_DB"] = "postgres"

from alembic.config import Config
from alembic import command

alembic_cfg = Config("alembic.ini")
command.upgrade(alembic_cfg, "head")
print("Migrations completed successfully ON SUPABASE!")
