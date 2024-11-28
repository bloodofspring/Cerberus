from playhouse.migrate import *

from database import db

migrator = SqliteMigrator(db)

migrate(
    migrator.drop_column('SendTime', 'delete_after_execution'),
)

print("migration finished!")
