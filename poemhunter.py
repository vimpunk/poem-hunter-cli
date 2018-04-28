#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import sys
import os

from lxml import html
import requests


HOST = 'https://www.poemhunter.com'


class PoemHunter(object):
    def __init__(self, poet, dest, concurrency):
        self.poet = poet
        self.dest = dest
        self.downloaded_poems = []
        self._executor = ThreadPoolExecutor(concurrency)

        if self.poet.lower() not in self.dest.lower():
            self.dest += '/' + self.poet
            if not os.path.exists(self.dest):
                os.makedirs(self.dest)

    def run(self):
        """Conccurently fetches and saves all poems of poet.

        poet -- A string of the full name of the poet.
        dest -- A valid path at which to save the poems.
        concurrency -- An integer specifying how many threads should be used.
        """

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
                print(f'"{title}" saved.')

    def download_poem(self, title, url):
        """Fetches poem from poemhunter.com and saves it.

        poet -- The full name of the poet.
        title -- title of the poem
        url -- full URL of the poem
        dest -- valid path to the directory where the poem is to be saved
        """

        if title in self.downloaded_poems:
            return False

        try:
            poem = self._fetch_poem(url)
        except IOError as exc:
            print(f'Could not download "{title}":', exc)
            return False

        try:
            self._save_poem(title, self._format_poem(title, poem))
        except IOError as exc:
            # For now (TODO).
            print(f'Could not save "{title}":', exc)
            return False

        self.downloaded_poems.append(title)
        return True

    def _fetch_poem(self, url):
        """Downloads and returns each line of the poem as a separate string in
        a list.
        """

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            description="Scrape poems from poemhunter.com")
    parser.add_argument(
            'poet', metavar='POET', type=str,
            help='the poet whose poems to download')
    parser.add_argument(
            'dest', metavar='DEST', type=str,
            help='the directory in which to save the poems')
    parser.add_argument(
            '-c', '--concurrency', metavar='N', default=30, type=int,
            help='the number of threads to use for parallel downloads')

    args = parser.parse_args()
    if not os.path.exists(args.dest):
        print(f'"{args.dest}" is not a valid path.')
        sys.exit(-1)

    poem_hunter = PoemHunter(args.poet, args.dest, args.concurrency)
    poem_hunter.run()
