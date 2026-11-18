"""Package an actual held-out example for the standalone upload-and-audit tool."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'results/v2/audit_example.csv').read_text(encoding='utf-8')
(ROOT/'website/example.csv').write_text(text,encoding='utf-8')
(ROOT/'website/example-data.js').write_text('window.EXAMPLE_CSV = '+json.dumps(text)+';\n',encoding='utf-8')
print('Standalone tool example prepared; no manuscript assets or routes copied.')
