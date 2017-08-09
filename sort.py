import itertools
from functools import partial
from operator import attrgetter
from typing import Iterable, Iterator, List, Tuple, TypeVar

from moviedata import Movie, MovieList

T = TypeVar('T')


def window(it: Iterable[T], size: int = 2) -> Iterator[Tuple[T, ...]]:
    """Get rolling windows of a given size from an iterable.

    Example: window(range(4), 2) == [(0, 1), (1, 2), (2, 3)]"""
    # noinspection PyArgumentEqualDefault
    iters = [itertools.islice(it, i, None) for i in range(size)]
    return zip(*iters)


def consecutive_runs(it: Iterable[int]) -> List[List[int]]:
    """Split an array into groups of consecutive increasing values in it.

    Example: consecutive_runs([2, 3, 4, 7, 12, 13]) == [[2, 3, 4], [7], [12, 13]]"""
    groups = itertools.groupby(enumerate(it), lambda ix: ix[0] - ix[1])
    return [[x for _, x in g] for _, g in groups]


def get_by_attr(objects: Iterable[T], attr: str, value) -> T:
    """Find the first object with a given attribute set to value."""
    res = next(o for o in objects if hasattr(o, attr) and getattr(o, attr) == value)
    if res is not None:
        return res
    else:
        raise Exception(f'None of the given objects have {attr} set to {value}')


def minmax_conseq_ranked_near_factory(movies: Iterable[Movie]):
    ranks: List[int] = sorted(m.rank for m in movies if m.rank)
    runs = consecutive_runs(ranks)

    def minmax_conseq_ranked_near(m: Movie, run_index: int) -> Movie:
        """Get the first or the last movie in a run of consecutively ranked movies that has the given movie.

        Example: if there are movies with ranks #10-13, this will return #13 for any of them."""
        if not m.rank:
            return m
        for run in runs:
            if m.rank in run:
                if m.rank == run[run_index]:  # m is the end of the run, no adjustment needed
                    return m
                return get_by_attr(movies, 'rank', run[run_index])
        raise Exception(f"Can't find rank {m.rank} in a list of all ranks, this can't happen")

    min_conseq_ranked_near = partial(minmax_conseq_ranked_near, run_index=0)
    max_conseq_ranked_near = partial(minmax_conseq_ranked_near, run_index=-1)
    return min_conseq_ranked_near, max_conseq_ranked_near


def set_bounds_by_year(movies: Iterable[Movie]):
    """Set for unranked movies which movies go after and before them based on yearly top-25s.

    Relies on MovieList being sorted by year, then by rby.
    Movies without rby should appear only after those with rby."""
    movies_by_year: Iterable[Tuple[int, Iterable[Movie]]] = \
        itertools.groupby(movies, attrgetter('year'))
    min_conseq_ranked_near, max_conseq_ranked_near = minmax_conseq_ranked_near_factory(movies)

    for year, mvs in movies_by_year:
        prev, seen_missing_rby = None, False
        for m in mvs:
            if prev:
                if not m.rank:
                    m.set_after(max_conseq_ranked_near(prev))
                if not prev.rank and not (seen_missing_rby and m.rank):
                    # only the first ranked movie without rby should be set as upper bound
                    prev.set_before(min_conseq_ranked_near(m))
            if m.rby:
                if seen_missing_rby or (prev and m.rby != prev.rby + 1):
                    raise ValueError(f'Rank by year conflicts with other movies:\n{m}')
                prev = m
            else:
                seen_missing_rby = True


def calculate_ranges(movies: Iterable[Movie]):
    """Determine places that each unranked movie may have by traversing their neighbors recursively
    until a ranked one is found."""
    for m in movies:
        rec_after, lower_bounds = m.after[:], []
        while rec_after:
            m_ = rec_after.pop()
            if m_.rank:
                lower_bounds.append(m_.rank + 1)
            else:
                rec_after.extend(m_.after)
        lower = max(lower_bounds, default=1001)

        rec_before, upper_bounds = m.before[:], []
        while rec_before:
            m_ = rec_before.pop()
            if m_.rank:
                upper_bounds.append(m_.rank - 1)
            else:
                rec_before.extend(m_.before)
        upper = min(upper_bounds, default=2000)

        m.range = (lower, upper)


def find_shortest_ranges(movies: Iterable[Movie]):
    print('\nShortest possible ranges (inclusive) for unranked movies:')
    for m in sorted(movies, key=lambda m: m.range[1] - m.range[0])[:5]:
        print(f'{m.range[1] - m.range[0]:3} {m.range} | {m}')


def process_all():
    # mlist = get_final_collated_list()
    mlist = MovieList.read_from_file('input.csv')
    print(f'{mlist.count_ranked()} movies are ranked')

    set_bounds_by_year(mlist.movies)
    calculate_ranges(mlist.unranked)
    find_shortest_ranges(mlist.unranked)

    mlist.write_to_file('output.csv')


if __name__ == '__main__':
    process_all()
    # TODO: don't assume anything about movies not in yearly tops (years have lots of mistakes)
