import os
from functools import lru_cache
from typing import List

from loguru import logger

from clippy.constants import ROOT_DIR
from clippy.dm.db_utils import Database


class DatabaseInterface:
    """
    since DB eventually will move to SQL thing and not TinyDB, this is just so I can keep a database in

    not sure if this should be part of State
    in which case will need to prefix things with _ for reflex to use as backend

    """

    _database_path: str = f"{ROOT_DIR}/data/db/db.json"
    _database = Database(_database_path)
    db_query = _database.Query()
    db_table_id_status = _database.table("id_status")
    # at some point ill have to make db_table_task coincide with the data dir, at present it doesnt
    db_table_task = _database.table("task")

    def dev_setup():
        if os.environ.get("PROD", False):
            return

        DatabaseInterface._database.drop_table("id_status")
        DatabaseInterface._database.drop_table("approved")
        logger.info("dropped approved table")

    def update_id_status(self, obj_id: str, value: str) -> List[int]:
        logger.info(f"updating id: {obj_id} to {value}")
        doc_id = self.db_table_id_status.upsert({"id": obj_id, "status": value}, self.db_query.id == obj_id)
        return doc_id

    def get_approval_status(self, obj_id: str) -> str:
        db_entry = self.db_table_id_status.search(self.db_query.id == obj_id)
        if db_entry:
            return db_entry[0]["status"]
        return None

    def remove_obj_id(self, obj_id: str, table_name: str = "id_status") -> None:
        self._database.table(table_name).remove(self.db_query.id == obj_id)

    @classmethod
    def check_db(cls, *args, **kwargs) -> None:
        # prevent circular import
        from trajlab.state import TaskState

        logger.info(f"checking db... with current task {TaskState.task_id}")
        return None


db_interface = DatabaseInterface()
