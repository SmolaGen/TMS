"""add user_role to drivers

Revision ID: add_user_role_01
Revises: add_address_fields_01
Create Date: 2026-01-06 15:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_user_role_01'
down_revision = 'add_address_fields_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Создаём ENUM тип
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
                CREATE TYPE user_role AS ENUM ('driver', 'dispatcher', 'admin', 'pending');
            END IF;
        END $$;
    """)
    
    # 2. Добавляем колонку к таблице drivers
    op.add_column('drivers', 
        sa.Column('role', 
            sa.Enum('driver', 'dispatcher', 'admin', 'pending', name='user_role'), 
            server_default='pending', 
            nullable=False,
            comment='Роль пользователя в системе'
        )
    )


def downgrade() -> None:
    op.drop_column('drivers', 'role')
    op.execute("DROP TYPE IF EXISTS user_role;")
