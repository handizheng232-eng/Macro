"""ReadingControls04 UI-only release layered over immutable research release 03.
The old verifier/receipt remain replayable at their original commit. This gate
revalidates every old research constraint; only reviewed UI/assets are versioned.
"""
import argparse
import hashlib
import json
from pathlib import Path
from verify_renewed_limited_publish import verify, verify_files, verify_assets
from verify_renewed_easing_publish import require

ROOT = Path(__file__).resolve().parents[1]
BASE_RECEIPT = 'release/replay-renewed-easing-publication-03.json'
UI_FILES = {'src/App.tsx', 'src/historyReplay.tsx', 'src/historyReplay.css',
            'src/replayHierarchy.ts', 'src/replayOutline.tsx', 'src/replayReading.tsx',
            'docs/macro-replay-template.md', 'docs/macro-replay-reading-template.md'}
DATA_FILES = {'src/data/' + name for name in (
    'historyReplay.json', 'historyReplay.README.md', 'historyReplayHawkishTransition.json',
    'historyReplayRenewedEasingQtEnd.json', 'historyReplayTariffPause.json',
    'usConsumptionData.json', 'usEmploymentData.json', 'usGdpData.json',
    'usInflationData.json', 'usLateModulesData.json', 'usMacroData.json')}


def verify_reading(receipt, root=ROOT, dist=None):
    require(receipt.get('schemaVersion') == 'replay-reading-controls-04', 'wrong UI contract')
    require(receipt.get('publicationAuthorized') is True and receipt.get('pageQAComplete') is True,
            'UI publication authorization/QA absent')
    require(receipt.get('scope') == 'renewed-easing-qt-end-ui-only', 'UI scope differs')
    require(receipt.get('pinEncoding') == 'git-lf', 'unknown pin encoding')
    # Git text checkout may use CRLF on Windows; public pins bind canonical LF.
    # The research verifier below still binds the critical dataset as exact bytes.
    base_raw = (root / BASE_RECEIPT).read_bytes()
    require(hashlib.sha256(base_raw.replace(b'\r\n', b'\n')).hexdigest() == receipt['researchReceiptSHA256'], 'original research receipt changed')
    base = json.loads(base_raw)
    raw = (root / 'src/data/historyReplayRenewedEasingQtEnd.json').read_bytes()
    result = verify(json.loads(raw), raw, base)
    # Preserve all previous non-UI pins, including the original release snapshot.
    old_pins = {k: v for k, v in base['publicFilePins'].items() if k != 'src/historyReplay.tsx'}
    verify_files({'publicFilePins': old_pins}, root)
    require(set(receipt['publicFilePins']) == UI_FILES | DATA_FILES, 'UI/data pin coverage differs')
    for relative, sha in receipt['publicFilePins'].items():
        raw_file = (root / relative).read_bytes()
        require(hashlib.sha256(raw_file.replace(b'\r\n', b'\n')).hexdigest() == sha,
                'public UI/data/template changed: ' + relative)
    if dist is not None:
        result['distFilesScanned'] = verify_assets(dist, receipt)
    result['readingRelease'] = 'ReadingControls04'
    result['researchReceiptUnchanged'] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path)
    args = parser.parse_args()
    try:
        receipt = json.loads((ROOT / 'release/replay-reading-publication-04.json').read_bytes())
        print(json.dumps(verify_reading(receipt, dist=args.dist), ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as error:
        print(json.dumps({'status': 'INVALID_READING_PUBLICATION_04', 'reason': str(error)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
