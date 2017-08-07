import itertools
from functools import reduce
from operator import attrgetter
from typing import Dict, Iterable, Iterator, List, Set, Tuple, TypeVar

from toposort import toposort

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


def max_ranked_after_factory(movies: Iterable[Movie]):
    ranks: List[int] = sorted(m.rank for m in movies if m.rank)
    runs = consecutive_runs(ranks)

    def max_ranked_after(m: Movie) -> Movie:
        """Get the last movie in a run of consecutively ranked movies that has the given movie.

        Example: if there are movies with ranks #10-13, this will return #13 for any of them."""
        if not m.rank:
            return m
        for run in runs:
            if m.rank in run:
                if m.rank == run[-1]:  # m is the end of the run, no adjustment needed
                    return m
                return get_by_attr(movies, 'rank', run[-1])
        raise Exception(f"Can't find rank {m.rank} in a list of all ranks, this can't happen")

    return max_ranked_after


def set_lower_bounds_by_year(movies: Iterable[Movie]):
    """Set which movie goes after which based on yearly top-25s.

    Relies on MovieList being sorted by year, then by rby.
    Movies without rby should appear only after those with rby."""
    movies_by_year: Iterable[Tuple[int, Iterable[Movie]]] = \
        itertools.groupby(movies, attrgetter('year'))
    max_ranked_after = max_ranked_after_factory(movies)

    for year, mvs in movies_by_year:
        prev, seen_missing_rby = None, False
        for m in mvs:
            # if both have ranks, bounds will be set in another function
            if prev and not (m.rank and prev.rank):
                m.set_after(max_ranked_after(prev))
            if m.rby:
                if seen_missing_rby or (prev and m.rby != prev.rby + 1):
                    raise ValueError(f'Rank by year conflicts with other movies:\n{m}')
                prev = m
            else:
                seen_missing_rby = True


def set_lower_bounds_by_rank(movies: Iterable[Movie]):
    """Chain all ranked movies after each other."""
    ranked = sorted((m for m in movies if m.rank), key=attrgetter('rank'))
    for m1, m2 in window(ranked):
        m2.set_after(m1)


# TODO: set_lower_bound_by_year rework seems to have made this unnecessary?
def remove_redundant_bounds(movies: Iterable[Movie]):
    adjusted = 0
    for m in movies:
        after_ranked = [m_ for m_ in m.after if m_.rank]
        if len(after_ranked) > 1:  # exclude trivial cases
            print(f'#{m.id} is after: {", ".join(m_.compact() for m_ in m.after)} -> ', end='')
            closest_after = sorted(after_ranked, key=lambda x: x.rank)[:-1]
            m.after = [m_ for m_ in m.after if m_ not in closest_after]
            print(m.after_ids)
            adjusted += 1
    print(f'{adjusted} movies had redundant lower bounds removed')


def get_id_graph(movies: Iterable[Movie]) -> Dict[str, Set[str]]:
    # toposort requires sets
    return {m.id: set(m.after_ids) for m in movies if m.after}


def set_approx_pos(movies: Iterable[Movie]):
    for i, same_pos in enumerate(toposort(get_id_graph(movies)), start=1):
        for m_id in same_pos:
            get_by_attr(movies, 'id', m_id).res = i
    print(f'{i} groups in the graph (more = better)')


def shift_down_movies_with_no_upper_bound(movies: Iterable[Movie]):
    # all rows that are mentioned in 'After' fields
    have_upper_limit = set(m_ for m in movies if m.after for m_ in m.after)
    # the rest
    no_upper_limit = (m for m in movies if m not in have_upper_limit)
    adjusted = 0
    for m in no_upper_limit:
        if m.res and not m.rank:
            m.res += 1000
            adjusted += 1
    print(f'{adjusted} unranked movies have no upper limit')


# returns chains of unranked rows between ranked
def get_chains(movies: Iterable[Movie]):
    chains = ([m] for m in movies if m.rank and m.after)
    good_chains = []
    for chain in chains:
        head = chain[0]
        found_chain_end, nontrivial = False, False
        # print(head)
        while not found_chain_end:
            # print(head)
            unranked_prev = [m for m in head.after if not m.rank]
            ranked_prev = [m for m in head.after if m.rank]
            nontrivial |= len(unranked_prev) > 0  # turns to True only once
            prevs = unranked_prev or ranked_prev
            if prevs:
                assert len(prevs) == 1
                head = prevs[0]
                chain.append(head)
                found_chain_end = bool(head.rank)
            else:
                break
        else:  # no break, ended on a ranked row
            if len(chain) > 1 and nontrivial:
                good_chains.append(chain[::-1])
    return good_chains


def process_chains(chains):
    # if two chains differ only in the last item, leave the shortest
    def only_shortest(acc, chain):
        def head_rank(ch):
            return ch[-1].rank

        if not acc:
            return [chain]
        else:
            last = acc[-1]
            if last[:-1] == chain[:-1]:  # all except heads match
                # return a chain with the smallest head
                if head_rank(last) > head_rank(chain):
                    acc[-1] = chain
                return acc
            else:
                acc.append(chain)
                return acc

    # source sorting by year -> by rby ensures that reduce will work
    chains = reduce(only_shortest, chains, [])
    # chains.sort(key=lambda x: x[0].rank)
    chains.sort(key=len, reverse=True)
    chains.sort(key=lambda x: x[-1].rank - x[0].rank)
    print(f'\n{len(chains)} chains:')
    for a_chain in chains:
        print(' —→ '.join(m.compact() for m in a_chain))


def process_all(gen_chains=True):
    # mlist = get_final_collated_list()
    mlist = MovieList.read_from_file('input.csv')
    print(f'{mlist.count_ranked()} movies are ranked')

    set_lower_bounds_by_year(mlist.movies)
    set_lower_bounds_by_rank(mlist.movies)
    remove_redundant_bounds(mlist.movies)

    set_approx_pos(mlist.movies)
    shift_down_movies_with_no_upper_bound(mlist.movies)
    print(f'{mlist.count_no_info()} items have no ranks and no lower bounds')
    if gen_chains:
        process_chains(get_chains(mlist.movies))

    mlist.sort()
    mlist.write_to_file('output.csv')
    return mlist


if __name__ == '__main__':
    process_all()
    # TODO: don't assume anything about movies not in yearly tops (years have lots of mistakes)
