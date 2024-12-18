"""Use this for collating the data from three different places on TSPDT.

All tables must be converted to .tsv manually before use:
in Excel click 'Save as -> Unicode Text (.txt)' (tab-separated, UTF16-LE),
that's the only way to preserve unicode chars in Excel.
Rename files to .tsv after exporting.

The third file with actual ranks comes from a JS-scraper for director pages.
"""

import csv
import re
from collections import Counter, OrderedDict
from collections.abc import Callable, Iterable, Mapping, MutableMapping
from pathlib import Path

from moviedata import Movie, MovieList
from unidecode import unidecode

PATH_NEXT1K = 'data/Films-Ranked-1001-2000.tsv'
PATH_YEARLY_TOP25 = 'data/Yearly-Top-25s-GF1000.tsv'
PATH_DIRECTORS = 'data/directors_scraped.tsv'


def parse_tsv(filename: str, row_modifier: Callable) -> list[dict]:
    """Open a .tsv file exported from Excel, applying a function to each row.

    Falsy rows are skipped.
    """
    with Path(filename).open(encoding='utf-16') as f:
        reader = csv.DictReader(f, dialect='excel-tab')
        return list(filter(None, map(row_modifier, reader)))


def pick(keys: Iterable, d: Mapping, f: Callable = lambda x: x) -> dict:
    """Return a dictionary with only provided keys.

    Optionally pass through a given function.
    """
    return {key: f(d[key]) for key in keys if key in d}


def mod_next1k(row: Mapping) -> OrderedDict:
    return OrderedDict({
        # take the lower year from ranges
        'Year': int(re.match(r'\d{4}', row['Year']).group()),
        'Title': row['Title'],
        'Director': normalize_directors(row['Director']),
    })


def mod_dirs(row: Mapping) -> OrderedDict:
    return OrderedDict(
        **pick(['Pos', 'Year'], row, int), **pick(['Title', 'Director'], row)
    )


def prepare_yearly_file():
    """Rewrite the file with yearly Top-25s (groups often have wrong years)."""
    filler = '\t\t\t\t\t\n'
    with Path(PATH_YEARLY_TOP25).open(encoding='utf-16') as f:
        header = f.readline()
        groups = f.read().split(filler)
    group_items = lambda g: g.rstrip('\n').split('\n')
    years_in_group = lambda g: (s[:4] for s in group_items(g))
    years = [Counter(years_in_group(g)).most_common(1)[0][0] for g in groups]
    assert len(set(years)) == len(years)

    groups_updated = (
        '\n'.join(year + s[4:] for s in group_items(g)) + '\n'
        for g, year in zip(groups, years)
    )
    with Path(PATH_YEARLY_TOP25).open(mode='w', encoding='utf-16') as f:
        f.write(header)
        f.write(filler.join(groups_updated))


def mod_yearly(row: Mapping) -> OrderedDict | None:
    return (
        OrderedDict({
            'Rank by year': int(row['Pos']),
            'Year': int(row['Year']),
            'Title': extract_title(row['Title/Year/Country/Length/Colour']),
            'Director': normalize_directors(row['Director']),
        })
        if row['Overall Pos'] == '1001-2000'
        else None
    )


def extract_title(field: str) -> str:
    # Sometimes a year is not the first value after a bracket
    title = re.fullmatch(
        r"""
        \s*(.+)\s+          # film title; trim whitespace
        \((
           .*\b\d{4}.*   # extra info in parens, incl. year
        )\)\s*
        """,
        field,
        re.VERBOSE,
    )
    if not title:
        msg = f"Can't extract film title from this row:\n    {field}"
        raise ValueError(msg)
    return title.group(1)


def normalize_directors(s: str) -> str:
    """Restore proper first-last name order.

    Use a uniform separator between multiple names.
    """
    flip = lambda name: ' '.join(reversed(name.split(', ')))
    return ' & '.join(map(flip, re.split(r' & |/', s)))


ARTICLES = [
    'the',
    'a',
    'an',
    'le',
    'la',
    'les',
    'un',
    'une',
    'der',
    'die',
    'das',
    'il',
    'el',
    'o',
    'os',
]
RE_TRAILING_ARTICLES = re.compile(f', (?:{"|".join(ARTICLES)})$')
RE_BRACKETED_SUFFIX = re.compile(r' \[[^\]]+\]$')


def norm_str(s: str) -> str:
    """Normalize a string.

    Remove diacritics, capitalization, trailing articles
    and bracketed suffixes.
    """
    s = unidecode(s.lower())
    s = re.sub(RE_BRACKETED_SUFFIX, '', s)
    return re.sub(RE_TRAILING_ARTICLES, '', s)


def title_match(row1: Mapping, row2: Mapping) -> bool:
    return norm_str(row1['Title']) == norm_str(row2['Title'])


def full_match(row1: Mapping, row2: Mapping) -> bool:
    return (
        row1['Director'] == row2['Director']
        and abs(row1['Year'] - row2['Year']) < 2
    )


def collate(
    target: list[MutableMapping], source: list[Mapping], keys: list[str]
):
    """Copy fields from a list of movies into matching movies in another list.

    Mutates rows in target.

    Raises:
        ValueError: if sources can't be fully collated.
    """
    remaining = target.copy()
    for src_row in source:
        match = None
        matches = [r for r in remaining if title_match(r, src_row)]
        if len(matches) > 1:
            full_matches = [r for r in matches if full_match(r, src_row)]
            if len(full_matches) > 1:
                print(
                    'Found several full matches:',
                    src_row,
                    full_matches,
                    sep='\n',
                )
            elif not full_matches:
                print(
                    "Can't find a full match among matching titles:",
                    src_row,
                    matches,
                    sep='\n',
                )
            else:
                match = full_matches[0]
        elif not matches:
            print("Can't find this row in target:", src_row, sep='\n')
        else:
            match = matches[0]

        if match:
            remaining.remove(match)
            for k in keys:
                match[k] = src_row[k]

    if len(target) - len(remaining) != len(source):
        msg = "Can't fully collate two sources."
        raise ValueError(msg)


def get_final_collated_list() -> MovieList:
    """Collate all three sources together."""
    print('Parsing lists from TSPDT...')
    next1k = parse_tsv(PATH_NEXT1K, mod_next1k)
    assert len(next1k) == 1000
    print(f'Next1k: {len(next1k)} movies')

    dirs = parse_tsv(PATH_DIRECTORS, mod_dirs)
    print(f'Directors: {len(dirs)} movies')

    prepare_yearly_file()
    yearly = parse_tsv(PATH_YEARLY_TOP25, mod_yearly)
    print(f'Yearly: {len(yearly)} movies')

    collate(next1k, dirs, ['Pos'])
    collate(
        next1k, yearly, ['Rank by year', 'Year']
    )  # years must match ranks by year
    assert len(dirs) == sum(1 for row in next1k if 'Pos' in row)
    assert len(yearly) == sum(1 for row in next1k if 'Rank by year' in row)

    return MovieList(
        Movie(
            title=row['Title'],
            year=row['Year'],
            rby=row.get('Rank by year'),
            rank=row.get('Pos'),
        )
        for row in next1k
    )


if __name__ == '__main__':
    mlist_ = get_final_collated_list()
    mlist_.write_to_file('input.csv')
