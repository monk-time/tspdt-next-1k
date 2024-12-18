import itertools
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from functools import partial
from operator import attrgetter, itemgetter
from typing import TypeVar

from moviedata import Movie, MovieList

T = TypeVar('T')


def window(it: Iterable[T], size: int = 2) -> Iterator[tuple[T, ...]]:
    """Get rolling windows of a given size from an iterable.

    Example: window(range(4), 2) == [(0, 1), (1, 2), (2, 3)]
    """
    # noinspection PyArgumentEqualDefault
    iters = [itertools.islice(it, i, None) for i in range(size)]
    return zip(*iters)


def consecutive_runs(it: Iterable[int]) -> list[list[int]]:
    """Split an array into groups of consecutive increasing values in it.

    Example:
    >>> consecutive_runs([2, 3, 4, 7, 12, 13]) == [[2, 3, 4], [7], [12, 13]]
    """
    groups = itertools.groupby(enumerate(it), lambda ix: ix[0] - ix[1])
    return [[x for _, x in g] for _, g in groups]


def get_by_attr(objects: Iterable[T], attr: str, value) -> T:
    """Find the first object with a given attribute set to value.

    Raises:
        ValueError: if none are found.
    """
    res = next(
        o for o in objects if hasattr(o, attr) and getattr(o, attr) == value
    )
    if res is not None:
        return res
    msg = f'None of the given objects have {attr} set to {value}'
    raise ValueError(msg)


def count_in_range(it: Iterable[int], min_value: int, max_value: int) -> int:
    """Count how many ints from iterable are in the given range (inclusive)."""
    return sum(1 for _ in (n for n in it if min_value <= n <= max_value))


def minmax_conseq_ranked_near_factory(
    movies: Iterable[Movie],
) -> tuple[Callable[[Movie], Movie], ...]:
    ranks: list[int] = sorted(m.rank for m in movies if m.rank)
    runs = consecutive_runs(ranks)

    def minmax_conseq_ranked_near(m: Movie, run_index: int) -> Movie:
        """Get the first or the last movie in a run.

        A run consists of consecutively ranked movies that has the given movie.
        Example: if there are movies with ranks #10-13, this will return #13
        for any of them.

        Raises:
            ValueError: if the movie's rank can't be found.
        """
        if not m.rank:
            return m
        for run in runs:
            if m.rank in run:
                if m.rank == run[run_index]:
                    # m is the end of the run, no adjustment needed
                    return m
                return get_by_attr(movies, 'rank', run[run_index])
        msg = f"Can't find rank {m.rank} in all ranks, this can't happen"
        raise ValueError(msg)

    min_conseq_ranked_near = partial(minmax_conseq_ranked_near, run_index=0)
    max_conseq_ranked_near = partial(minmax_conseq_ranked_near, run_index=-1)
    return min_conseq_ranked_near, max_conseq_ranked_near


def set_bounds_by_year(movies: Iterable[Movie]):
    """Set which movies go after and before unranked movies.

    Based on yearly top-25s.
    Relies on MovieList being sorted by year, then by rby.
    Movies without rby should appear only after those with rby.

    Raises:
        ValueError: if rby conflicts with other movies.
    """
    movies_by_year: Iterable[tuple[int, Iterable[Movie]]] = itertools.groupby(
        movies, attrgetter('year')
    )
    min_conseq_ranked_near, max_conseq_ranked_near = (
        minmax_conseq_ranked_near_factory(movies)
    )

    for _year, mvs in movies_by_year:
        prev, seen_missing_rby = None, False
        for m in mvs:
            if prev:
                if not m.rank:
                    m.set_after(max_conseq_ranked_near(prev))
                if not prev.rank and not (seen_missing_rby and m.rank):
                    # only the first ranked movie without rby
                    # should be set as upper bound
                    prev.set_before(min_conseq_ranked_near(m))
            if m.rby:
                if seen_missing_rby or (prev and m.rby != prev.rby + 1):
                    msg = f'Rank by year conflicts with other movies:\n{m}'
                    raise ValueError(msg)
                prev = m
            else:
                seen_missing_rby = True


def rec_traversal_factory(
    direction: str, f: Callable, diff: int, extreme: int
):
    def traverse(m: Movie):
        neighbors, bounds, depth = getattr(m, direction)[:], [], 0
        while neighbors:  # breadth-first search
            deeper_neighbors = []
            for n in neighbors:
                if n.rank:
                    # all items in a chain of unranked movies should fit
                    bounds.append(n.rank + diff + diff * depth)
                else:
                    deeper_neighbors.extend(getattr(n, direction))
            neighbors = deeper_neighbors
            depth += 1
        return f(bounds, default=extreme)

    return traverse


def calculate_ranges(mlist: MovieList):
    """Determine places that each unranked movie may have.

    Traverse their neighbors recursively until a ranked one is found.
    """
    min_free_rank = next(r for r in range(1001, 2001) if r not in mlist.ranks)
    max_free_rank = next(
        r for r in range(2000, 1000, -1) if r not in mlist.ranks
    )
    find_min_possible_rank = rec_traversal_factory(
        'after', max, 1, min_free_rank
    )
    find_max_possible_rank = rec_traversal_factory(
        'before', min, -1, max_free_rank
    )
    for m in mlist.unranked:
        m.range = (find_min_possible_rank(m), find_max_possible_rank(m))


def find_shortest_ranges(mlist: MovieList, limit: int = 5):
    print('\nUnranked movies with the fewest possible ranks:')
    num_choices = [
        m.range[1] - m.range[0] + 1 - count_in_range(mlist.ranks, *m.range)
        for m in mlist.unranked
    ]
    for n, m in sorted(zip(num_choices, mlist.unranked), key=itemgetter(0))[
        :limit
    ]:
        print(f'{n:3} {m.range} | {m}')


def least_crowded_free_ranks(mlist: MovieList):
    print('\nUnfilled ranks that have the fewest candidates for them:')
    all_possible_pos = (
        r
        for m in mlist.unranked
        for r in range(m.range[0], m.range[1] + 1)
        if r not in mlist.ranks
    )
    candidate_counter = Counter(all_possible_pos)
    assert len(candidate_counter) == 1000 - len(mlist.ranks)
    tail = candidate_counter.most_common()[:-6:-1]
    print('\n'.join(f'{num:3} movies for @{rank}' for rank, num in tail))


def process_all():
    # load from cache for subsequent runs
    mlist = MovieList.read_from_file('input.csv')
    print(f'{mlist.count_ranked()} movies are ranked')

    set_bounds_by_year(mlist.movies)
    calculate_ranges(mlist)
    find_shortest_ranges(mlist)
    least_crowded_free_ranks(mlist)

    mlist.write_to_file('output.csv')


if __name__ == '__main__':
    process_all()
