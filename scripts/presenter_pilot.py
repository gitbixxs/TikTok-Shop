import argparse
import json
import math
import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

LONGCAT_MAX_AUDIO_SECONDS = 4.8


def cents(value, minimum=0, maximum=None):
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise ValueError('A known integer EUR-cent amount within the budget is required')
    return value


class BudgetLedger:
    def __init__(self, database):
        self.database = str(Path(database))
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS reels (
                    reel_id TEXT PRIMARY KEY,
                    cap_cents INTEGER NOT NULL,
                    overhead_cents INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    reel_id TEXT NOT NULL REFERENCES reels(reel_id),
                    attempt_id TEXT NOT NULL,
                    reserved_cents INTEGER NOT NULL,
                    actual_cents INTEGER,
                    outcome TEXT NOT NULL DEFAULT 'reserved',
                    PRIMARY KEY (reel_id, attempt_id)
                );
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.database, timeout=20)
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def create_reel(self, reel_id, *, overhead_cents, cap_cents=100):
        if not isinstance(reel_id, str) or not reel_id.strip():
            raise ValueError('A reel ID is required')
        cents(cap_cents, 1, 100)
        cents(overhead_cents, 0, cap_cents)
        try:
            with self.connection() as db:
                db.execute('INSERT INTO reels VALUES (?, ?, ?)', (reel_id, cap_cents, overhead_cents))
        except sqlite3.IntegrityError as error:
            raise ValueError('Existing reel budgets cannot be reset') from error

    def _summary(self, db, reel_id):
        row = db.execute('SELECT cap_cents, overhead_cents FROM reels WHERE reel_id=?', (reel_id,)).fetchone()
        if row is None:
            raise ValueError('Unknown reel budget')
        attempted = db.execute('SELECT COALESCE(SUM(COALESCE(actual_cents, reserved_cents)), 0) FROM attempts WHERE reel_id=?', (reel_id,)).fetchone()[0]
        committed = row[1] + attempted
        return {'cap_cents': row[0], 'overhead_cents': row[1], 'attempt_cents': attempted,
                'committed_cents': committed, 'remaining_cents': max(0, row[0] - committed),
                'over_budget': committed > row[0]}

    def summary(self, reel_id):
        with self.connection() as db:
            return self._summary(db, reel_id)

    def reserve(self, reel_id, attempt_id, upper_bound_cents):
        cents(upper_bound_cents, 1)
        if not isinstance(attempt_id, str) or not attempt_id.strip():
            raise ValueError('A stable provider-attempt ID is required')
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            summary = self._summary(db, reel_id)
            existing = db.execute('SELECT reserved_cents FROM attempts WHERE reel_id=? AND attempt_id=?', (reel_id, attempt_id)).fetchone()
            if existing:
                if existing[0] != upper_bound_cents:
                    raise ValueError('Attempt reservation cannot be changed')
                return False
            if upper_bound_cents > summary['remaining_cents']:
                raise ValueError('Reel budget exhausted; paid submission blocked')
            db.execute('INSERT INTO attempts (reel_id, attempt_id, reserved_cents) VALUES (?, ?, ?)', (reel_id, attempt_id, upper_bound_cents))
            return True

    def settle(self, reel_id, attempt_id, *, actual_cents, outcome):
        if outcome not in ('accepted', 'rejected', 'failed', 'unknown'):
            raise ValueError('Invalid attempt outcome')
        if actual_cents is not None:
            cents(actual_cents)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT actual_cents, outcome FROM attempts WHERE reel_id=? AND attempt_id=?', (reel_id, attempt_id)).fetchone()
            if previous is None:
                raise ValueError('Attempt was not reserved')
            if previous[0] is not None:
                if previous != (actual_cents, outcome):
                    raise ValueError('Settled costs cannot be overwritten')
                return
            db.execute('UPDATE attempts SET actual_cents=?, outcome=? WHERE reel_id=? AND attempt_id=?', (actual_cents, outcome, reel_id, attempt_id))


def build_timeline(scenes):
    if not isinstance(scenes, list) or not 3 <= len(scenes) <= 16:
        raise ValueError('A presenter reel needs 3–16 scenes')
    if scenes[0].get('role') != 'hook' or scenes[-1].get('role') != 'cta':
        raise ValueError('Hook and CTA scenes are required')
    if any(scene.get('visual') != 'presenter' for scene in (scenes[0], scenes[-1])):
        raise ValueError('A visible presenter is required in hook and CTA')
    timeline = []
    seen = set()
    start = Decimal('0')
    for scene in scenes:
        scene_id = scene.get('scene_id')
        duration = scene.get('voice_duration_sec')
        if not isinstance(scene_id, str) or not scene_id.strip() or scene_id in seen:
            raise ValueError('Unique scene IDs are required')
        if not str(scene.get('text', '')).strip():
            raise ValueError('Every scene needs spoken text')
        if type(duration) not in (int, float) or not math.isfinite(duration) or not 0 < duration <= 35:
            raise ValueError('Measured positive voice duration is required for every scene')
        if scene.get('generation_provider') == 'longcat15' and (scene.get('visual') != 'presenter' or duration > LONGCAT_MAX_AUDIO_SECONDS):
            raise ValueError('LongCat narration must be a measured presenter segment of at most4.8 seconds')
        seen.add(scene_id)
        end = start + Decimal(str(duration))
        timeline.append({**scene, 'start_sec': float(start), 'end_sec': float(end), 'duration_sec': float(end - start)})
        start = end
    if not Decimal('28') <= start <= Decimal('35'):
        raise ValueError('Revise narration: pilot must last 28–35 seconds without padding or truncation')
    return {'format': 'presenter_advice_v1', 'duration_sec': float(start), 'transition_sec': 0,
            'scenes': timeline}


def build_manifest(specification):
    product_key = specification.get('product_key')
    if not isinstance(product_key, str) or not product_key.strip():
        raise ValueError('An exact product key is required')
    timeline = build_timeline(specification.get('scenes'))
    asset_list = specification.get('assets', [])
    if not isinstance(asset_list, list):
        raise ValueError('Assets must be a list')
    assets = {}
    for asset in asset_list:
        key = asset.get('asset_id')
        if not isinstance(key, str) or not key.strip() or key in assets:
            raise ValueError('Unique asset IDs are required')
        if asset.get('rights_status') not in ('owned', 'licensed') or not asset.get('rights_evidence'):
            raise ValueError('Every asset needs documented reuse rights')
        if asset.get('quality_status') != 'accepted' or not asset.get('source'):
            raise ValueError('Every asset needs a source and accepted quality review')
        if asset.get('kind') == 'product' and asset.get('product_key') != product_key:
            raise ValueError('Product asset does not match exact SKU')
        if asset.get('kind') == 'presenter' and asset.get('identity_status') not in ('fictional', 'authorized'):
            raise ValueError('Presenter identity must be fictional or explicitly authorized')
        assets[key] = asset
    for scene in timeline['scenes']:
        asset = assets.get(scene.get('asset_id'))
        if asset is None or asset.get('kind') != scene['visual']:
            raise ValueError('Scene requires a reviewed matching asset')
        if scene.get('claim_sources') is None or not isinstance(scene['claim_sources'], list):
            raise ValueError('Every scene must explicitly list its claim evidence')
        if scene['role'] == 'body' and not scene['claim_sources']:
            raise ValueError('Product claims require evidence')
        if scene.get('generated_clip_path'):
            checksum = scene.get('generated_clip_sha256')
            if not isinstance(checksum, str) or len(checksum) != 64 or any(character not in '0123456789abcdef' for character in checksum):
                raise ValueError('Generated media requires a recorded checksum')
            if scene.get('media_quality_status') != 'accepted' or scene.get('commercial_dependency_review') != 'accepted':
                raise ValueError('Generated media needs explicit audiovisual and commercial-dependency approval')
    return {**timeline, 'product_key': product_key, 'assets': asset_list,
            'draft_only': True, 'is_ai_generated': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('specification', type=Path)
    arguments = parser.parse_args()
    with arguments.specification.open(encoding='utf-8') as source:
        specification = json.load(source)
    try:
        manifest = build_manifest(specification)
    except (ValueError, TypeError, KeyError) as error:
        parser.exit(2, 'Pilot blocked: ' + str(error) + '\n')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
