import csv
import inspect
import random
from collections import OrderedDict
from itertools import permutations
from string import ascii_lowercase
from typing import Iterable, List, Optional


def unique_ids():
    chars = ascii_lowercase + '2345678'  # 33 * 32 - 7 * 6 = 1014 possible ids
    ids = [p for p in map(''.join, permutations(chars, 2)) if not p.isdigit()]
    assert len(ids) == 1014
    random.seed(0)  # for hash reproducibility
    random.shuffle(ids)
    return ids


class Movie:
    _free_ids = unique_ids()

    def __init__(self, title: str, year: int,
                 rby: Optional[int] = None, rank: Optional[int] = None):
        self.title = title
        if not isinstance(year, int):
            raise ValueError(f'Year ({year}) for "{title}" must be an integer')
        self.year = year
        if rby is not None and not 1 <= rby <= 25:
            raise ValueError(f'Invalid rank by year ({rby}) for "{title}" ({year})')
        self.rby: Optional[int] = rby  # rank by year
        if rank is not None and not 1001 <= rank <= 2000:
            raise ValueError(f'Invalid rank ({rank}) for "{title}" ({year})')
        self.rank: Optional[int] = rank
        # the following fields can only get default values during initialization
        self.id: str = self._free_ids.pop()
        self.res: Optional[int] = None
        self.after: List[Movie] = []

    @property
    def after_ids(self) -> List[str]:
        return [m.id for m in self.after]

    def __str__(self):
        return f'#{self.id}: ' \
               f'[{self.rby or "-":>2}, @{self.rank or "----"}, {self.after_ids!s:<10}] ' \
               f'{self.year} - {self.title}'

    def compact(self):
        """A short string representation of the movie."""
        return f'#{self.id} @{self.rank or "----"}'

    def set_after(self, antecedent: 'Movie'):
        if antecedent not in self.after:
            self.after.append(antecedent)

    attr_to_field_map = OrderedDict(title='Title', year='Year', rby='Rank by year', rank='Rank',
                                    res='Res', id='Hash', after_ids='After')
    # keys that can be used for constructing a Movie instance
    allowed_attrs: List[str] = inspect.getfullargspec(__init__).args[1:]

    def form_row(self):
        """Prepare a movie for writing to a .csv file, preserving a proper field order.
        Missing or falsy attributes are converted to '-'."""
        return [getattr(self, k) or '-' for k in self.attr_to_field_map.keys()]

    @classmethod
    def from_row(cls, row: Iterable[str]):
        """Reversed form_row: create a movie from a .csv row,
        using only fields that can be used for constructing a Movie instance."""
        kwargs = {k: v for k, v in zip(cls.attr_to_field_map.keys(), row)
                  if k in cls.allowed_attrs}
        for k in ['year', 'rby', 'rank']:
            kwargs[k] = int(kwargs[k]) if kwargs[k] != '-' else None
        return cls(**kwargs)


class MovieList:
    def __init__(self, it: Iterable[Movie]):
        self.movies = list(it)
        self.sort()

    def sort(self):
        self.movies.sort(
            key=lambda m: (m.res or 1001, m.year, m.rby or 99, m.rank or 9999))

    def write_to_file(self, path: str):
        with open(path, mode='w', encoding='utf-8') as f:
            writer = csv.writer(f, dialect=csv.excel(), lineterminator='\n')
            writer.writerow(Movie.attr_to_field_map.values())
            writer.writerows(m.form_row() for m in self.movies)

    @classmethod
    def read_from_file(cls, path: str):
        with open(path, encoding='utf-8') as f:
            reader = csv.reader(f, dialect=csv.excel(), lineterminator='\n')
            next(reader)  # skip header
            return cls(map(Movie.from_row, reader))

    def count_ranked(self):
        return sum(1 for m in self.movies if m.rank)

    def count_no_info(self):
        no_info = (m for m in self.movies if not m.after and not m.rank)
        return sum(1 for _ in no_info)
