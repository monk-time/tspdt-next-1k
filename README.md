# tspdt-next-1k
A failed (so far) attempt to figure out the order of the second thousand of movies from the [They Shoot Pictures, Don't They?](http://www.theyshootpictures.com/gf1000.htm) (TSPDT) project by collating ~500 known positions with partial orderings of movies made in the same year.

The assumption was that there's more than enough data to figure out at least some new exact ranks, which in turn should snowball into even more revealed ranks until the full order is restored. But it turned out that so far it's not enough to find even a single one.

Data sources:
* [`data/Films-Ranked-1001-2000.tsv`](data/Films-Ranked-1001-2000.tsv) — [the full list of the movies ranked 1001-2000](http://www.theyshootpictures.com/resources/Films-Ranked-1001-2000.xls)
* [`data/Yearly-Top-25s-GF1000.tsv`](data/Yearly-Top-25s-GF1000.tsv) — [yearly top-25s from TSPDT](http://www.theyshootpictures.com/resources/Yearly-Top-25s-GF1000.xlsx)
* [`data/directors_scraped.tsv`](data/directors_scraped.tsv) — [individual director filmographies with exact ranks for the movies in question](http://www.theyshootpictures.com/directors.htm)

## How to use this tool
1. Load two Excel tables from the links above and convert them to .tsv as described in [`parse.py`](parse.py).
2. Use `scrape_directors.js` in the browser console to get the third data source, save the output to `data/directors_scraped.tsv`.
3. Run `parse.py` to collate data sources to a single file.
4. Run `sort.py` to find unranked candidates with the fewest possible ranks.

If you want to skip straight to the result, here's [a sample output](https://gist.github.com/monk-time/951a74705ac581b07d3e31b76a1cf1db), make sure to scroll to the 'Range' column.
