#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import sys
import os

from lxml import html
import requests


HOST = 'https://www.poemhunter.com'
DEFAULT_CONCURRENCY = 30


class PoemHunter(object):
    def __init__(self, poet, dest, concurrency, verbose=False):
        """Initializes the instance.

        poet -- A string of the full name of the poet.
        dest -- A valid path at which to save the poems.
        concurrency -- An integer specifying how many threads should be used.
        verbose -- Print progress and erorr reports if True.
        """
        if not poet:
            raise TypeError('poet is a required argument')
        if not dest:
            raise TypeError('dest is a required argument')
        self.poet = poet
        self.dest = dest
        self.downloaded_poems = []
        self._executor = ThreadPoolExecutor(concurrency)
        self._verbose = verbose

        if self.poet.lower() not in self.dest.lower():
            self.dest += '/' + self.poet
            if not os.path.exists(self.dest):
                os.makedirs(self.dest)

    def run(self):
        """Conccurently fetches and saves all poems of poet."""
        # Format poet name as used in the URL.
        poem_url_base = HOST + '/' + self.poet.lower().replace(' ', '-') + '/poems/'
        futures = {}
        page_no = 1
        while True:
            # nth page URL format:
            # https://www.poemhunter.com/poet-name/poems/page-n
            try:
                page = requests.get(poem_url_base + f'page-{page_no}')
            except IOError:
                if self._verbose:
                    print('Error loading page')
                break
            if not page.content:
                break

            dom = html.fromstring(page.content)

            poem_titles = dom.xpath('//*[@class="poems"]/tbody/tr/td[2]/a')
            for title in poem_titles:
                future = self._executor.submit(
                        self.download_poem,
                        title.text,
                        HOST + title.attrib['href'])
                futures[future] = title.text

            next_page = dom.xpath('//*[@class="next"]/a')
            if not next_page:
                break
            page_no += 1

        for future in as_completed(futures.keys()):
            if future.result():
                title = futures[future]
                if self._verbose:
                    print(f'{self.poet} - {title} saved.')

    def download_poem(self, title, url):
        """Fetches poem from poemhunter.com and saves it.

        title -- title of the poem
        url -- full URL of the poem
        """
        if title in self.downloaded_poems:
            return False

        try:
            poem = self._fetch_poem(url)
        except IOError as exc:
            if self._verbose:
                print(f'Could not download {self.poet} - {title}:', exc)
            return False

        try:
            self._save_poem(title, self._format_poem(title, poem))
        except IOError as exc:
            # For now (TODO).
            if self._verbose:
                print(f'Could not save {self.poet} - {title}:', exc)
            return False

        self.downloaded_poems.append(title)
        return True

    def _fetch_poem(self, url):
        """Downloads and returns each line of the poem as a list of strings."""
        # URL format: https://www.poemhunter.com/poem/poem-title/
        page = requests.get(url)
        if page.content:
            dom = html.fromstring(page.content)

            lines = []
            p = dom.xpath(
                    '/html/body/div[1]/div[6]/div[3]/div/div[1]/div[2]/div[1]/p')
            if p:
                lines.append(p[0].text)
                brs = p[0].xpath('br')
                for br in brs:
                    if br.tail:
                        lines.append(br.tail)
                    else:
                        lines.append('')
            return lines
        else:
            return ""

    def _format_poem(self, title, lines):
        """Removes artifacts and appends title and author to the poem."""
        if lines:
            # For some reason there are a \r\n chars at the beginning of the
            # first line and in the last line and at the end of the second last
            # line line, so trim these.
            lines[0] = lines[0].lstrip()
            lines[-1] = lines[-1].strip()
            if not lines[-1]:
                del lines[-1]
                if lines:
                    lines[-1] = lines[-1].strip()

            # Insert header (title), footer (poet) and blanks in between.
            lines.insert(0, title)
            lines.insert(1, '')
            lines.insert(1, '')
            lines.append('')
            lines.append('')
            lines.append(self.poet)
        return lines

    def _save_poem(self, title, poem):
        """Writes poem to a file."""
        with open(self.dest + '/' + title, 'w') as f:
            for line in poem:
                f.write(line + '\n')


def parse_top_poets(args):
    # TODO determine the optimal number of threads, because this means
    # n * args.concurrency, which might be way too much.
    # That aside, the whole architecture is probably not great--maybe extend the
    # PoemHunter class to take a list of poets so that only a single executor
    # instance is employed?
    # Or use Twisted or python3 async IO.
    executor = ThreadPoolExecutor(min(args.number, 10))
    futures = {}
    url_base = HOST + f'/p/t/l.asp?l=Top500'
    page_no = 1
    n_poets = 0
    while True:
        page = requests.get(url_base + f'&p={page_no}')
        if not page.content:
            break

        dom = html.fromstring(page.content)
        poets = dom.xpath('/html/body/div/div[6]/div[2]/div/div/ol/li/a[2]')
        for poet in poets:
            if poet is None:
                continue
            future = executor.submit(
                    parse_poet,
                    poet.text, args.dest,
                    args.concurrency, args.verbose)
            futures[future] = poet
            n_poets += 1
            if n_poets == args.number:
                return

        next_page = dom.xpath('//*[@class="next"]/a')
        if not next_page:
            break
        page_no += 1
        
    for future in as_completed(futures):
        poet = futures[future]
        if args.verbose:
            print(f'All poems downloaded for {poet}')
        

def parse_poet(poet, dest, concurrency, verbose):
    poem_hunter = PoemHunter(
            poet=poet, dest=dest,
            concurrency=args.concurrency, verbose=verbose)
    poem_hunter.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description='Scrapes poems from poemhunter.com.')

    sp = parser.add_subparsers(title='subcommands')

    # Args for parsing the top N poets.
    sp_top = sp.add_parser(name='top',
            help='download all poems of the top poets',
            description='Download poems of the top poets from poemhunter.com')
    sp_top.add_argument(
            'number', metavar='N', default=100, type=int,
            help='the number of poets\' works to download')
    sp_top.set_defaults(func=parse_top_poets)

    # Args for parsing a single poet.
    sp_poet = sp.add_parser(name='poet',
            help='download all poems of a single poet',
            description='Download poems of a poet from poemhunter.com')
    sp_poet.add_argument(
            'poet', metavar='POET', type=str,
            help='the poet whose poems to download')
    sp_poet.set_defaults(
            func=lambda args:
                parse_poet(args.poet, args.dest, args.concurrency, args.verbose))

    parser.add_argument(
            'dest', metavar='DEST', type=str,
            help='the directory in which to save the poems')
    parser.add_argument(
            '-c', '--concurrency',
            metavar='N', default=DEFAULT_CONCURRENCY, type=int,
            help='the number of threads to use for parallel downloads')
    parser.add_argument(
            '-v', '--verbose', action='store_true',
            help='enables progress and error reporting')

    args = parser.parse_args()
    if not os.path.exists(args.dest):
        print(f'"{args.dest}" is not a valid path.')
        sys.exit(-1)
    args.func(args)
