"""empty message

Revision ID: 3ec02016e564
Revises: feb38eaa262b
Create Date: 2018-10-22 22:07:22.634036

"""

# revision identifiers, used by Alembic.
revision = '3ec02016e564'
down_revision = 'feb38eaa262b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('sessions')
    op.add_column('service_connection', sa.Column('data_path', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('service_connection', 'data_path')
    op.create_table('sessions',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('session_id', sa.VARCHAR(length=255), nullable=True),
    sa.Column('data', sa.BLOB(), nullable=True),
    sa.Column('expiry', sa.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_id')
    )
    # ### end Alembic commands ###
