# Poem Hunter Command Line Interface

A little script to scrape poems from https://poemhunter.com.


I found that when I discovered a poem by an author I like I usually want to view the rest of their work, but navigating
the webpage was a slightly cumbersome experience. Thus, I wanted to be able to download their collection so I could
explore it via my preferred methods (cli + vim).


It tries to be fast by sending requests on multiple threads, but this is a small script, so it could probably be done
a lot better if more effort were to be put into it.


As far as I could tell, there is no official API, so if you use this, please don't abuse it. It was made for the
occasional personal use.

## Usage
To get help:
```bash
./poemhunter.py -h
./poemhunter.py top -h
./poemhunter.py poet -h

```
To download all works of a single artist:
```bash
./poemhunter.py poet 'John Keats' /path/to/poems/folder
```
To download all works of the top 100 artists on pomehunter.com:
```bash
./poemhunter.py top 100 /path/to/poems/folder
```
