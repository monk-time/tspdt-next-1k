import itertools
from functools import partial
from operator import attrgetter, itemgetter
from typing import Callable, Iterable, Iterator, List, Tuple, TypeVar

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


def count_in_range(it: Iterable[int], min_value: int, max_value: int) -> int:
    """Count how many numbers in an iterable are between given values (inclusive)."""
    return sum(1 for _ in (n for n in it if min_value <= n <= max_value))


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


def rec_traversal_factory(direction: str, f: Callable, diff: int, extreme: int):
    def traverse(m: Movie):
        neighbors, bounds, depth = getattr(m, direction)[:], [], 0
        while neighbors:  # breadth-first search
            deeper_neighbors = []
            for n in neighbors:
                if n.rank:
                    # all items in a chain of unranked movies should be able to fit
                    bounds.append(n.rank + diff + diff * depth)
                else:
                    deeper_neighbors.extend(getattr(n, direction))
            neighbors = deeper_neighbors
            depth += 1
        return f(bounds, default=extreme)

    return traverse


def calculate_ranges(mlist: MovieList):
    """Determine places that each unranked movie may have by traversing their neighbors recursively
    until a ranked one is found."""
    min_free_rank = next(r for r in range(1001, 2001) if r not in mlist.ranks)
    max_free_rank = next(r for r in range(2000, 1000, -1) if r not in mlist.ranks)
    find_min_possible_rank = rec_traversal_factory('after', max, 1, min_free_rank)
    find_max_possible_rank = rec_traversal_factory('before', min, -1, max_free_rank)
    for m in mlist.unranked:
        m.range = (find_min_possible_rank(m), find_max_possible_rank(m))


def find_shortest_ranges(mlist: MovieList, limit: int = 5):
    print('\nUnranked movies sorted by the number of possible ranks they may have:')
    num_choices = [m.range[1] - m.range[0] + 1 - count_in_range(mlist.ranks, *m.range)
                   for m in mlist.unranked]
    for n, m in sorted(zip(num_choices, mlist.unranked), key=itemgetter(0))[:limit]:
        print(f'{n:3} {m.range} | {m}')


def process_all():
    # mlist = get_final_collated_list()
    mlist = MovieList.read_from_file('input.csv')
    print(f'{mlist.count_ranked()} movies are ranked')

    set_bounds_by_year(mlist.movies)
    calculate_ranges(mlist)
    find_shortest_ranges(mlist)

    mlist.write_to_file('output.csv')


if __name__ == '__main__':
    process_all()
    # TODO: don't assume anything about movies not in yearly tops (years have lots of mistakes)
