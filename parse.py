"""Use this for collecting and cleaning data from fresh .xls tables from TSPDT site.

All tables must be converted to .csv manually before use.
In Excel choose 'Unicode Text (.txt)' (tab-separated, UTF16-LE),
that's the only way to preserve unicode chars in Excel.
"""

import csv
import re
from collections import OrderedDict
from itertools import groupby
from operator import itemgetter
from typing import Dict, Iterable, List, Mapping

PATH_NEXT1K = 'data/Films-Ranked-1001-2000.csv'
PATH_YEARLY_TOP25 = 'data/Yearly-Top-25s-GF1000.csv'


def parse_tsv(filename) -> List[Dict]:
    """Opens a .csv file exported from Excel."""
    with open(filename, encoding="utf-16") as f:
        cfg = {'dialect': 'excel-tab'}
        rows = list(csv.DictReader(f, **cfg))
    return rows


def extract_title(row: dict) -> str:
    title_full = row['Title/Year/Country/Length/Colour']
    # sometimes a year is not the first value after a bracket
    title = re.fullmatch(r"""
        \s*(.+)\s+          # film title; trim whitespace
        \((
           .*\b\d{4},\s.*   # extra info in parens, incl. year
        )\)
        """, title_full, re.VERBOSE)
    if not title:
        raise AssertionError("Can't extract film title from this row:\n    {}"
                             .format(title_full))
    return title.group(1)


def pick(keys: Iterable, d: Mapping) -> dict:
    """Returns a dictionary with only provided keys."""
    return {key: d[key] for key in keys if key in d}


yearly = parse_tsv(PATH_YEARLY_TOP25)
# pick only relevant rows and fields and add a clean title
yearly1k = ({'Title': extract_title(r), **pick(['Year', 'Director', 'Pos'], r)}
            for r in yearly if r['Overall Pos'] == '1001-2000')
# group by year
iter_g = groupby(yearly1k, itemgetter('Year'))
yearly1k = OrderedDict((int(year), [pick(['Director', 'Title'], r) for r in group])
                       for year, group in iter_g)

# pprint(yearly1k, width=150)
next1k = [pick(['Title', 'Director', 'Year'], r) for r in parse_tsv(PATH_NEXT1K)]
for year, group in yearly1k.items():
    print('{}:'.format(year))
    for pos, r in enumerate(group):
        print("    #{:>2}: {r[Title]:50} - {r[Director]}".format(pos + 1, r=r))
