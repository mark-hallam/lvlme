"""Moving terms are shown and checked, without becoming a scoring input."""
import os
import unittest
from unittest import mock

import helpers as H
import _today as T
import build_dashboard as B
import validate as V
from test_dashboard import page_data


class PayTests(unittest.TestCase):
    def test_yearly_formats(self):
        for text, expected in [
            ('USD 300,000', ('USD', 300000, 300000)),
            ('US$300k', ('USD', 300000, 300000)),
            ('A$150,000 to $180,000', ('AUD', 150000, 180000)),
            ('AUD 150k-180k', ('AUD', 150000, 180000)),
            ('$120,000 - $140,000 per annum', (None, 120000, 140000)),
            ('£80,000', ('GBP', 80000, 80000)),
            ('€90.000', ('EUR', 90000, 90000)),
            ('GBP 80.5k to 100k yearly', ('GBP', 80500, 100000)),
            ('USD 1.2m', ('USD', 1200000, 1200000)),
            ('$190,000 to $240,000 USD', ('USD', 190000, 240000)),
        ]:
            with self.subTest(text=text):
                self.assertEqual(B.parse_pay(text), expected)

    def test_unclear_or_non_yearly_pay(self):
        for text in [None, '', 'competitive', 'USD 80 per hour', 'USD 80/hr',
                     'AUD 800 a day', 'AUD 800 daily', 'USD 8000 monthly',
                     'USD 8000 per month', 'USD 80 hourly', 'USD 80 /h',
                     'USD 300k to EUR 400k', 'USD 300k plus USD 20k bonus',
                     'USD 400k-300k']:
            with self.subTest(text=text):
                self.assertIsNone(B.parse_pay(text))


class MoveTests(unittest.TestCase):
    def setUp(self):
        self.config = H.example_config()
        self.config['targets'] = [{'id': 'acme', 'name': 'Acme AI'}]
        self.role = {'org': 'acme', 'lc': 'us'}
        self.home = B.home_class(self.config)
        self.config.setdefault('candidate', {})['relocation'] = {
            'willing': 'anywhere', 'from': 'now',
            'minimum_pay': {'currency': 'USD', 'amount': 300000}}
        self.relocation = self.config['candidate']['relocation']

    def line(self, pay='USD 300,000'):
        return B.move_line(self.config, self.role, {'compensation': pay}, self.home)

    def test_willing_with_terms_and_floor_met_at_high_end(self):
        line = self.line('USD 250k-300k')
        self.assertEqual(line, {'verdict': 'willing', 'text':
            'A move. You said you would move for this: anywhere, from now, for USD 300,000 a year or more. '
            "The posting's pay meets your floor."})

    def test_below_floor(self):
        self.assertEqual(self.line('USD 200k-299k')['verdict'], 'below_floor')
        self.assertIn("below the pay you said you would move for.", self.line('USD 200k')['text'])

    def test_no_pay_other_currency_and_unclear_yearly_pay(self):
        self.assertIn('does not state pay, so ask early.', self.line(None)['text'])
        self.assertIn('another currency, so compare it yourself.', self.line('AUD 400k')['text'])
        self.assertIn('does not name its currency, so compare it yourself.', self.line('$400,000')['text'])
        for pay in ['AUD 400k', '$400,000']:
            self.assertEqual(self.line(pay)['verdict'], 'willing')

    def test_money_mask_leaves_standards_and_product_numbers_alone(self):
        mask = lambda t: B.MONEY_RX.sub('[salary]', t)
        for text in ['ISO 9001 audits', 'SQL 2019', 'GPT 4 work', 'AS 4801']:
            with self.subTest(text=text):
                self.assertEqual(mask(text), text)
        for text in ['USD 300,000', 'A$150,000 to $180,000', 'CHF 120k', '$95k']:
            with self.subTest(text=text):
                self.assertEqual(mask(text), '[salary]')
        for pay in ['competitive', 'USD 300 per hour']:
            self.assertIn('yearly pay is unclear, so compare it yourself.', self.line(pay)['text'])

    def test_some_places_date_and_sponsorship(self):
        self.relocation.update(willing='some_places', classes=['us'],
                               **{'from': '2027-03', 'needs_sponsorship_paid': True})
        text = self.line()['text']
        self.assertIn('to United States, from March 2027,', text)
        self.assertIn('with the visa paid by the employer.', text)
        self.role['lc'] = 'apac_other'
        self.assertEqual(self.line(), {'verdict': 'not_willing', 'text':
                                     'You said you would not move for a role here.'})

    def test_no_and_unknown(self):
        self.relocation['willing'] = 'no'
        self.assertEqual(self.line()['verdict'], 'not_willing')
        self.relocation['willing'] = 'unsure'
        self.assertEqual(self.line()['verdict'], 'unknown')
        del self.config['candidate']['relocation']
        self.assertEqual(self.line(), {'verdict': 'unknown', 'text':
            'You have not said whether you would move for a role here. Ask your agent to record it.'})

    def test_organisation_override_includes_name_and_no_comparison(self):
        self.relocation.update(willing='no', organisations_regardless=['acme'])
        self.assertEqual(self.line('USD 1'), {'verdict': 'willing', 'text':
            'A move. You said Acme AI is worth the move at any pay.'})

    def test_home_has_no_move_line(self):
        self.role['lc'] = self.home
        self.assertIsNone(self.line())

    def test_optional_terms_are_omitted(self):
        self.config['candidate']['relocation'] = {'willing': 'anywhere'}
        self.assertEqual(self.line()['text'], 'A move. You said you would move for this: anywhere.')


class RelocationSchemaTests(unittest.TestCase):
    def check(self, relocation):
        config = H.example_config()
        config.setdefault('candidate', {})['relocation'] = relocation
        return V.check(config, H.schema('config.schema.json'))

    def test_accepts_all_fields(self):
        self.assertEqual(self.check({'willing': 'some_places', 'classes': ['us'],
            'from': '2027-03', 'minimum_pay': {'amount': 300000, 'currency': 'USD'},
            'needs_sponsorship_paid': True, 'organisations_regardless': ['acme'],
            'evidence': 'E01', 'answered_on': '2026-11-07'}), [])
        for willing in ['anywhere', 'no', 'unsure']:
            self.assertEqual(self.check({'willing': willing}), [])

    def test_rejects_unknown_property_and_bad_willing(self):
        self.assertTrue(self.check({'willing': 'maybe'}))
        self.assertTrue(self.check({'willing': 'anywhere', 'unknown': True}))
        self.assertTrue(self.check({}))

    def test_classes_only_with_some_places(self):
        self.assertTrue(self.check({'willing': 'some_places'}))
        for willing in ['anywhere', 'no', 'unsure']:
            self.assertTrue(self.check({'willing': willing, 'classes': ['us']}))

    def test_rejects_bad_terms(self):
        for extra in [{'from': '2027-13'}, {'from': 'tomorrow'},
                      {'minimum_pay': {'amount': -1, 'currency': 'USD'}},
                      {'minimum_pay': {'amount': 1, 'currency': 'dollars'}},
                      {'minimum_pay': {'amount': 1}},
                      {'needs_sponsorship_paid': 'yes'}, {'answered_on': 'today'}]:
            self.assertTrue(self.check(dict(willing='anywhere', **extra)))


class RelocationIntegrationTests(unittest.TestCase):
    def test_page_and_agent_roles_carry_pay_and_move_without_changing_scores(self):
        ws = H.copy_demo(self)
        config = H.load(os.path.join(ws, 'config.json'))
        data = B.Data(ws, config)
        before = H.deep(data.cur)
        roles = B.build_roles(data, {}, set())
        home = B.home_class(config)
        for r in roles:
            self.assertEqual(r['pay'], B.clean(data.role_index[r['id']].get('compensation')) or None)
            self.assertEqual('mv' in r, r['lc'] != home)
        B.main(['--workspace', ws])
        payload = H.load(os.path.join(ws, 'report', 'for-agents', 'dashboard.json'))
        self.assertTrue(all('pay' in r for r in payload['roles']))
        self.assertTrue(any('mv' in r for r in payload['roles']))
        self.assertEqual(data.cur, before)

    def test_sensitive_agent_files_mask_floor_but_preserve_posted_pay(self):
        ws = H.copy_demo(self)
        config = H.load(os.path.join(ws, 'config.json'))
        config['privacy']['sensitive_mode'] = True
        config['candidate']['relocation'] = {'willing': 'anywhere',
            'minimum_pay': {'amount': 312345, 'currency': 'USD'}}
        H.save(os.path.join(ws, 'config.json'), config)
        path = os.path.join(ws, 'market', 'roles', 'latest.json')
        postings = H.load(path)
        for r in postings['roles']:
            r['compensation'] = 'USD 400,000'
        H.save(path, postings)
        B.main(['--workspace', ws])
        payload = H.load(os.path.join(ws, 'report', 'for-agents', 'dashboard.json'))
        for r in payload['roles']:
            self.assertEqual(r['pay'], 'USD 400,000')
            if r.get('mv'):
                self.assertIn('[salary]', r['mv']['text'])
                self.assertNotIn('312,345', r['mv']['text'])
        summary = open(os.path.join(ws, 'report', 'for-agents', 'SUMMARY.md'), encoding='utf-8').read()
        self.assertIn('Relocation: would move anywhere, for [salary] a year or more.', summary)
        self.assertNotIn('312,345', summary)
        _, page = page_data(ws)
        self.assertTrue(any('312,345' in r.get('mv', {}).get('text', '') for r in page['roles']))

    def test_summary_no_or_unanswered(self):
        for willing, expected in [('no', 'would not move'), ('unsure', 'not asked yet'), (None, 'not asked yet')]:
            ws = H.copy_demo(self)
            path = os.path.join(ws, 'config.json')
            config = H.load(path)
            config['candidate'].pop('relocation', None)
            if willing:
                config['candidate']['relocation'] = {'willing': willing}
            H.save(path, config)
            B.main(['--workspace', ws])
            summary = open(os.path.join(ws, 'report', 'for-agents', 'SUMMARY.md'), encoding='utf-8').read()
            self.assertIn('Relocation: ' + expected, summary)

    def test_today_adds_only_the_best_roles_move_sentence(self):
        ws = H.copy_demo(self)
        data = B.Data(ws, H.load(os.path.join(ws, 'config.json')))
        _, page = B.render_page(data)
        with mock.patch.object(T.G, 'starting_line', return_value={
                'role_id': page['roles'][0]['id'], 'level': 3, 'band': 'Moderate',
                'role': 'Test role', 'org': 'Acme', 'fit_text': '60'}):
            best = page['roles'][0]
            best.pop('mv', None)
            home = T.build(page, data, {})['stand']
            for verdict, sentence in [
                ('willing', ' You said you would move for this.'),
                ('below_floor', " It is a move, and the posting's pay is below your floor."),
                ('not_willing', ' It is a move you said you would not make.'),
                ('unknown', ' It is outside your home area; you have not said whether you would move.')]:
                best['mv'] = {'verdict': verdict, 'text': 'Moving terms'}
                self.assertEqual(T.build(page, data, {})['stand'], home + sentence)
            best.pop('mv')
            self.assertEqual(T.build(page, data, {})['stand'], home)


class RelocationValidationTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        self.path = os.path.join(self.ws, 'config.json')
        self.config = H.load(self.path)

    def validate(self):
        H.save(self.path, self.config)
        errors, warnings, _ = V.validate_workspace(self.ws)
        return '\n'.join(errors), '\n'.join(warnings)

    def test_unknown_class_and_target_are_errors(self):
        self.config['candidate']['relocation'] = {'willing': 'some_places',
            'classes': ['absent'], 'organisations_regardless': ['absent']}
        errors, _ = self.validate()
        self.assertIn("relocation class 'absent' is not a location class id", errors)
        self.assertIn("relocation organisation 'absent' is not a target id", errors)

    def test_missing_evidence_warns(self):
        self.config['candidate']['relocation']['evidence'] = 'missing'
        errors, warnings = self.validate()
        self.assertEqual(errors, '')
        self.assertIn("relocation evidence 'missing' is not in profile/evidence.json", warnings)

    def test_no_move_conflicting_d6_warns_only_outside_home(self):
        self.config['candidate']['relocation'] = {'willing': 'no'}
        _, warnings = self.validate()
        profile = H.load(os.path.join(self.ws, 'eval', 'profile-dimensions.json'))
        home = B.home_class(self.config)
        names = {c['id']: c['name'] for c in self.config['locations']['classes']}
        for key, entry in profile['D6_rules']['classes'].items():
            message = 'the person said they would not move, but the D6 rule for %s scores %s' % (names.get(key, key), entry['score'])
            self.assertEqual(message in warnings, key != home and entry['score'] > 0)

    def test_unasked_warning_counts_current_roles_outside_home(self):
        self.config['candidate'].pop('relocation')
        _, warnings = self.validate()
        data = B.Data(self.ws, self.config)
        home = B.home_class(self.config)
        count = sum(r['location_class'] != home for r in data.cur['roles'])
        name = next(c['name'] for c in self.config['locations']['classes'] if c['id'] == home)
        self.assertIn('%d open roles are outside %s and the person has not been asked whether they would move: method/INTAKE.md section 2, question 4' % (count, name), warnings)
        self.config['candidate']['relocation'] = {'willing': 'unsure'}
        self.assertNotIn('has not been asked', self.validate()[1])
