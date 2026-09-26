"""
ArthX Analysis Routes — T2.1 / T2.3 / T3.1
Exposes:
  GET  /api/datasets           — List available datasets by name/id
  POST /api/analysis/run       — Unified pipeline (optional dataset switch: ingest+analyze)
  GET  /api/analysis/anomalies — List persisted anomalies
  GET  /api/anomalies          — List persisted anomalies (T3.2 specification alias)
  POST /api/analysis/explain   — Regenerate LLM explanations
"""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config import ROOT_DIR
from database import get_db
from schemas.anomaly import AnomalyResponse
from services.analysis import get_stored_anomalies
from services.explanation import run_explanation_pipeline
from services.ingestion import run_ingestion_from_dir
from services.orchestrator import run_orchestrated_pipeline

router = APIRouter(tags=["analysis"])

# ---------------------------------------------------------------------------
# Dataset registry — auto-discovered from /data/dataset_*/ subdirectories
# ---------------------------------------------------------------------------
_DATASET_META = {
    "dataset_a": {"id": "dataset_a", "label": "Dataset A — Default",            "description": "Balanced mix of 17 anomalies, clear declining trend, 7 duplicate invoice pairs."},
    "dataset_b": {"id": "dataset_b", "label": "Dataset B — High Fraud Activity",  "description": "38 injected anomalies, 10 duplicate pairs, obvious large-fraud patterns."},
    "dataset_c": {"id": "dataset_c", "label": "Dataset C — Cash Flow Crisis",     "description": "Only 8 minor anomalies, but sharp 90-day outflow ramp + revenue decline. Showcases forecasting."},
    "dataset_d": {"id": "dataset_d", "label": "Dataset D — Mostly Clean",         "description": "Only 4 anomalies, stable positive cash flow. Proves model doesn't over-flag healthy data."},
}


@router.get("/api/datasets")
def list_datasets():
    """
    Return all available datasets with their label, id, and description.
    Each dataset lives under /data/<id>/transactions.csv + invoices.csv.
    """
    data_root = ROOT_DIR / "data"
    available = []
    for ds_id, meta in _DATASET_META.items():
        ds_path = data_root / ds_id
        tx_path = ds_path / "transactions.csv"
        inv_path = ds_path / "invoices.csv"
        available.append({
            **meta,
            "available": tx_path.exists() and inv_path.exists(),
        })
    return {"datasets": available}


@router.post("/api/analysis/run")
def run_analysis_endpoint(
    run_explainer: bool = Query(
        default=True,
        description="Whether to run LLM explainability generation for results",
    ),
    horizon_days: int = Query(
        default=30,
        ge=7,
        le=90,
        description="Cash flow forecast horizon in days",
    ),
    dataset: Optional[str] = Query(
        default=None,
        description="Dataset ID to ingest before analysis (e.g. 'dataset_b'). If None, analyzes currently loaded data.",
    ),
    db: Session = Depends(get_db),
):
    """
    T3.1 — Master pipeline orchestration endpoint:
      0. (Optional) Ingest a specific dataset by ID — replaces existing data idempotently
      1. Anomaly & fraud detection (T2.1)
      2. Invoice validation (T2.4)
      3. Cash flow forecasting (T2.2)
      4. Forecast impact linking (T2.5)
      5. Grounded explainability generation (T2.3)

    Persists all computed outputs to the database.
    Subsequent GET queries to dashboard endpoints return instantaneously (<1s).
    """
    try:
        # Step 0: Optional dataset switch — ingest fresh data before computing
        ingestion_summary = None
        if dataset:
            if dataset not in _DATASET_META:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown dataset '{dataset}'. Available: {list(_DATASET_META.keys())}"
                )
            ds_path = ROOT_DIR / "data" / dataset
            if not (ds_path / "transactions.csv").exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Dataset '{dataset}' files not found at {ds_path}"
                )
            ingestion_summary = run_ingestion_from_dir(db, data_dir=ds_path)

        result = run_orchestrated_pipeline(
            db=db,
            run_explainer=run_explainer,
            horizon_days=horizon_days,
        )

        if ingestion_summary:
            result["dataset"] = dataset
            result["dataset_label"] = _DATASET_META[dataset]["label"]
            result["ingestion"] = ingestion_summary

        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Orchestration pipeline failed: {str(e)}")


@router.get("/api/analysis/anomalies", response_model=List[AnomalyResponse])
@router.get("/api/anomalies", response_model=List[AnomalyResponse])
@router.get("/api/anomalies/", response_model=List[AnomalyResponse], include_in_schema=False)
def list_anomalies(
    min_risk: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum risk score (0.0 - 1.0)"),
    vendor: Optional[str] = Query(None, description="Filter by vendor name (case-insensitive substring)"),
    reason_code: Optional[str] = Query(None, description="Filter by reason code"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    db: Session = Depends(get_db),
):
    """
    T3.2 — Return persisted anomaly records from the DB, ordered by risk_score descending.
    Includes risk_score, reason_code, trigger_metric, explanation, and impact_on_30d_forecast.
    """
    return get_stored_anomalies(
        db=db,
        min_risk=min_risk,
        vendor=vendor,
        reason_code=reason_code,
        limit=limit,
        offset=offset,
    )


@router.post("/api/analysis/explain")
def run_explain_endpoint(
    overwrite: bool = Query(
        default=True,
        description="If false, skip anomalies/forecasts that already have explanations.",
    ),
    db: Session = Depends(get_db),
):
    """
    T2.3 — Standalone trigger for generating LLM explanations.
    """
    try:
        result = run_explanation_pipeline(db, overwrite=overwrite)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explanation pipeline failed: {str(e)}")
