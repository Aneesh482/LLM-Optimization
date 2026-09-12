"""Unit tests for JSONCompressor (SmartCrusher-style JSON compression)."""

from __future__ import annotations

import json
import pytest
from app.services.compressors.json_compressor import JSONCompressor


@pytest.fixture
def compressor() -> JSONCompressor:
    return JSONCompressor()


def test_compress_empty_string(compressor: JSONCompressor):
    res = compressor.compress("")
    assert res.compressed_content == ""
    assert res.original_size == 0
    assert res.metadata.get("strategy") == "empty"


def test_compress_invalid_json(compressor: JSONCompressor):
    invalid = "{ this is not valid json :"
    res = compressor.compress(invalid)
    assert res.metadata.get("strategy") == "fallback_invalid_json"
    assert res.compressed_size <= res.original_size


def test_compress_small_json_not_crushed(compressor: JSONCompressor):
    # Under minimum threshold (< 5 items) -> minified verbatim without losing data
    data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    raw = json.dumps(data, indent=2)
    res = compressor.compress(raw)
    assert res.metadata.get("strategy") == "minified_verbatim"
    parsed = json.loads(res.compressed_content)
    assert parsed == data
    assert res.compression_ratio <= 1.0


def test_compress_large_uniform_records(compressor: JSONCompressor):
    # 50 records of similar structure
    records = [
        {"id": i, "status": "active", "response_time_ms": 20.0 + (i % 5), "user_id": f"usr_{i}"}
        for i in range(50)
    ]
    raw = json.dumps(records, indent=2)
    res = compressor.compress(raw, max_representatives=3)

    assert res.content_type == "json"
    assert res.compression_ratio < 0.6  # Significant compression
    assert res.estimated_tokens_saved > 0

    parsed = json.loads(res.compressed_content)
    assert "schema" in parsed
    assert "summary" in parsed
    assert "representative_records" in parsed
    assert "original_count" in parsed
    assert parsed["original_count"] == 50

    # Schema contains keys
    assert "id" in parsed["schema"]
    assert "status" in parsed["schema"]
    assert "response_time_ms" in parsed["schema"]

    # Statistical summary
    num_summary = parsed["summary"]["numerical_fields"]
    assert "response_time_ms" in num_summary
    assert num_summary["response_time_ms"]["count"] == 50
    assert num_summary["response_time_ms"]["min"] == 20.0

    # Representatives
    assert len(parsed["representative_records"]) <= 3


def test_detect_anomalies_and_outliers(compressor: JSONCompressor):
    # 40 normal records and 2 anomalous records
    records = [
        {"id": i, "status": "success", "latency": 15.0, "error": None}
        for i in range(40)
    ]
    # Anomaly 1: Failure error status
    records.append({"id": 41, "status": "FAILED", "latency": 550.0, "error": "DatabaseTimeout"})
    # Anomaly 2: Extra fields and missing latency
    records.append({"id": 42, "status": "success", "unexpected_payload": "crash_dump"})

    raw = json.dumps(records)
    res = compressor.compress(raw, min_records_for_compression=10)
    parsed = json.loads(res.compressed_content)

    assert "anomalies" in parsed
    assert len(parsed["anomalies"]) >= 2

    anomaly_ids = [a["id"] for a in parsed["anomalies"]]
    assert 41 in anomaly_ids
    assert 42 in anomaly_ids

    # Check that anomaly reasons are populated
    for anom in parsed["anomalies"]:
        assert "_anomaly_reasons" in anom
        assert len(anom["_anomaly_reasons"]) > 0


def test_compress_primitive_numerical_list(compressor: JSONCompressor):
    numbers = [i * 2 for i in range(100)]
    raw = json.dumps(numbers)
    res = compressor.compress(raw, min_records_for_compression=10)

    assert res.compression_ratio < 0.5
    parsed = json.loads(res.compressed_content)
    assert parsed["type"] == "numerical_array"
    assert parsed["original_count"] == 100
    assert parsed["summary"]["min"] == 0
    assert parsed["summary"]["max"] == 198


def test_compress_nested_dict_with_arrays(compressor: JSONCompressor):
    data = {
        "status": 200,
        "page": 1,
        "items": [
            {"item_id": i, "price": 10.0 + i, "category": "electronics"}
            for i in range(30)
        ],
    }
    raw = json.dumps(data, indent=2)
    res = compressor.compress(raw, min_records_for_compression=5)

    assert res.compression_ratio < 0.7
    parsed = json.loads(res.compressed_content)
    assert parsed["status"] == 200
    assert parsed["page"] == 1
    assert isinstance(parsed["items"], dict)
    assert "schema" in parsed["items"]
    assert "representative_records" in parsed["items"]
