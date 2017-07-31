"""Use this for collating the data from three different places on TSPDT.

All tables must be converted to .csv manually before use:
in Excel click 'Save as -> Unicode Text (.txt)' (tab-separated, UTF16-LE),
that's the only way to preserve unicode chars in Excel.
Rename files to .csv after exporting.

The third file with actual ranks comes from a JS-tool that scrapes director pages."""

import csv
import re
from collections import OrderedDict
from typing import Callable, Dict, Iterable, List, Mapping, Optional

PATH_NEXT1K = 'data/Films-Ranked-1001-2000.csv'
PATH_YEARLY_TOP25 = 'data/Yearly-Top-25s-GF1000.csv'
PATH_DIRECTORS = 'data/directors_scraped.csv'


def parse_tsv(filename: str, row_modifier: Callable) -> List[Dict]:
    """Open a .csv file exported from Excel, applying a modifier function to each row.
    Falsy rows are skipped."""
    with open(filename, encoding='utf-16') as f:
        rows = list(filter(None, map(row_modifier, csv.DictReader(f, dialect='excel-tab'))))
    return rows


def pick(keys: Iterable, d: Mapping, f: Callable = lambda x: x) -> dict:
    """Return a dictionary only with provided keys, optionally passed through a given function."""
    return {key: f(d[key]) for key in keys if key in d}


def mod_next1k(row: Mapping) -> OrderedDict:
    return OrderedDict({
        'Year': int(re.match('\d{4}', row['Year']).group()),  # take the lower year from ranges
        'Title': row['Title'],
        'Director': normalize_directors(row['Director'])})


def mod_dirs(row: Mapping) -> OrderedDict:
    return OrderedDict(**pick(['Pos', 'Year'], row, int),
                       **pick(['Title', 'Director'], row))


def mod_yearly(row: Mapping) -> Optional[OrderedDict]:
    return OrderedDict({
        'Yearly Pos': int(row['Pos']),
        'Year': int(row['Year']),
        'Title': extract_title(row['Title/Year/Country/Length/Colour']),
        'Director': normalize_directors(row['Director'])
    }) if row['Overall Pos'] == '1001-2000' else None


def extract_title(field: str) -> str:
    # Sometimes a year is not the first value after a bracket
    title = re.fullmatch(r"""
        \s*(.+)\s+          # film title; trim whitespace
        \((
           .*\b\d{4}.*   # extra info in parens, incl. year
        )\)\s*
        """, field, re.VERBOSE)
    if not title:
        raise ValueError(f"Can't extract film title from this row:\n    {field}")
    return title.group(1)


def normalize_directors(s: str) -> str:
    """Restore proper first-last name order and use a uniform separator between multiple names."""
    def flip(name):
        return ' '.join(reversed(name.split(', ')))

    return ' & '.join(map(flip, re.split(' & |/', s)))


def main():
    next1k = parse_tsv(PATH_NEXT1K, mod_next1k)
    # pprint(next1k, width=200)
    print(f'Next1k: {len(next1k)}')

    dirs = parse_tsv(PATH_DIRECTORS, mod_dirs)
    # pprint(dirs, width=200)
    print(f'Directors: {len(dirs)}')

    yearly = parse_tsv(PATH_YEARLY_TOP25, mod_yearly)
    # pprint(yearly, width=200)
    print(f'Yearly: {len(yearly)}')


if __name__ == '__main__':
    main()
