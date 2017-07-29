from collections import Counter

import sort as s


def create_between_col(table):
    table['header'].append('Between')  # a tuple of a range of possible ranks (incl. both ends)
    rows = table['rows']
    # extract upper bounds for rows that are in 'After' of ranked rows
    ranked = (r for r in rows if s.has_rank(r))
    unranked_before_ranked = ((ant, r) for r in ranked for ant in s.get_after(r) if
                              not s.has_rank(ant))
    for (ant, r) in unranked_before_ranked:
        if ('BeforeRank' not in ant) or ant['BeforeRank'] > r['Rank']:
            ant['BeforeRank'] = r['Rank']
    # extract lower bounds
    unranked = (r for r in rows if not s.has_rank(r))
    ranked_before_unranked = ((ant, r) for r in unranked for ant in s.get_after(r) if
                              s.has_rank(ant))
    for (ant, r) in ranked_before_unranked:
        if ('AfterRank' not in r) or r['AfterRank'] < ant['Rank']:
            r['AfterRank'] = ant['Rank']
    # fill 'Between' column
    for r in rows:
        if 'BeforeRank' in r and 'AfterRank' in r:
            r['Between'] = (int(r['AfterRank']) + 1, int(r['BeforeRank']) - 1)
            # print('between:', '@' + r['AfterRank'], '—→', '#' + r['Hash'], '—→', '@' + r['BeforeRank'])
        elif 'BeforeRank' in r:
            r['Between'] = (1001, int(r['BeforeRank']) - 1)
            # print(' before: #{0:4} —→ @{1:4}'.format(r['Hash'], r['BeforeRank']))
        elif 'AfterRank' in r:
            r['Between'] = (int(r['AfterRank']) + 1, 2000)
            # print('  after: @{0:4} —→ #{1:4}'.format(r['AfterRank'], r['Hash']))


def occupied_ranks(rows):
    return sorted(int(r['Rank']) for r in rows if s.has_rank(r))


def available_ranks_fct(rows):
    occ = set(occupied_ranks(rows))

    def available_ranks(range_incl):
        return set(range(range_incl[0], range_incl[1] + 1)) - occ

    return available_ranks


def brute(rows):
    available_ranks = available_ranks_fct(rows)
    unranked = [r for r in rows if not s.has_rank(r)]
    unranked_lim = [r for r in unranked if 'Between' in r]
    unlim_count = len(unranked) - len(unranked_lim)
    print(len(unranked_lim), 'rows have a limited range of possible ranks')
    print(unlim_count, 'rows have no explicit rank limit')
    easiest_rows = ((available_ranks(r['Between']), r) for r in unranked_lim)
    easiest_rows = sorted(easiest_rows, key=lambda x: len(x[0]))
    # print(ft.reduce(lambda x, y: x * y, (len(x[0]) for x in easiest_rows)))
    # for l in [x[0] for x in easiest_rows][:10]:
    # print(sorted(l))
    print('Candidates:', sum((Counter(x[0]) for x in easiest_rows), Counter()))


def main():
    table = s.process_table(gen_chains=False)
    rows = table['rows']
    create_between_col(table)
    brute(rows)
    s.output(table)


if __name__ == '__main__':
    main()
