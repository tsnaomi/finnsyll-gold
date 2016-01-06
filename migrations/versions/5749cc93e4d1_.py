"""empty message

Revision ID: 5749cc93e4d1
Revises: 38843212685d
Create Date: 2015-08-26 13:30:08.078255

"""

# revision identifiers, used by Alembic.
revision = '5749cc93e4d1'
down_revision = '38843212685d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('Poem',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=80, convert_unicode=True), nullable=True),
    sa.Column('poet', sa.Enum(u'Erkko', u'Hellaakoski', u'Kaatra', u'Kailas', u'Koskenniemi', u'Kramsu', u'Leino', u'L\xf6nnrot', u'Siljo', name='POET'), nullable=True),
    sa.Column('portion', sa.Integer(), nullable=True),
    sa.Column('ebook_number', sa.Integer(), nullable=True),
    sa.Column('date_released', sa.DateTime(), nullable=True),
    sa.Column('last_updated', sa.DateTime(), nullable=True),
    sa.Column('tokenized_poem', sa.PickleType(), nullable=True),
    sa.Column('reviewed', sa.Boolean(), nullable=True),
    sa.Column('sequence_count', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('Variation',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('token_id', sa.Integer(), nullable=True),
    sa.Column('poem_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['poem_id'], ['Poem.id'], ),
    sa.ForeignKeyConstraint(['token_id'], ['Token.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('Sequence',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('variation_id', sa.Integer(), nullable=True),
    sa.Column('sequence', sa.String(length=10, convert_unicode=True), nullable=True),
    sa.Column('html', sa.String(length=80, convert_unicode=True), nullable=True),
    sa.Column('split', sa.Enum('split', 'join', 'unknown', name='SPLIT'), nullable=True),
    sa.Column('scansion', sa.Enum('S', 'W', 'SW', 'WS', 'SS', 'WW', 'UNK', name='SCANSION'), nullable=True),
    sa.Column('is_odd', sa.Boolean(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['variation_id'], ['Variation.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column(u'Token', sa.Column('is_aamulehti', sa.Boolean(), nullable=True))
    op.add_column(u'Token', sa.Column('is_gutenberg', sa.Boolean(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column(u'Token', 'is_gutenberg')
    op.drop_column(u'Token', 'is_aamulehti')
    op.drop_table('Sequence')
    op.drop_table('Variation')
    op.drop_table('Poem')
    ### end Alembic commands ###
