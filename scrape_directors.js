// Run the script from http://www.theyshootpictures.com/directors.htm
{
    'use strict';

    // Some pages have mismatching "Acclaimed Films" links
    const urlErrorsMap = {
        'kieslowskikrszystof.htm': 'kieslowskikrzysztof.php',
        'clouzothg.htm': 'clouzothenrigeorges.php',
        'sturgesjohn.htm': 'page/sturgesjohn.php',
    };

    const getFilmographyUrl = url => urlErrorsMap.hasOwnProperty(url) ?
        urlErrorsMap[url] :
        url.replace('htm', 'php');

    const parseDirector = html => {
        const [, name] = html.title.match(/TSPDT\s*-\s*(.+)'s Acclaimed/);
        if (!name) {
            throw new Error(`Can't parse director's name. Got html.title "${html.title}"`);
        }

        const movies = [...html.querySelectorAll('.csv_row')].map(el => ({
            pos: parseInt(el.querySelector('.csv_column_6').textContent, 10),
            year: parseInt(el.querySelector('.csv_column_2').textContent, 10),
            title: el.querySelector('.csv_column_3').textContent.trim(),
            name
        })).sort(sortByPos);
        if (!movies.length) {
            throw new Error(`Extracted 0 movies of ${name}`);
        }

        console.log(`Parsed ${name}, got ${movies.length} movies.`);
        return movies;
    };

    const sortByPos = (a, b) => {
        if (!a.pos && !b.pos) {
            return a.year - b.year;
        } else if (!a.pos) {
            return 1; // b before a
        } else if (!b.pos) {
            return -1; // a before b
        } else {
            return a.pos - b.pos;
        }
    };

    const output = arr => 'Pos\tYear\tTitle\tDirector \n' + arr
        .filter(el => el.pos > 1000 && el.pos <= 2000)
        .map(el => Object.values(el).join('\t'))
        .join('\n');

    const parseHTML = s => new DOMParser().parseFromString(s, 'text/html');
    const loadMovies = async url => {
        const r = await fetch(url);
        if (!r.ok) {
            throw new Error(`Bad response for ${url}`);
        }

        const html = parseHTML(await r.text());
        return parseDirector(html);
    };

    const loadAll = async urls => {
        const movies = [];
        for (let url of urls) {
            movies.push(...await loadMovies(url));
        };
        movies.sort(sortByPos);
        console.log(output(movies));
    };

    // Same but fully async (won't stop the rest of requests after error)
    const loadAllParallel = urls => Promise.all(urls.map(loadMovies))
        .then(arr => [].concat(...arr).sort(sortByPos))
        .then(arr => console.log(output(arr)));

    const urls = [...document.querySelectorAll('.jwresp_wrapper a')]
        .map(el => getFilmographyUrl(el.getAttribute('href')));

    loadAllParallel(urls);
    // console.log(output(parseDirector(document))); // use on director pages
}
