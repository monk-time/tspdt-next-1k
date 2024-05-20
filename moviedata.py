import csv
import inspect
import random
from collections import OrderedDict
from collections.abc import Iterable
from itertools import permutations
from string import ascii_lowercase


def unique_ids() -> list[str]:
    chars = ascii_lowercase + '2345678'  # 33 * 32 - 7 * 6 = 1014 possible ids
    ids = [p for p in map(''.join, permutations(chars, 2)) if not p.isdigit()]
    assert len(ids) == 1014
    random.seed(0)  # for hash reproducibility
    random.shuffle(ids)
    return ids


class Movie:
    _free_ids = unique_ids()

    def __init__(
        self,
        title: str,
        year: int,
        rby: int | None = None,
        rank: int | None = None,
    ):
        self.title = title
        if not isinstance(year, int):
            msg = f'Year ({year}) for "{title}" must be an integer'
            raise TypeError(msg)
        self.year = year
        if rby is not None and not 1 <= rby <= 25:
            msg = f'Invalid rank by year ({rby}) for "{title}" ({year})'
            raise ValueError(msg)
        self.rby: int | None = rby  # rank by year
        if rank is not None and not 1001 <= rank <= 2000:
            msg = f'Invalid rank ({rank}) for "{title}" ({year})'
            raise ValueError(msg)
        self.rank: int | None = rank

        # these fields can only get default values during initialization
        self.id: str = self._free_ids.pop()
        self.after: list[Movie] = []
        self.before: list[Movie] = []
        self.range: tuple[int, int] | None = (
            None  # inclusive, set only for unranked movies
        )

    @property
    def after_ids(self) -> list[str]:
        return [m.id for m in self.after]

    @property
    def before_ids(self) -> list[str]:
        return [m.id for m in self.before]

    def set_after(self, antecedent: 'Movie'):
        if antecedent not in self.after:
            self.after.append(antecedent)

    def set_before(self, consequent: 'Movie'):
        if consequent not in self.before:
            self.before.append(consequent)

    def __str__(self):
        return (
            f'#{self.id}: [{self.rby or '-':>2}, @{self.rank or '----'}, '
            f'{self.after_ids!s:<10}..{self.before_ids!s:<10}] '
            f'{self.year} - {self.title}'
        )

    def compact(self):
        """Get a short string representation of the movie."""
        return f'#{self.id} @{self.rank or '----'}'

    attr_to_field_map = OrderedDict(
        title='Title',
        year='Year',
        rby='Rank by year',
        rank='Rank',
        res='Res',
        id='Hash',
        after_ids='After',
        before_ids='Before',
        range='Range',
    )
    # keys that can be used for constructing a Movie instance
    allowed_attrs: list[str] = inspect.getfullargspec(__init__).args[1:]

    def form_row(self):
        """Prepare a movie for writing to a .csv file.

        A proper field order is preserved.
        Missing or falsy attributes are converted to '-'.
        """
        return [getattr(self, k, '-') or '-' for k in self.attr_to_field_map]

    @classmethod
    def from_row(cls, row: Iterable[str]):
        """Create a movie from a .csv row.

        Uses only fields that can be used for constructing a Movie instance.
        Reversed form_row.
        """
        kwargs = {
            k: v
            for k, v in zip(cls.attr_to_field_map.keys(), row)
            if k in cls.allowed_attrs
        }
        for k in ['year', 'rby', 'rank']:
            kwargs[k] = int(kwargs[k]) if kwargs[k] != '-' else None
        return cls(**kwargs)


class MovieList:
    def __init__(self, it: Iterable[Movie]):
        self.movies = list(it)
        self.sort()
        self.unranked = [m for m in self.movies if not m.rank]
        self.ranks = sorted(m.rank for m in self.movies if m.rank)

    def sort(self):
        self.movies.sort(key=lambda m: (m.year, m.rby or 99, m.rank or 9999))

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
        return 1000 - len(self.unranked)
