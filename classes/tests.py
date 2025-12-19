from django.test import TestCase

from utils.etl_normalization import canonical_subject_name, map_grade_level, norm_key


class ETLNormalizationTests(TestCase):
    def test_norm_key_strips_accents_and_case(self):
        self.assertEqual(norm_key('  Educación   Rítmica  '), norm_key('educacion ritmica'))

    def test_map_grade_level_words(self):
        parsed = map_grade_level('Primero', 'A')
        self.assertEqual(parsed.level, '1')
        self.assertEqual(parsed.section, 'A')

    def test_map_grade_level_bachillerato(self):
        parsed = map_grade_level('10o (2o Bachillerato)', 'B (vespertina)')
        self.assertEqual(parsed.level, '10')
        self.assertEqual(parsed.section, 'B')

    def test_canonical_subject_respects_aliases(self):
        aliases = {norm_key('Lenguaje Musica'): 'Lenguaje musical'}
        self.assertEqual(canonical_subject_name('Lenguaje Musica', aliases), 'Lenguaje musical')
