import sys
sys.path.insert(0, 'D:/ArthX/backend')
from config import settings
print('model:', settings.LLM_MODEL_NAME)

from ml.explainer import generate_explanation
import re

data = {
    'transaction_id': 210,
    'vendor': 'LegalEdge Partners',
    'amount': 8750.0,
    'risk_score': 0.70,
    'reason_code': 'POSSIBLE_DUPLICATE',
    'trigger_metric': 'Possible duplicate: 8750.00 from LegalEdge Partners also on 2026-07-28'
}
result = generate_explanation(data)

print()
print('=== EXPLANATION ===')
print(result)
print()
is_grounded = bool(re.search(r'\d', result))
is_fallback = result.startswith('This transaction from')
print('Grounded (has digit):', is_grounded)
print('Used LLM (not template fallback):', not is_fallback)
