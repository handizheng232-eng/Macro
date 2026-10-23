"""EconomicMechanisms02: scoped research revision over immutable release 03/04.
Public CI replays byte/structure contracts, not private-source economic review.
The inverse projection executes the complete previous gate on its exact bytes.
"""
import argparse
import copy
import hashlib
import json
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse
from verify_renewed_easing_publish import require, public_privacy
from verify_renewed_limited_publish import digest, verify_assets
from verify_replay_reading_publish import verify_reading, UI_FILES, DATA_FILES

ROOT = Path(__file__).resolve().parents[1]
DATA = 'src/data/historyReplayRenewedEasingQtEnd.json'
RENDERER = 'src/historyReplay.tsx'
INVERSE = 'release/replay-economic-mechanisms-02-inverse.json'
RECEIPT = 'release/replay-economic-mechanisms-publication-02.json'
READING = 'release/replay-reading-publication-04.json'
RESEARCH = 'release/replay-renewed-easing-publication-03.json'
FIXTURE = 'src/data/historyReplayEconomicMechanisms02.fixture.json'
TOPICS = {'inflation-vintages', 'demand-supply'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def lf(raw):
    return raw.replace(b'\r\n', b'\n')


def baseline_bytes(relative, root=ROOT):
    """Apply reviewed inverse edits; both source blocks and final bytes are bound."""
    patches = json.loads((root / INVERSE).read_bytes())
    require(set(patches) == {DATA, RENDERER}, 'inverse scope differs')
    record = patches[relative]
    raw = lf((root / relative).read_bytes())
    require(sha(raw) == record['currentSHA256'], 'inverse input bytes differ')
    lines = raw.decode('utf-8').splitlines(keepends=True)
    previous_end = 0
    for op in record['operations']:
        start, end = op['start'], op['end']
        require(0 <= previous_end <= start <= end <= len(lines), 'invalid inverse span')
        require(sha(''.join(lines[start:end]).encode()) == op['currentSHA256'], 'inverse block changed')
        previous_end = end
    for op in reversed(record['operations']):
        lines[op['start']:op['end']] = [op['baselineText']]
    restored = ''.join(lines).encode('utf-8')
    require(sha(restored) == record['baselineSHA256'], 'inverse baseline bytes differ')
    return restored


@contextmanager
def baseline_root(root=ROOT):
    """Isolated public-only legacy fixture; never rewrites old receipts or sources."""
    reading = json.loads((root / READING).read_bytes())
    research = json.loads((root / RESEARCH).read_bytes())
    names = set(reading['publicFilePins']) | set(research['publicFilePins']) | {READING, RESEARCH}
    with tempfile.TemporaryDirectory(prefix='economic-release-legacy-') as directory:
        target = Path(directory)
        for name in names:
            path = Path(name)
            require(not path.is_absolute() and '..' not in path.parts, 'unsafe legacy path')
            dest = target / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(baseline_bytes(name, root) if name in {DATA, RENDERER} else (root / path).read_bytes())
        yield target


def verify_revision(data, baseline, receipt, fixture):
    """Check authorized fields independently of the outer payload hash."""
    restored = copy.deepcopy(data)
    old_sections = {s['id']: s for s in baseline['marketAnalysis']['sections']}
    sections = {s['id']: s for s in data['marketAnalysis']['sections']}
    require(len(sections) == len(data['marketAnalysis']['sections']) == 5, 'topic identities differ')
    require(set(receipt['approvedSummaryDigests']) == TOPICS, 'summary approval scope differs')
    for section in restored['marketAnalysis']['sections']:
        if section['id'] in TOPICS:
            section['periodSummary'] = copy.deepcopy(old_sections[section['id']]['periodSummary'])
    old_ids = {s['id'] for s in baseline['sources']}
    added = [s for s in data['sources'] if s['id'] not in old_ids]
    require(len(added) == 11 and len({s['id'] for s in data['sources']}) == len(data['sources']) == 239, 'source scope differs')
    require({s['id']: digest(s) for s in added} == receipt['approvedAddedSourceDigests'], 'new source metadata changed')
    for source in added:
        require(source['firstAvailableDate'] is None and source['historicalAsOfEligible'] is False and source['retrospectiveOnly'] is True, 'new source historical upgrade')
    restored['sources'] = [s for s in restored['sources'] if s['id'] in old_ids]
    require(restored == baseline, 'non-authorized research, series, sources or seven increments changed')
    sm = {s['id']: s for s in data['sources']}
    rm = {r['id']: r for r in data['reports']}
    require(len(fixture) == 2 and {f['topic'] for f in fixture} == TOPICS, 'fixture topic scope differs')
    for f in fixture:
        section = sections[f['topic']]
        summary = section['periodSummary']
        require(digest(summary) == receipt['approvedSummaryDigests'][f['topic']], 'approved summary changed')
        require(summary['firstAvailableDate'] is None and summary['historicalAsOfEligible'] is False and summary['retrospectiveOnly'] is True, 'summary historical upgrade')
        require(len(summary['paragraphs']) == len(summary['paragraphSources']) == 12, 'monthly paragraph count differs')
        nodes = {n['id']: n for entries in section['deepDive'].values() for n in entries}
        require(set(summary['evidenceRefs']) <= nodes.keys(), 'unregistered summary node')
        require(set(summary['reportIds']) <= rm.keys(), 'unregistered summary report')
        require(set(summary['sourceIds']) <= sm.keys(), 'unregistered summary source')
        used = set()
        for i, (text, refs) in enumerate(zip(summary['paragraphs'], summary['paragraphSources'])):
            month, within = divmod(i, 3)
            require(text.startswith(str(month + 9) + '月'), 'monthly paragraph order differs')
            require(bool(refs) and len({r['sourceId'] for r in refs}) == len(refs), 'empty or duplicate paragraph sources')
            for ref in refs:
                require(ref['sourceId'] in sm and bool(ref['label'].strip()), 'unreadable paragraph citation')
                require(urlparse(sm[ref['sourceId']]['url']).scheme in {'https', 'http'}, 'unsafe citation URL')
                used.add(ref['sourceId'])
            if within < 2:
                j = month * 2 + within
                require(sha(text.encode()) == f['mechanismSHA256'][j] and refs == f['mechanismSources'][j], 'official explanation or citation changed')
            else:
                expected = f['institutions'][month]
                require(sha(text.encode()) == expected['textSHA256'], 'institution conditions or attribution changed')
                require(set(expected['nodes']) <= set(summary['evidenceRefs']), 'institution support missing')
                for sid in expected['sourceIds']:
                    require(sid in used and sid in summary['reportIds'] and sid in summary['sourceIds'], 'institution source/report missing')
                    report = rm[sid]
                    require(report['publicationDate'][:7] == f'2025-{month + 9:02}' and report['firstAvailableDate'] is None and report['historicalAsOfEligible'] is False, 'institution month/history differs')
                    require(any(sid in nodes[nid]['reportIds'] and sid in nodes[nid]['sourceIds'] for nid in expected['nodes']), 'institution report not reachable')
        require(used == set(summary['sourceIds']), 'paragraph citation closure differs')
    public_privacy(data)


def verify_economic(receipt, root=ROOT, dist=None):
    require(receipt.get('schemaVersion') == 'economic-mechanisms-publication-02', 'wrong economic release contract')
    require(receipt.get('scope') == 'renewed-easing-qt-end-two-summaries-and-paragraph-citations', 'economic scope differs')
    require(receipt.get('publicationAuthorized') is True and receipt.get('pageQAComplete') is True and receipt.get('fullStageReady') is False, 'limited authorization/QA absent or upgraded')
    require(receipt.get('pinEncoding') == 'git-lf', 'unknown pin encoding')
    required = UI_FILES | DATA_FILES | {INVERSE, READING, RESEARCH, FIXTURE}
    require(set(receipt['publicFilePins']) == required, 'release pin coverage differs')
    for relative, expected in receipt['publicFilePins'].items():
        require(sha(lf((root / relative).read_bytes())) == expected, 'public file changed: ' + relative)
    raw = (root / DATA).read_bytes()
    require(sha(raw) == receipt['datasetSHA256'], 'approved economic payload bytes differ')
    baseline = json.loads(baseline_bytes(DATA, root))
    verify_revision(json.loads(raw), baseline, receipt, json.loads((root / FIXTURE).read_bytes()))
    with baseline_root(root) as previous:
        result = verify_reading(json.loads((previous / READING).read_bytes()), root=previous)
    if dist is not None:
        result['distFilesScanned'] = verify_assets(dist, receipt)
    result.update(status='PASS_AUTHORIZED_ECONOMIC_MECHANISMS_02', officialParagraphs=16,
                  institutionParagraphs=8, addedOfficialSources=11, legacyGateReplayed=True,
                  rawOriginalReadbackPerformed=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path)
    args = parser.parse_args()
    try:
        result = verify_economic(json.loads((ROOT / RECEIPT).read_bytes()), dist=args.dist)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as error:
        print(json.dumps({'status': 'INVALID_ECONOMIC_MECHANISMS_02', 'reason': str(error)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
