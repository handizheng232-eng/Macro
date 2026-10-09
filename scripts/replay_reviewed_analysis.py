"""Reviewed prose is a versioned presentation overlay, never a replacement of raw evidence."""
import hashlib
import json
from pathlib import Path

BODY_FIELDS = ('judgement', 'expectation', 'reality', 'mechanism', 'divergence', 'implication', 'validation')


def reviewed_analysis(stage, original):
    study = Path(stage) / '研究'
    reviewed_file = study / 'market-analysis-reviewed.json'
    if not reviewed_file.exists():
        return original
    document = json.loads(reviewed_file.read_text(encoding='utf-8'))
    source_hash = hashlib.sha256((study / 'market-analysis.json').read_bytes()).hexdigest()
    if document.get('sourceSha256') != source_hash:
        raise ValueError('Reviewed analysis source SHA is stale; re-audit before presentation')
    candidate = document['analysis']
    if not isinstance(candidate.get('conclusion'), str) or not candidate['conclusion'].strip():
        raise ValueError('Reviewed analysis conclusion must not be empty')
    if original.get('asOf') != candidate.get('asOf'):
        raise ValueError('Reviewed analysis cutoff must not change')
    for key, value in original.items():
        if key not in ('conclusion', 'sections', 'limitations') and candidate.get(key) != value:
            raise ValueError(f'Reviewed analysis changed audit/citation registry: {key}')
    if [section['id'] for section in candidate['sections']] != [section['id'] for section in original['sections']]:
        raise ValueError('Reviewed analysis theme order must not change')
    for before, after in zip(original['sections'], candidate['sections']):
        for key, value in before.items():
            if key not in BODY_FIELDS and after.get(key) != value:
                raise ValueError(f'Reviewed analysis changed citation/identity metadata: {key}')
        if any(not isinstance(after.get(field), str) or not after[field].strip() for field in BODY_FIELDS):
            raise ValueError('Reviewed analysis lost a required analytical field')
    return candidate
