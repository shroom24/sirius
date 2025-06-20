"""Remove friends

Revision ID: 89a031bd9657
Revises: 44c4368c2db1
Create Date: 2023-07-04 18:44:13.041005

"""

# revision identifiers, used by Alembic.
revision = "89a031bd9657"
down_revision = "44c4368c2db1"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("twitter_o_auth", "last_friend_refresh")
    op.drop_column("twitter_o_auth", "friends")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "twitter_o_auth",
        sa.Column("friends", postgresql.BYTEA(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "twitter_o_auth",
        sa.Column(
            "last_friend_refresh",
            postgresql.TIMESTAMP(),
            autoincrement=False,
            nullable=True,
        ),
    )
    # ### end Alembic commands ###
