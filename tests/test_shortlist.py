import collections
import hashlib
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shortlist import mmr
ROOT=Path(__file__).resolve().parents[1]

class ShortlistTests(unittest.TestCase):
 def test_pilot_provenance_and_diversity(self):
  rows=json.loads((ROOT/'data/candidates.json').read_text())
  self.assertEqual(len(rows),24)
  self.assertEqual(len({c['address'] for c in rows}),24)
  self.assertEqual(len({c['metadataHash'] for c in rows}),24)
  needs=collections.Counter(c['need'] for c in rows)
  self.assertEqual(len(needs),8)
  self.assertTrue(all(3<=n<=5 for n in needs.values()))
  self.assertTrue(all(n<=2 for n in collections.Counter((c['need'],c['registry']) for c in rows).values()))
  for c in rows:
   self.assertTrue(c['license']['verified'])
   self.assertEqual(hashlib.sha256((ROOT/'data/evidence'/(c['id']+'.json')).read_bytes()).hexdigest(),c['version'])
   self.assertTrue(c['signals'])
 def test_mmr_respects_registry_cap(self):
  rows=[dict(id=str(i),registry='a' if i<4 else 'b',score=1,tags=['same'],dependencies=[],pattern='same') for i in range(5)]
  chosen=mmr(rows,4)
  self.assertEqual(len(chosen),3)
  self.assertEqual(sum(c['registry']=='a' for c in chosen),2)

if __name__=='__main__':unittest.main()
