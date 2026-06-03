"""create usuarios and sessoes tables

Revision ID: 3745582af902
Revises: 
Create Date: 2026-05-30 01:10:28.002388
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '3745582af902'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('usuarios',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('nome', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('senha_hash', sa.String(length=255), nullable=False),
        sa.Column('perfil', sa.Enum('ADMIN', 'SECRETARIA', 'PROFESSOR', 'RESPONSAVEL', name='perfil'), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=False),
        sa.Column('ultimo_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_usuarios_email'),
    )
    op.create_table('sessoes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('usuario_id', sa.Uuid(), nullable=False),
        sa.Column('refresh_token_jti', sa.String(length=36), nullable=False),
        sa.Column('ip', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name='fk_sessoes_usuario_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('refresh_token_jti', name='uq_sessoes_refresh_token_jti'),
    )


def downgrade() -> None:
    op.drop_table('sessoes')
    op.drop_table('usuarios')
    op.execute('DROP TYPE IF EXISTS perfil')
