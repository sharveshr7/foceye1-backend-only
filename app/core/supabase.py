import logging
from typing import Any, Dict, List, Optional, Union
from app.core.config import settings

logger = logging.getLogger("foceye.supabase")

# In-memory mock storage for local resilient testing
_mock_db: Dict[str, List[Dict[str, Any]]] = {
    "profiles": [],
    "patients": [],
    "therapy_sessions": [],
    "calibration_records": [],
    "devices": []
}


class MockSupabaseClient:
    """Resilient in-memory mock client when live Supabase credentials are not connected."""
    
    def __init__(self):
        self.db = _mock_db

    def table(self, table_name: str):
        return MockTableQuery(table_name, self.db)


class MockTableQuery:
    def __init__(self, table_name: str, db: Dict[str, List[Dict[str, Any]]]):
        self.table_name = table_name
        self.db = db
        if self.table_name not in self.db:
            self.db[self.table_name] = []
        self._filter_col = None
        self._filter_val = None

    def select(self, *args, **kwargs):
        return self

    def eq(self, column: str, value: Any):
        self._filter_col = column
        self._filter_val = value
        return self

    def upsert(self, record: Union[Dict[str, Any], List[Dict[str, Any]]]):
        items = record if isinstance(record, list) else [record]
        self._pending_upsert = items
        return self

    def insert(self, record: Union[Dict[str, Any], List[Dict[str, Any]]]):
        items = record if isinstance(record, list) else [record]
        self._pending_insert = items
        return self

    def update(self, updates: Dict[str, Any]):
        self._pending_update = updates
        return self

    def delete(self):
        self._pending_delete = True
        return self

    def execute(self):
        if hasattr(self, "_pending_upsert") and self._pending_upsert:
            res = []
            for item in self._pending_upsert:
                item_id = item.get("id")
                found = False
                if item_id:
                    for existing in self.db[self.table_name]:
                        if existing.get("id") == item_id:
                            existing.update(item)
                            res.append(existing)
                            found = True
                            break
                if not found:
                    self.db[self.table_name].append(item)
                    res.append(item)
            self._pending_upsert = []
            return MockResponse(res)

        if hasattr(self, "_pending_insert") and self._pending_insert:
            for item in self._pending_insert:
                self.db[self.table_name].append(item)
            res = list(self._pending_insert)
            self._pending_insert = []
            return MockResponse(res)

        if hasattr(self, "_pending_update") and self._pending_update:
            updated = []
            for item in self.db[self.table_name]:
                if self._filter_col is None or item.get(self._filter_col) == self._filter_val:
                    item.update(self._pending_update)
                    updated.append(item)
            self._pending_update = None
            return MockResponse(updated)

        if hasattr(self, "_pending_delete") and self._pending_delete:
            initial_len = len(self.db[self.table_name])
            if self._filter_col:
                self.db[self.table_name] = [
                    x for x in self.db[self.table_name] 
                    if x.get(self._filter_col) != self._filter_val
                ]
            deleted_count = initial_len - len(self.db[self.table_name])
            self._pending_delete = False
            return MockResponse([{"deleted": deleted_count}])

        records = self.db[self.table_name]
        if self._filter_col is not None:
            records = [r for r in records if r.get(self._filter_col) == self._filter_val]
        return MockResponse(records)


class MockResponse:
    def __init__(self, data: Any):
        self.data = data


def get_supabase_client():
    """Initializes the real Supabase client or falls back to in-memory mock."""
    key = settings.get_supabase_key()
    if (
        settings.SUPABASE_URL 
        and "mock" not in settings.SUPABASE_URL 
        and key 
        and "mock" not in key
    ):
        try:
            from supabase import create_client, Client
            client: Client = create_client(settings.SUPABASE_URL, key)
            logger.info(f"Connected to live Supabase project: {settings.SUPABASE_URL}")
            return client
        except Exception as e:
            logger.warning(f"Could not connect to live Supabase, using mock fallback: {e}")
            return MockSupabaseClient()
    return MockSupabaseClient()


supabase = get_supabase_client()
