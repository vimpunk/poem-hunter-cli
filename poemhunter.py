#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import sys
import os

from lxml import html
import requests


HOST = 'https://www.poemhunter.com'


def fetch_poem(url):
    """
    Downloads and returns each line of the poem as a separate string
    in a list.
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


def save_poem(title, poem, path):
    with open(path + '/' + title, 'w') as f:
        for line in poem:
            f.write(line + '\n')


def format_poem(poet, title, lines):
    if lines:
        # For some reason there are a \r\n chars at the beginning of the first
        # line and in the last line and at the end of the second last line line,
        # so trim these.
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
        lines.append(poet)
    return lines


def download_poem(poet, title, url, dest):
    """
    Fetches poem from poemhunter.com and saves it.

    poet -- The full name of the poet.
    title -- title of the poem
    url -- full URL of the poem
    dest -- valid path to the directory where the poem is to be saved
    """

    poem = fetch_poem(url)
    poem = format_poem(poet, title, poem)
    save_poem(title, poem, dest)
    # Signal that this poem was accepted and saved. This may change in the
    # future in that a poem might not be saved.
    return True


def run(poet, dest, concurrency):
    """
    Conccurently fetches and saves all poems of poet.
    
    poet -- A string of the full name of the poet.
    dest -- A valid path at which to save the poems.
    concurrency -- An integer specifying how many threads should be used.
    """

    if poet.lower() not in dest.lower():
        dest += '/' + poet
        if not os.path.exists(dest):
            os.makedirs(dest)

    # Format poet name as used in the URL.
    poem_url_base = HOST + '/' + poet.lower().replace(' ', '-') + '/poems/'

    executor = ThreadPoolExecutor(concurrency)
    futures = {}

    page_no = 1
    while True:
        # nth page URL format: https://www.poemhunter.com/poet-name/poems/page-n
        try:
            page = requests.get(poem_url_base + f'page-{page_no}')
        except IOError:
            print('Error loading page');
            break;
        if not page.content:
            break

        dom = html.fromstring(page.content)

        poem_titles = dom.xpath('//*[@class="poems"]/tbody/tr/td[2]/a')
        for title in poem_titles:
            future = executor.submit(
                    download_poem,
                    poet,
                    title.text,
                    HOST + title.attrib['href'],
                    dest)
            futures[future] = title.text

        next_page = dom.xpath('//*[@class="next"]/a')
        if not next_page:
            break
        page_no += 1

    for future in as_completed(futures.keys()):
        title = futures[future]
        if future.result():
            print(f'"{title}" saved.')


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

    run(args.poet, args.dest, args.concurrency)
