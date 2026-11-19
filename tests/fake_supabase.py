"""In-memory stand-in for the supabase-py client (just what the service uses)."""

import re
from types import SimpleNamespace


def _cmp(op, a, b):
    if a is None:
        return False
    a, b = str(a), str(b)
    return {"eq": a == b, "gte": a >= b, "gt": a > b, "lt": a < b, "lte": a <= b}[op]


def _parse_or(expr):
    """'and(c.gte.v,c.lt.v),and(...)' -> list of [(col, op, val), ...]."""
    groups = []
    for inner in re.findall(r"and\(([^()]*)\)", expr):
        conds = []
        for piece in inner.split(","):
            col, op, val = piece.split(".", 2)
            conds.append((col, op, val))
        groups.append(conds)
    return groups


class Query:
    def __init__(self, db, table):
        self.db, self.table_name = db, table
        self.filters = []
        self.action = "select"
        self.payload = None
        self.offset, self._limit = 0, None
        self.on_conflict = None
        self.ignore_duplicates = False
        db.calls.append(self)

    # builders
    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.filters.append(lambda r: _cmp("eq", r.get(col), val) if not isinstance(val, bool) else r.get(col) is val)
        return self

    def neq(self, col, val):
        self.filters.append(lambda r: r.get(col) != val)
        return self

    def in_(self, col, vals):
        vals = {str(v) for v in vals}
        self.filters.append(lambda r: str(r.get(col)) in vals)
        return self

    def gte(self, col, val):
        self.filters.append(lambda r: _cmp("gte", r.get(col), val))
        return self

    def lt(self, col, val):
        self.filters.append(lambda r: _cmp("lt", r.get(col), val))
        return self

    def lte(self, col, val):
        self.filters.append(lambda r: _cmp("lte", r.get(col), val))
        return self

    def or_(self, expr):
        groups = _parse_or(expr)
        self.filters.append(lambda r: any(all(_cmp(op, r.get(c), v) for c, op, v in g) for g in groups))
        return self

    def order(self, *_a, **_k):
        return self

    def range(self, start, end):
        self.offset, self._limit = start, end - start + 1
        return self

    def limit(self, n):
        self._limit = n
        return self

    def delete(self):
        self.action = "delete"
        return self

    def update(self, payload):
        self.action, self.payload = "update", payload
        return self

    def insert(self, payload):
        self.action, self.payload = "insert", payload
        return self

    def upsert(self, payload, on_conflict=None, ignore_duplicates=False, **_k):
        self.action, self.payload = "upsert", payload
        self.on_conflict, self.ignore_duplicates = on_conflict, ignore_duplicates
        return self

    def execute(self):
        if self.table_name in self.db.broken:
            raise RuntimeError(f"relation {self.table_name} does not exist")
        rows = self.db.tables.setdefault(self.table_name, [])
        match = [r for r in rows if all(f(r) for f in self.filters)]
        if self.action == "select":
            end = None if self._limit is None else self.offset + self._limit
            return SimpleNamespace(data=[dict(r) for r in match[self.offset:end]])
        if self.action == "delete":
            for r in match:
                rows.remove(r)
            return SimpleNamespace(data=[dict(r) for r in match])
        if self.action == "update":
            for r in match:
                r.update(self.payload)
            return SimpleNamespace(data=[dict(r) for r in match])
        payloads = self.payload if isinstance(self.payload, list) else [self.payload]
        inserted = []
        for p in payloads:
            if self.on_conflict:
                keys = [k.strip() for k in self.on_conflict.split(",")]
                existing = [r for r in rows if all(str(r.get(k)) == str(p.get(k)) for k in keys)]
                if existing:
                    if not self.ignore_duplicates:
                        existing[0].update(p)
                        inserted.append(dict(existing[0]))
                    continue
            row = dict(p)
            row.setdefault("id", f"{self.table_name}-{len(rows) + 1}")
            rows.append(row)
            inserted.append(dict(row))
        return SimpleNamespace(data=inserted)


class FakeSupabase:
    def __init__(self, tables=None, rpcs=None, broken=()):
        self.tables = {k: [dict(r) for r in v] for k, v in (tables or {}).items()}
        self.rpcs = rpcs or {}
        self.broken = set(broken)
        self.calls = []

    def table(self, name):
        return Query(self, name)

    def rpc(self, name, params):
        fn = self.rpcs.get(name)
        if fn is None:
            raise RuntimeError(f"function {name} does not exist")
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=fn(params)))
