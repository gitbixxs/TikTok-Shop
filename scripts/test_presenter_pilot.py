import concurrent.futures
import tempfile
import unittest
from pathlib import Path

from presenter_pilot import BudgetLedger, build_manifest, build_timeline


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'budget.sqlite'
        self.ledger = BudgetLedger(self.path)
        self.ledger.create_reel('pilot', overhead_cents=25)

    def tearDown(self):
        self.directory.cleanup()

    def test_reservations_are_atomic(self):
        def reserve(index):
            try:
                return self.ledger.reserve('pilot', str(index), 30)
            except ValueError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            accepted = list(executor.map(reserve, range(8)))
        self.assertEqual(sum(accepted), 2)
        self.assertEqual(self.ledger.summary('pilot')['committed_cents'], 85)

    def test_idempotency_does_not_authorize_second_submission(self):
        self.assertTrue(self.ledger.reserve('pilot', 'wan-hook', 20))
        self.assertFalse(self.ledger.reserve('pilot', 'wan-hook', 20))
        with self.assertRaises(ValueError):
            self.ledger.reserve('pilot', 'wan-hook', 21)
        self.assertEqual(self.ledger.summary('pilot')['committed_cents'], 45)

    def test_reel_cannot_be_reset(self):
        self.ledger.reserve('pilot', 'wan', 20)
        with self.assertRaises(ValueError):
            self.ledger.create_reel('pilot', overhead_cents=0)
        self.assertEqual(self.ledger.summary('pilot')['committed_cents'], 45)

    def test_unknown_costs_and_invalid_limits_block(self):
        for amount in [None, -1, 0, 1.5, True]:
            with self.assertRaises(ValueError):
                self.ledger.reserve('pilot', 'invalid', amount)
        with self.assertRaises(ValueError):
            self.ledger.create_reel('expensive', overhead_cents=0, cap_cents=101)
        with self.assertRaises(ValueError):
            self.ledger.reserve('missing', 'job', 10)

    def test_failures_and_uncertain_timeouts_stay_charged(self):
        self.ledger.reserve('pilot', 'timeout', 30)
        self.ledger.settle('pilot', 'timeout', actual_cents=None, outcome='unknown')
        self.assertFalse(self.ledger.reserve('pilot', 'timeout', 30))
        self.assertEqual(self.ledger.summary('pilot')['committed_cents'], 55)
        self.ledger.reserve('pilot', 'rejected', 20)
        self.ledger.settle('pilot', 'rejected', actual_cents=15, outcome='rejected')
        self.assertEqual(self.ledger.summary('pilot')['committed_cents'], 70)

    def test_overspend_is_recorded_and_blocks_further_work(self):
        self.ledger.reserve('pilot', 'job', 20)
        self.ledger.settle('pilot', 'job', actual_cents=90, outcome='accepted')
        summary = self.ledger.summary('pilot')
        self.assertEqual(summary['committed_cents'], 115)
        self.assertTrue(summary['over_budget'])
        with self.assertRaises(ValueError):
            self.ledger.reserve('pilot', 'another', 1)
        with self.assertRaises(ValueError):
            self.ledger.settle('pilot', 'job', actual_cents=0, outcome='accepted')


class TimelineTests(unittest.TestCase):
    def scenes(self):
        return [
            {'scene_id': 'hook', 'role': 'hook', 'visual': 'presenter', 'text': 'Eine Frage.', 'voice_duration_sec': 4.2},
            {'scene_id': 'detail', 'role': 'body', 'visual': 'product', 'text': 'Ein belegtes Detail.', 'voice_duration_sec': 21.1},
            {'scene_id': 'cta', 'role': 'cta', 'visual': 'presenter', 'text': 'Mehr im Warenkorb.', 'voice_duration_sec': 4.1},
        ]

    def test_measured_timeline_contains_full_cta(self):
        result = build_timeline(self.scenes())
        self.assertEqual(result['duration_sec'], 29.4)
        self.assertEqual(result['scenes'][1]['start_sec'], 4.2)
        self.assertEqual(result['scenes'][-1]['end_sec'], 29.4)
        self.assertEqual(len(result['scenes']), 3)

    def test_no_fixed_duration_fallback(self):
        scenes = self.scenes()
        del scenes[1]['voice_duration_sec']
        with self.assertRaises(ValueError):
            build_timeline(scenes)
        for duration in [float('nan'), float('inf'), -1, 0]:
            scenes[1]['voice_duration_sec'] = duration
            with self.assertRaises(ValueError):
                build_timeline(scenes)

    def test_short_reels_and_missing_presenter_block(self):
        scenes = self.scenes()
        scenes[1]['voice_duration_sec'] = 4
        with self.assertRaises(ValueError):
            build_timeline(scenes)
        scenes = self.scenes()
        scenes[-1]['visual'] = 'packshot'
        with self.assertRaises(ValueError):
            build_timeline(scenes)
        scenes = self.scenes()
        scenes[1]['scene_id'] = 'hook'
        with self.assertRaises(ValueError):
            build_timeline(scenes)


class ManifestTests(TimelineTests):
    def specification(self):
        scenes = self.scenes()
        for scene in scenes:
            scene['asset_id'] = scene['visual']
            scene['claim_sources'] = ['verified product specification']
        return {'product_key': 'verified-sku', 'scenes': scenes, 'assets': [
            {'asset_id': 'presenter', 'kind': 'presenter', 'identity_status': 'fictional', 'rights_status': 'owned', 'rights_evidence': 'generation receipt', 'source': 'original generation', 'quality_status': 'accepted'},
            {'asset_id': 'product', 'kind': 'product', 'product_key': 'verified-sku', 'rights_status': 'licensed', 'rights_evidence': 'supplier permission', 'source': 'supplier media', 'quality_status': 'accepted'},
        ]}

    def test_validated_manifest_is_draft_only(self):
        manifest = build_manifest(self.specification())
        self.assertTrue(manifest['draft_only'])
        self.assertTrue(manifest['is_ai_generated'])
        self.assertEqual(manifest['duration_sec'], 29.4)

    def test_missing_rights_wrong_product_or_unreviewed_media_block(self):
        for field, value in [('rights_status', 'unknown'), ('rights_evidence', ''), ('product_key', 'other-sku'), ('quality_status', 'pending')]:
            spec = self.specification()
            spec['assets'][1][field] = value
            with self.assertRaises(ValueError):
                build_manifest(spec)

    def test_unsupported_claim_or_unauthorized_presenter_blocks(self):
        spec = self.specification()
        spec['scenes'][1]['claim_sources'] = []
        with self.assertRaises(ValueError):
            build_manifest(spec)
        spec = self.specification()
        spec['assets'][0]['identity_status'] = 'unverified'
        with self.assertRaises(ValueError):
            build_manifest(spec)


if __name__ == '__main__':
    unittest.main()
