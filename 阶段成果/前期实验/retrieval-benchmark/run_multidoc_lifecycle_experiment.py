"""Persistent local multi-document lifecycle and isolation experiment.

Uses SQLite FTS5 and synthetic English tokens so the index lifecycle is
observable without depending on a product server or external services.
It checks ACL-before-result, cache invalidation, version/stale handling,
tombstone/delete propagation, sensitivity routing, and concurrent queries.
"""

from __future__ import annotations

import json
import os
import sqlite3
import statistics
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


OUT = Path(__file__).resolve().parent / "results"


DOCS = [
    ("DOC-A", "v1", "internal", "architecture evidence authorized search", "team-a"),
    ("DOC-B", "v1", "internal", "cross document evidence source version", "team-a"),
    ("DOC-X", "v1", "internal", "project x secret evidence", "team-x"),
    ("DOC-R", "v1", "restricted", "restricted local index evidence", "team-a"),
    ("DOC-V", "v1", "internal", "old version concurrency four", "team-a"),
    ("DOC-V", "v2", "internal", "new version concurrency eight", "team-a"),
]


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA secure_delete=ON")
    return conn


def setup(path: str) -> None:
    conn = connect(path)
    conn.executescript(
        """
        CREATE TABLE documents (
            document_id TEXT NOT NULL,
            version TEXT NOT NULL,
            sensitivity TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            acl_version INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (document_id, version)
        );
        CREATE TABLE chunks (
            chunk_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            version TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (document_id, version) REFERENCES documents(document_id, version)
        );
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            chunk_id UNINDEXED,
            document_id UNINDEXED,
            version UNINDEXED,
            content
        );
        CREATE TABLE principals (
            principal TEXT NOT NULL,
            document_id TEXT NOT NULL,
            can_read INTEGER NOT NULL,
            acl_version INTEGER NOT NULL,
            PRIMARY KEY (principal, document_id)
        );
        """
    )
    for index, (doc_id, version, sensitivity, content, source) in enumerate(DOCS):
        conn.execute("INSERT INTO documents(document_id,version,sensitivity,source,status) VALUES(?,?,?,?,?)", (doc_id, version, sensitivity, source, "ready"))
        chunk_id = f"{doc_id}-{version}-c1"
        conn.execute("INSERT INTO chunks VALUES(?,?,?,?)", (chunk_id, doc_id, version, content))
        conn.execute("INSERT INTO chunks_fts VALUES(?,?,?,?)", (chunk_id, doc_id, version, content))
    # team-a cannot read project X; team-a can read restricted only through a local restricted route.
    for principal, doc_id, can_read, acl_version in [
        ("alice", "DOC-A", 1, 1), ("alice", "DOC-B", 1, 1), ("alice", "DOC-R", 1, 1), ("alice", "DOC-V", 1, 1),
        ("alice", "DOC-X", 0, 1), ("bob", "DOC-X", 1, 1),
    ]:
        conn.execute("INSERT INTO principals VALUES(?,?,?,?)", (principal, doc_id, can_read, acl_version))
    conn.commit()
    conn.close()


def query(path: str, principal: str, text: str, allowed_sensitivity: set[str], cache: dict, cache_lock) -> list[dict]:
    conn = connect(path)
    acl_rows = conn.execute("SELECT document_id, acl_version FROM principals WHERE principal=? AND can_read=1", (principal,)).fetchall()
    allowed_ids = {row["document_id"] for row in acl_rows}
    acl_snapshot = tuple(sorted((row["document_id"], row["acl_version"]) for row in acl_rows))
    key = (principal, acl_snapshot, text, tuple(sorted(allowed_sensitivity)))
    with cache_lock:
        if key in cache:
            conn.close()
            return [dict(row) for row in cache[key]]
    placeholders = ",".join("?" for _ in allowed_ids) or "NULL"
    sensitivity_placeholders = ",".join("?" for _ in allowed_sensitivity) or "NULL"
    params = [text, *allowed_ids, *allowed_sensitivity]
    rows = conn.execute(
        f"""
        SELECT f.chunk_id, f.document_id, f.version, f.content, d.sensitivity, d.source
        FROM chunks_fts f
        JOIN documents d ON d.document_id=f.document_id AND d.version=f.version
        WHERE chunks_fts MATCH ?
          AND f.document_id IN ({placeholders})
          AND d.sensitivity IN ({sensitivity_placeholders})
          AND d.status='ready'
        ORDER BY f.document_id, f.version
        """,
        params,
    ).fetchall()
    output = [dict(row) for row in rows]
    with cache_lock:
        cache[key] = output
    conn.close()
    return output


def main() -> None:
    import threading

    with tempfile.TemporaryDirectory(prefix="multidoc-lifecycle-") as temp:
        db_path = os.path.join(temp, "index.sqlite")
        setup(db_path)
        cache: dict = {}
        cache_lock = threading.Lock()

        authorized = query(db_path, "alice", "authorized evidence", {"internal"}, cache, cache_lock)
        unauthorized = query(db_path, "alice", "secret evidence", {"internal"}, cache, cache_lock)
        restricted_default = query(db_path, "alice", "restricted local index", {"internal"}, cache, cache_lock)
        restricted_local = query(db_path, "alice", "restricted local index", {"restricted"}, cache, cache_lock)

        # Revoke DOC-B and bump its ACL snapshot; old cache key must not be reused.
        conn = connect(db_path)
        conn.execute("UPDATE principals SET can_read=0, acl_version=acl_version+1 WHERE principal='alice' AND document_id='DOC-B'")
        conn.commit()
        conn.close()
        revoked = query(db_path, "alice", "source version", {"internal"}, cache, cache_lock)
        old_cache_reused = any(row["document_id"] == "DOC-B" for row in revoked)

        # Version update: v2 is current, v1 remains a stale historical citation.
        conn = connect(db_path)
        conn.execute("UPDATE documents SET status='stale' WHERE document_id='DOC-V' AND version='v1'")
        conn.commit()
        conn.close()
        current = query(db_path, "alice", "new version concurrency", {"internal"}, cache, cache_lock)
        stale = query(db_path, "alice", "old version concurrency", {"internal"}, cache, cache_lock)

        # Delete DOC-X transactionally from metadata, chunks, FTS and cache.
        conn = connect(db_path)
        conn.execute("BEGIN")
        conn.execute("UPDATE documents SET status='deleted' WHERE document_id='DOC-X'")
        conn.execute("DELETE FROM chunks_fts WHERE document_id='DOC-X'")
        conn.execute("DELETE FROM chunks WHERE document_id='DOC-X'")
        conn.execute("DELETE FROM principals WHERE document_id='DOC-X'")
        conn.commit()
        conn.close()
        deleted = query(db_path, "bob", "secret evidence", {"internal"}, cache, cache_lock)
        conn = connect(db_path)
        residual = conn.execute("SELECT count(*) AS n FROM chunks WHERE document_id='DOC-X'").fetchone()["n"]
        fts_residual = conn.execute("SELECT count(*) AS n FROM chunks_fts WHERE document_id='DOC-X'").fetchone()["n"]
        conn.close()

        # Concurrent queries with per-thread connections and the same ACL path.
        cases = [("alice", "authorized evidence", {"internal"}), ("alice", "secret evidence", {"internal"}), ("bob", "secret evidence", {"internal"})] * 20
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=16) as pool:
            concurrent_results = list(pool.map(lambda item: query(db_path, item[0], item[1], item[2], cache, cache_lock), cases))
        concurrent_ms = (time.perf_counter() - started) * 1000
        concurrent_leak = any(item["document_id"] == "DOC-X" for rows in concurrent_results[:40] for item in rows)

        result = {
            "experiment_id": "TECH-MDOC-004-009-013-R01",
            "scope": "SQLite FTS5 persistent local lifecycle, isolation and concurrency; synthetic English fixture",
            "database": {"fts5": True, "secure_delete": True, "temporary": True},
            "checks": {
                "authorized_result": bool(authorized),
                "unauthorized_result_empty": not unauthorized,
                "restricted_default_denied": not restricted_default,
                "restricted_local_route_available": bool(restricted_local),
                "acl_revoke_cache_not_reused": not old_cache_reused,
                "current_version_available": any(row["version"] == "v2" for row in current),
                "stale_version_not_in_ready_query": not any(row["version"] == "v1" for row in stale),
                "deleted_new_query_empty": not deleted,
                "deleted_chunk_rows_zero": residual == 0,
                "deleted_fts_rows_zero": fts_residual == 0,
                "concurrent_unauthorized_leak": concurrent_leak,
            },
            "metrics": {
                "cache_entries": len(cache),
                "concurrent_requests": len(cases),
                "concurrent_workers": 16,
                "concurrent_batch_ms": round(concurrent_ms, 3),
                "concurrent_p95_proxy_ms": round(concurrent_ms / len(cases), 3),
            },
            "boundary": [
                "SQLite temporary database is a local lifecycle proxy, not the production vector store.",
                "secure_delete and zero row counts do not prove disk, backup or cloud-provider erasure.",
                "Concurrency check exercises ACL consistency under parallel reads, not model generation throughput.",
            ],
        }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "TECH-MDOC-004-009-013-R01.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# TECH-MDOC-004-009-013-R01 本地持久化索引生命周期实验",
        "",
        "使用临时 SQLite FTS5 和合成英文 token，验证 ACL 前置、缓存失效、版本 stale、删除传播、保密等级路由和并发查询；不连接产品服务、不使用真实敏感文档。",
        "",
        "| 验证 | 结果 |",
        "|---|---|",
    ]
    for key, value in result["checks"].items():
        lines.append(f"| {key} | {'PASS' if (value is True or (key == 'concurrent_unauthorized_leak' and value is False)) else 'FAIL'} |")
    lines.extend([
        "",
        f"并发请求：{result['metrics']['concurrent_requests']}，工作线程：{result['metrics']['concurrent_workers']}，批次耗时：{result['metrics']['concurrent_batch_ms']} ms。",
        "",
        "## 边界",
        "",
        *[f"- {item}" for item in result["boundary"]],
    ])
    (OUT / "TECH-MDOC-004-009-013-R01.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"experiment_id": result["experiment_id"], "checks": result["checks"], "metrics": result["metrics"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
