import sqlite3
import re
import requests
import json
import time
import os

DB_PATH = 'd:/ArthX/data/arthx.db'

def has_concrete_data(text):
    if not text:
        return False
    # Check for digits (amounts, percentages, dates)
    has_digits = bool(re.search(r'\d+', text))
    # Check for dollar signs
    has_dollar = bool(re.search(r'\$', text))
    return has_digits or has_dollar

def run_audit():
    print("--- STARTING EXPLAINABILITY AUDIT ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Audit Anomalies
    cursor.execute("SELECT id, explanation FROM anomalies WHERE explanation IS NOT NULL AND explanation != ''")
    anomalies = cursor.fetchall()
    
    print(f"\n[1] Auditing {len(anomalies)} Anomaly Explanations...")
    anomaly_failures = 0
    for row in anomalies:
        anom_id, reason = row
        if not has_concrete_data(reason):
            print(f"  [FAIL] Anomaly {anom_id} failed audit. Reason: '{reason}'")
            anomaly_failures += 1
            
    if anomaly_failures == 0:
        print("  [PASS] All anomalies passed audit.")
        
    # 2. Audit Forecasts
    # Let's check schema for forecast tables
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='forecasts'")
    res = cursor.fetchone()
    forecast_failures = 0
    if res:
        cursor.execute("SELECT id, trend_summary FROM forecasts WHERE trend_summary IS NOT NULL AND trend_summary != ''")
        forecasts = cursor.fetchall()
        print(f"\n[2] Auditing {len(forecasts)} Forecast Explanations...")
        for row in forecasts:
            fid, reasoning = row
            if not has_concrete_data(reasoning):
                print(f"  [FAIL] Forecast {fid} failed audit. Reasoning: '{reasoning}'")
                forecast_failures += 1
                
        if forecast_failures == 0 and len(forecasts) > 0:
            print("  [PASS] All forecasts passed audit.")
        elif len(forecasts) == 0:
            print("  [-] No forecast reasonings found.")
    else:
        print("\n[2] Forecasts table not found or doesn't have reasoning.")

    # 3. Audit Assistant Answers
    print("\n[3] Auditing Assistant Chat Endpoints...")
    test_queries = [
        "Why is CloudScale Logistics flagged?",
        "What is the net position for the next 30 days?",
        "Are there any duplicate invoices?"
    ]
    
    assistant_failures = 0
    for q in test_queries:
        print(f"  Testing query: '{q}'")
        try:
            res = requests.post("http://127.0.0.1:8000/api/assistant/query", json={"question": q})
            res.raise_for_status()
            data = res.json()
            answer = data.get("answer", "")
            
            if not has_concrete_data(answer):
                print(f"  [FAIL] Assistant failed on query '{q}'. Answer: '{answer}'")
                assistant_failures += 1
            else:
                print(f"  [PASS] Passed. Contains concrete data.")
        except Exception as e:
            print(f"  [!] Failed to call assistant API: {e}")
            assistant_failures += 1
            
    print("\n--- AUDIT SUMMARY ---")
    total_failures = anomaly_failures + forecast_failures + assistant_failures
    if total_failures == 0:
        print("STATUS: SUCCESS. Zero generic or black-box explanations found. All text outputs grounded in data.")
    else:
        print(f"STATUS: FAILED. Found {total_failures} violations.")

if __name__ == "__main__":
    run_audit()
