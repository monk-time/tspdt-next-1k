import csv
from collections import OrderedDict
from functools import reduce
from itertools import groupby, tee
from operator import itemgetter

from lib.toposort import toposort


# modified itertools recipe for pairwise: s -> (s0,s1), (s1,s2), (s2, s3), ...
def pairwise(iterable, n=2):
    iters = tee(iterable, n)
    for i in range(1, n):
        for _ in range(i):
            next(iters[i], None)
    return zip(*iters)


def parse(filename="input.csv"):
    with open(filename, encoding="utf-8", newline='') as f:
        header = next(csv.reader(f))  # keeps header sorted
        f.seek(0)  # DictReader needs header for keys
        rows = list(csv.DictReader(f))
        return {'header': header, 'rows': rows}


def output(table, filename="output.csv"):
    with open(filename, mode='w', encoding="utf-8", newline='') as f:
        dialect = csv.excel()
        dialect.lineterminator = '\n'
        writer = csv.DictWriter(f, table['header'], extrasaction='ignore', dialect=dialect)
        writer.writeheader()
        writer.writerows(table['rows'])


def has_rank(r):
    return r['Rank'] != '-'


def row_to_str(r):
    s = '{0:>4}: [{1:>2}, {2:>4}, {3!s:<10}] {4} - {5}'.format(
        r['Hash'], r['Rank by year'], r['Rank'], r['After'], r['Year'], r['Title'])
    return s


def compact_row(r):
    return '#{0:3} @{1:4}'.format(r['Hash'], r['Rank'])


def preview_rows(rows, header=None):
    if header:
        print(header)
    for r in rows:
        print(row_to_str(r))


def preview_dict(rows_by_year):
    for year, rows in rows_by_year.items():
        print('>{0}:'.format(year))
        preview_rows(rows)


def grouped_dict(arr, key):
    by_key = groupby(arr, key)
    return OrderedDict((k, list(vs)) for k, vs in by_key)


# [2, 3, 4, 7, 12, 13] -> [[2, 3, 4], [7], [12, 13]]
def consecutive_runs(num_arr):
    groups = groupby(enumerate(num_arr), lambda ix: ix[0] - ix[1])
    return [[ix[1] for ix in g] for _, g in groups]


# finds the first row with field=value
def row_by_field(rows, field, value):
    res = next(r for r in rows if field in r and r[field] == value)
    if res is not None:
        return res
    else:
        raise Exception('No row with {0}={1}'.format(field, value))


# if you need to insert #15 after #10, and ranks #11-#13 are already used,
# use this to get a function to convert row #10 to #13
def max_ranked_after_factory(rows):
    ranks = sorted(int(r['Rank']) for r in rows if has_rank(r))
    runs = consecutive_runs(ranks)

    def mra(row, guard):
        # should adjust only ranked rows 
        # and only when inserting rankless rows after them 
        if not has_rank(row) or has_rank(guard):
            return row
        rank = int(row['Rank'])
        for run in runs:
            if rank in run:
                if rank != run[-1]:
                    # print('Adjusted #{0} to #{1} from run {2}'.format(rank, run[-1], run))
                    pass
                else:  # no adjustment needed
                    return row
                # return row with rank=run[-1]
                return row_by_field(rows, 'Rank', str(run[-1]))
        else:
            raise Exception('Couldn\'t find a rank in a list of ranks (sic)')

    return mra


def set_after(r, antecedent):
    ante_index = int(antecedent['Hash'])
    if not r['After']:
        r['After'] = [ante_index]
        r['AfterRows'] = [antecedent]
    else:
        if ante_index not in r['After']:
            r['After'].append(ante_index)
            r['AfterRows'].append(antecedent)


def get_after(r):
    return r.get('AfterRows', [])


def compute_edges_by_year(rows):
    rows_by_year = grouped_dict(rows, itemgetter('Year'))
    max_ranked_after = max_ranked_after_factory(rows)

    for year, rows in rows_by_year.items():
        prev, seen_dash = None, False
        for r in rows:
            rby = r['Rank by year']
            if rby != '-':
                rby = int(rby)
                if rby <= 0:
                    raise Exception('rby should be positive; at:\n{0}'.format(row_to_str(r)))
                # dashes can appear only after all numbers
                if not seen_dash and (not prev or rby == int(prev['Rank by year']) + 1):
                    # both are consecutive numbers
                    if prev:  # == not the first in rows
                        set_after(r, max_ranked_after(prev, guard=r))
                    prev = r
                else:
                    raise Exception('Wrong rby ({0}) at:\n{1}'.format(rby, row_to_str(r)))
            else:
                seen_dash = True
                if prev:  # only after encountering a row with rby
                    set_after(r, max_ranked_after(prev, guard=r))


def compute_edges_by_rank(rows):
    with_rank = (r for r in rows if has_rank(r))
    rows_by_rank = sorted(with_rank, key=itemgetter('Rank'))
    for r1, r2 in pairwise(rows_by_rank):
        set_after(r2, r1)


def remove_extra_afters(rows):
    adjusted = 0
    for r in rows:
        ranked_prev_rows = list(filter(has_rank, get_after(r)))
        if len(ranked_prev_rows) > 1:  # exclude trivial cases
            before_closest = sorted(ranked_prev_rows, key=lambda x: int(x['Rank']))[:-1]
            # print('#{0} is after: {1} -> '.format(r['Hash'],
            #     ', '.join([compact_row(a) for a in get_after(r)])), end='')
            r['AfterRows'] = [r2 for r2 in get_after(r) if r2 not in before_closest]
            r['After'] = [int(r2['Hash']) for r2 in r['AfterRows']]
            # print(r['After'])
            adjusted += 1
    print('Removed extra afters in {0} items'.format(adjusted))


# Vertices are 1-based indexes
def get_graph(rows):
    # toposort needs sets, but lists were more useful for testing
    return {int(r['Hash']): set(r['After']) for r in rows if r['After']}


def set_approx_pos(rows):
    i = 1
    for same_pos in toposort(get_graph(rows)):
        for index in same_pos:
            rows[index - 1]['Res'] = i
        i += 1
    print(str(i - 1) + ' groups in the graph (more = better)')


def shift_rows_with_no_upper_limit(rows):
    # all rows that are mentioned in 'After' fields
    have_upper_limit = set(n for r in rows if r['After'] for n in r['After'])
    # the rest
    no_upper_limit = (r for r in rows if int(r['Hash']) not in have_upper_limit)
    adjusted = 0
    for r in no_upper_limit:
        if r['Res'] != '-' and not has_rank(r):
            r['Res'] += 1000
        adjusted += 1
    print('{0} items have no upper limit'.format(adjusted))


# returns chains of unranked rows between ranked
def get_chains(rows):
    chains = ([r] for r in rows if has_rank(r) and r['After'])
    good_chains = []
    for chain in chains:
        head = chain[0]
        found_chain_end, nontrivial = False, False
        # print(row_to_str(head))
        while not found_chain_end:
            # print(head)
            unranked_prev = [r for r in get_after(head) if not has_rank(r)]
            ranked_prev = [r for r in get_after(head) if has_rank(r)]
            nontrivial |= len(unranked_prev) > 0  # turns to True only once
            prevs = unranked_prev or ranked_prev
            if prevs:
                assert len(prevs) == 1
                head = prevs[0]
                chain.append(head)
                found_chain_end = has_rank(head)
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
            return int(ch[-1]['Rank'])

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
    # chains.sort(key=lambda x: x[0]['Rank'])
    chains.sort(key=len, reverse=True)
    chains.sort(key=lambda x: int(x[-1]['Rank']) - int(x[0]['Rank']))
    for a_chain in chains:
        print(' —→ '.join(compact_row(r) for r in a_chain))
    print(len(chains), 'chains')


def no_info_count(rows):
    no_info = (r for r in rows if not r['After'] and not has_rank(r))
    return sum(1 for _ in no_info)


def process_table(gen_chains=True):
    table = parse()
    rows = table['rows']
    print('{} ranked rows'.format(sum(1 for _ in filter(has_rank, rows))))

    compute_edges_by_year(rows)
    compute_edges_by_rank(rows)
    remove_extra_afters(rows)

    set_approx_pos(rows)
    shift_rows_with_no_upper_limit(rows)
    print('{0} items have no info'.format(no_info_count(rows)))
    if gen_chains:
        process_chains(get_chains(rows))

    output(table)
    return table


if __name__ == '__main__':
    process_table()
