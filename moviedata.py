import csv
import random
from collections import OrderedDict
from itertools import permutations
from string import ascii_lowercase
from typing import Iterable, Optional


def unique_ids():
    chars = ascii_lowercase + '2345678'  # 33 * 32 - 7 * 6 = 1014 possible ids
    ids = [p for p in map(''.join, permutations(chars, 2)) if not p.isdigit()]
    assert len(ids) == 1014
    random.seed(0)  # for hash reproducibility
    random.shuffle(ids)
    return ids


class Movie:
    __free_ids = unique_ids()

    def __init__(self, title: str, year: int,
                 rby: Optional[int] = None, rank: Optional[int] = None):
        self.title = title
        self.year = year
        self.rby = rby  # rank by year
        self.rank = rank
        # the following fields can only get default values during initialization
        self.id = self.__free_ids.pop()
        self.res: Optional[int] = None
        self.after = []

    def __str__(self):
        return f'#{self.id}: [{self.rby or "-":>2}, @{self.rank or "----"}, {self.after!s:<10}] ' \
               f'{self.year} - {self.title}'

    @property
    def ranked(self) -> bool:
        return self.rank is not None

    def compact(self):
        """A short string representation of the movie."""
        return f'#{self.id} @{self.rank or "----"}'


class MovieList:
    attr_to_field_map = OrderedDict(title='Title', year='Year', rby='Rank by year', rank='Rank',
                                    res='Res', id='Hash', after='After')

    @classmethod
    def form_row(cls, m: Movie):
        """Prepare a movie for writing to a .csv file, preserving a proper field order.
        Missing or falsy attributes are converted to '-'."""
        return [getattr(m, k) or '-' for k in cls.attr_to_field_map.keys()]

    def __init__(self, it: Iterable[Movie]):
        self.movies = list(it)

    def write_to_file(self, path: str):
        with open(path, mode='w', encoding='utf-8') as f:
            writer = csv.writer(f, dialect=csv.excel(), lineterminator='\n')
            writer.writerow(self.attr_to_field_map.values())
            writer.writerows(map(self.form_row, self.movies))

    def sort(self):
        self.movies.sort(
            key=lambda m: (m.res or 1001, m.year, m.rby or 99, m.rank or 9999))
