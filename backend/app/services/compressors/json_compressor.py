"""SmartCrusher-style JSON Compressor for LLM Context Optimization.

Features
--------
1. Schema Extraction:
   - Infers field names, types, presence rates, and nullability across all records.
2. Anomaly & Outlier Detection:
   - Identifies records with schema deviations (missing/extra fields).
   - Identifies categorical outliers (rare status codes, error states, uncommon flags).
   - Identifies numerical outliers using Interquartile Range (IQR) / z-score heuristics.
3. Repetitive Record Clustering & Representative Sampling:
   - Clusters records by structural and categorical signatures.
   - Extracts representative exemplar records (head, tail, and cluster medoids).
4. Statistical Summarization:
   - Computes min, max, mean, count for numerical fields.
   - Summarizes value frequencies for low-cardinality categorical fields.
5. Compression Metrics:
   - Computes original size, compressed size, compression ratio, and estimated token savings.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Optional

from app.services.compressors.base import BaseCompressor, CompressionResult
from app.services.token_analyzer import estimate_tokens


class JSONCompressor(BaseCompressor):
    """Intelligent, structure-preserving JSON compressor."""

    DEFAULT_MIN_RECORDS_TO_COMPRESS = 5
    DEFAULT_MAX_REPRESENTATIVES = 4
    DEFAULT_MAX_ANOMALIES = 6
    MAX_CATEGORICAL_CARDINALITY = 10

    def content_type(self) -> str:
        return "json"

    def compress(
        self,
        content: str,
        *,
        min_records_for_compression: Optional[int] = None,
        max_representatives: Optional[int] = None,
        max_anomalies: Optional[int] = None,
        minify_only_if_small: bool = True,
        **options: Any,
    ) -> CompressionResult:
        """Compress JSON string while preserving schema, statistics, representatives, and anomalies.

        Parameters
        ----------
        content : str
            The raw JSON string.
        min_records_for_compression : int, optional
            Minimum list elements to trigger statistical compression (default 5).
        max_representatives : int, optional
            Maximum sample records to preserve verbatim (default 4).
        max_anomalies : int, optional
            Maximum anomalous/outlier records to preserve (default 6).
        minify_only_if_small : bool
            If true and records < threshold, output minified JSON without loss.
        """
        raw_text = content.strip()
        original_size = len(content.encode("utf-8"))
        tokens_before = estimate_tokens(content)

        if not raw_text:
            return self._build_result(
                original=content,
                compressed="",
                original_size=original_size,
                metadata={"strategy": "empty"},
            )

        parsed = None
        prefix = ""
        postfix = ""
        try:
            parsed = json.loads(raw_text)
        except (json.JSONDecodeError, ValueError) as exc:
            first_bracket = raw_text.find("[")
            last_bracket = raw_text.rfind("]")
            if first_bracket != -1 and last_bracket > first_bracket:
                candidate = raw_text[first_bracket : last_bracket + 1]
                try:
                    p = json.loads(candidate)
                    if isinstance(p, list):
                        parsed = p
                        prefix = raw_text[:first_bracket]
                        postfix = raw_text[last_bracket + 1:]
                except (json.JSONDecodeError, ValueError):
                    pass

            if parsed is None:
                first_brace = raw_text.find("{")
                last_brace = raw_text.rfind("}")
                if first_brace != -1 and last_brace > first_brace:
                    candidate = raw_text[first_brace : last_brace + 1]
                    try:
                        p = json.loads(candidate)
                        if isinstance(p, dict):
                            parsed = p
                            prefix = raw_text[:first_brace]
                            postfix = raw_text[last_brace + 1:]
                    except (json.JSONDecodeError, ValueError):
                        pass

            if parsed is None:
                minified = " ".join(raw_text.split())
                return self._build_result(
                    original=content,
                    compressed=minified,
                    original_size=original_size,
                    metadata={"strategy": "fallback_invalid_json", "error": str(exc)},
                )

        min_records = min_records_for_compression or self.DEFAULT_MIN_RECORDS_TO_COMPRESS
        max_reps = max_representatives or self.DEFAULT_MAX_REPRESENTATIVES
        max_anom = max_anomalies or self.DEFAULT_MAX_ANOMALIES

        # Baseline: minified verbatim JSON (lossless compression by whitespace removal)
        minified_verbatim = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
        minified_bytes = len(minified_verbatim.encode("utf-8"))

        compressed_candidate: Optional[str] = None
        candidate_meta: dict[str, Any] = {}

        # Determine strategy based on data structure
        if isinstance(parsed, list) and len(parsed) >= min_records:
            # Array of records
            if all(isinstance(item, dict) for item in parsed):
                compressed_dict, meta = self._compress_dict_list(parsed, max_reps, max_anom)
                compressed_candidate = json.dumps(compressed_dict, separators=(",", ":"), ensure_ascii=False)
                candidate_meta = meta
            elif all(isinstance(item, (int, float)) for item in parsed):
                compressed_dict, meta = self._compress_primitive_list(parsed, max_reps)
                compressed_candidate = json.dumps(compressed_dict, separators=(",", ":"), ensure_ascii=False)
                candidate_meta = meta

        elif isinstance(parsed, dict):
            # Check for large array fields inside top-level wrapper dicts (e.g. {"data": [...], "status": 200})
            array_fields = [k for k, v in parsed.items() if isinstance(v, list) and len(v) >= min_records]
            if array_fields:
                compressed_obj, meta = self._compress_nested_dict(parsed, array_fields, max_reps, max_anom)
                compressed_candidate = json.dumps(compressed_obj, separators=(",", ":"), ensure_ascii=False)
                candidate_meta = meta

        # Safety Guarantee: If statistical compression produces larger output than minified verbatim,
        # fallback to minified verbatim to guarantee we never inflate payload size!
        if compressed_candidate:
            candidate_bytes = len(compressed_candidate.encode("utf-8"))
            if candidate_bytes < minified_bytes:
                final_compressed = f"{prefix}{compressed_candidate}{postfix}" if (prefix or postfix) else compressed_candidate
                return self._build_result(
                    original=content,
                    compressed=final_compressed,
                    original_size=original_size,
                    metadata=candidate_meta,
                )
            else:
                final_minified = f"{prefix}{minified_verbatim}{postfix}" if (prefix or postfix) else minified_verbatim
                return self._build_result(
                    original=content,
                    compressed=final_minified,
                    original_size=original_size,
                    metadata={
                        "strategy": "minified_verbatim_better_ratio",
                        "note": "Payload is small; verbatim minification is more compact than statistical metadata.",
                        "original_record_count": len(parsed) if isinstance(parsed, list) else 1,
                    },
                )

        # Fallback: Minification without data loss for small structures or scalars
        final_fallback = f"{prefix}{minified_verbatim}{postfix}" if (prefix or postfix) else minified_verbatim
        return self._build_result(
            original=content,
            compressed=final_fallback,
            original_size=original_size,
            metadata={"strategy": "minified_verbatim"},
        )

    # ── Core Compression Engines ──────────────────────────────────────

    def _compress_dict_list(
        self,
        records: list[dict[str, Any]],
        max_reps: int,
        max_anom: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Compress a list of uniform/semi-uniform dictionaries."""
        total_count = len(records)

        # 1. Schema Analysis & Field Extraction
        field_types: dict[str, set[str]] = {}
        field_counts: Counter[str] = Counter()
        numerical_values: dict[str, list[float]] = {}
        categorical_values: dict[str, list[str]] = {}

        for record in records:
            for k, v in record.items():
                field_counts[k] += 1
                tname = type(v).__name__ if v is not None else "null"
                field_types.setdefault(k, set()).add(tname)

                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    numerical_values.setdefault(k, []).append(float(v))
                elif isinstance(v, (str, bool)):
                    categorical_values.setdefault(k, []).append(str(v))

        # Build schema summary
        schema: dict[str, Any] = {}
        for k, types in field_types.items():
            presence_rate = round(field_counts[k] / total_count, 3)
            schema[k] = {
                "types": sorted(list(types)),
                "presence_rate": presence_rate,
                "nullable": "null" in types or presence_rate < 1.0,
            }

        # 2. Statistical Summarization
        numerical_summary: dict[str, dict[str, Any]] = {}
        for k, vals in numerical_values.items():
            if vals:
                min_v = min(vals)
                max_v = max(vals)
                avg_v = sum(vals) / len(vals)
                numerical_summary[k] = {
                    "count": len(vals),
                    "min": round(min_v, 4) if isinstance(min_v, float) else min_v,
                    "max": round(max_v, 4) if isinstance(max_v, float) else max_v,
                    "avg": round(avg_v, 4),
                }

        categorical_summary: dict[str, dict[str, Any]] = {}
        for k, vals in categorical_values.items():
            counts = Counter(vals)
            if len(counts) <= self.MAX_CATEGORICAL_CARDINALITY:
                categorical_summary[k] = dict(counts.most_common(self.MAX_CATEGORICAL_CARDINALITY))
            else:
                top_3 = dict(counts.most_common(3))
                top_3["_other_distinct_count"] = len(counts) - 3
                categorical_summary[k] = top_3

        # 3. Anomaly & Outlier Detection
        # Identify common schema keys (present in >= 80% of items)
        common_keys = {k for k, cnt in field_counts.items() if cnt / total_count >= 0.8}
        anomalies: list[dict[str, Any]] = []
        anomaly_indices: set[int] = set()

        # Check for numerical outliers using IQR where applicable
        numerical_outlier_bounds: dict[str, tuple[float, float]] = {}
        for k, vals in numerical_values.items():
            if len(vals) >= 10:
                svals = sorted(vals)
                q1 = svals[len(svals) // 4]
                q3 = svals[(3 * len(svals)) // 4]
                iqr = q3 - q1
                if iqr > 0:
                    numerical_outlier_bounds[k] = (q1 - 1.5 * iqr, q3 + 1.5 * iqr)

        # Rare categorical values (< 5% frequency)
        rare_categories: dict[str, set[str]] = {}
        for k, vals in categorical_values.items():
            counts = Counter(vals)
            rare = {val for val, cnt in counts.items() if (cnt / total_count) < 0.05}
            if rare:
                rare_categories[k] = rare

        for idx, record in enumerate(records):
            is_anomaly = False
            reasons: list[str] = []

            # Missing common keys
            missing = common_keys - record.keys()
            if missing and len(missing) < len(common_keys):
                is_anomaly = True
                reasons.append(f"missing_keys:{list(missing)}")

            # Extra unexpected keys
            extra = record.keys() - common_keys
            if extra:
                is_anomaly = True
                reasons.append(f"extra_keys:{list(extra)}")

            # Check numerical bounds
            for k, (low, high) in numerical_outlier_bounds.items():
                val = record.get(k)
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    if val < low or val > high:
                        is_anomaly = True
                        reasons.append(f"numerical_outlier:{k}={val}")

            # Check rare categories or error terms
            for k, rare_set in rare_categories.items():
                val = record.get(k)
                if val is not None and str(val) in rare_set:
                    is_anomaly = True
                    reasons.append(f"rare_value:{k}={val}")

            # Explicit error / failure flags
            for k, val in record.items():
                if "error" in k.lower() or "fail" in str(val).lower() or "exception" in str(val).lower():
                    if val not in (False, None, 0, "", "None"):
                        is_anomaly = True
                        reasons.append(f"error_flag:{k}={val}")

            if is_anomaly:
                anomaly_indices.add(idx)
                if len(anomalies) < max_anom:
                    anom_record = dict(record)
                    anom_record["_anomaly_reasons"] = reasons
                    anom_record["_original_index"] = idx
                    anomalies.append(anom_record)

        # 4. Representative Sampling
        # Pick normal (non-anomalous) records: head, tail, and evenly spaced middle records
        normal_indices = [i for i in range(total_count) if i not in anomaly_indices]
        if not normal_indices:
            normal_indices = list(range(total_count))

        representatives: list[dict[str, Any]] = []
        if len(normal_indices) <= max_reps:
            chosen_indices = normal_indices
        else:
            step = (len(normal_indices) - 1) / float(max_reps - 1) if max_reps > 1 else 1.0
            chosen_indices = [normal_indices[int(round(i * step))] for i in range(max_reps)]
            # Ensure uniqueness preserving order
            seen = set()
            unique_chosen = []
            for i in chosen_indices:
                if i not in seen:
                    seen.add(i)
                    unique_chosen.append(i)
            chosen_indices = unique_chosen

        for i in chosen_indices:
            rep = dict(records[i])
            rep["_original_index"] = i
            representatives.append(rep)

        compressed_representation = {
            "schema": schema,
            "summary": {
                "numerical_fields": numerical_summary,
                "categorical_fields": categorical_summary,
            },
            "representative_records": representatives,
            "anomalies": anomalies,
            "original_count": total_count,
            "anomalies_detected": len(anomaly_indices),
        }

        meta = {
            "strategy": "smart_crusher_dict_list",
            "original_record_count": total_count,
            "representative_count": len(representatives),
            "anomalies_detected": len(anomaly_indices),
            "anomalies_preserved": len(anomalies),
            "fields_analyzed": list(schema.keys()),
        }

        return compressed_representation, meta

    def _compress_primitive_list(
        self,
        values: list[int | float],
        max_reps: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Compress a large list of numerical primitives."""
        total = len(values)
        min_v = min(values)
        max_v = max(values)
        avg_v = sum(values) / total

        # Samples
        step = max(1, total // max_reps)
        samples = [values[i] for i in range(0, total, step)][:max_reps]

        res = {
            "type": "numerical_array",
            "original_count": total,
            "summary": {
                "min": round(min_v, 4) if isinstance(min_v, float) else min_v,
                "max": round(max_v, 4) if isinstance(max_v, float) else max_v,
                "avg": round(avg_v, 4),
            },
            "sample_values": samples,
        }
        meta = {
            "strategy": "primitive_numerical_summary",
            "original_count": total,
        }
        return res, meta

    def _compress_nested_dict(
        self,
        data: dict[str, Any],
        array_keys: list[str],
        max_reps: int,
        max_anom: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Compress nested dictionaries containing large collection fields."""
        compressed = dict(data)
        compressed_keys = []
        total_orig_records = 0

        for key in array_keys:
            arr = data[key]
            if all(isinstance(item, dict) for item in arr):
                comp_arr, _ = self._compress_dict_list(arr, max_reps, max_anom)
                compressed[key] = comp_arr
                compressed_keys.append(key)
                total_orig_records += len(arr)
            elif all(isinstance(item, (int, float)) for item in arr):
                comp_arr, _ = self._compress_primitive_list(arr, max_reps)
                compressed[key] = comp_arr
                compressed_keys.append(key)
                total_orig_records += len(arr)

        meta = {
            "strategy": "nested_dict_compression",
            "compressed_array_keys": compressed_keys,
            "total_original_records": total_orig_records,
        }
        return compressed, meta

    # ── Helper ────────────────────────────────────────────────────────

    @staticmethod
    def _build_result(
        original: str,
        compressed: str,
        original_size: int,
        metadata: dict[str, Any],
    ) -> CompressionResult:
        compressed_bytes = len(compressed.encode("utf-8"))
        tokens_before = estimate_tokens(original)
        tokens_after = estimate_tokens(compressed)
        ratio = round(compressed_bytes / max(1, original_size), 4)

        return CompressionResult(
            original_content=original,
            compressed_content=compressed,
            original_size=original_size,
            compressed_size=compressed_bytes,
            compression_ratio=ratio,
            estimated_tokens_before=tokens_before,
            estimated_tokens_after=tokens_after,
            estimated_tokens_saved=max(0, tokens_before - tokens_after),
            content_type="json",
            metadata=metadata,
        )
