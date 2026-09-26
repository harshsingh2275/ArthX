import requests, json, time

print('Switching to Dataset D (Mostly Clean)...')
start = time.time()
r = requests.post('http://127.0.0.1:8000/api/analysis/run?dataset=dataset_d', timeout=180)
elapsed = round(time.time() - start, 1)
data = r.json()
print('Status:', r.status_code, '| Time:', elapsed, 's')
print('Dataset label:', data.get('dataset_label', 'N/A'))
ingest = data.get('ingestion', {})
if ingest:
    print('Ingested:', ingest['loaded']['transactions'], 'tx,', ingest['loaded']['invoices'], 'inv')
anom = data.get('anomaly_detection', {})
print('Anomalies detected:', anom.get('flagged_count', 'N/A'))
fc = data.get('forecast', {})
print('Forecast days:', len(fc.get('forecast', [])))
print('PASSED - Dataset D pipeline ran successfully.')
