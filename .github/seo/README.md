# Search visibility, generated from one file

Everything a search engine sees about this repository comes from
[`.github/repository-metadata.yml`](../repository-metadata.yml). Change a fact there
and CI regenerates — or fails, if the tree disagrees.

```
.github/repository-metadata.yml   the source of truth
.github/seo/seo.py                validate · build · check · verify · sync-metadata · indexnow
docs/                             the published site, mostly generated
```

## What is generated and what is not

`seo.py` only rewrites the regions between `seo:*:begin` and `seo:*:end` markers, and
refuses to run if a marker is missing rather than guessing where generated content
belongs. Hand-written prose is never touched.

| File | Generated |
| --- | --- |
| `docs/index.html` | the `<head>` metadata block and the project-resources block |
| `README.md` | one facts block under the badges |
| `docs/robots.txt` | entirely |
| `docs/sitemap.xml` | entirely |
| `docs/<indexnow-key>.txt` | entirely |
| `docs/assets/social-preview.png` | rendered from `social-preview.svg`, see below |

## Commands

```bash
python .github/seo/seo.py validate    # the manifest is well-formed and truthful
python .github/seo/seo.py build       # regenerate the generated regions
python .github/seo/seo.py check       # exit 1 if anything would change (CI gate)
python .github/seo/seo.py verify      # quality gates over the built site
python .github/seo/seo.py sync-metadata [--apply]
python .github/seo/seo.py indexnow --all [--dry-run]
```

Standard library only, Python 3.9+. No dependency is added to the tree to run this.

### What `validate` actually checks

Not just shape. It checks claims: that `canonical_url` really is this repository's
Pages URL, that topic count and format meet GitHub's rules and describe the software
rather than praise it, that `runnable_scripts` equals the number of CLIs actually in
`scripts/`, that every declared network surface names a file that exists, and that
`content_updated` is a real date that is not in the future.

`verify` goes further and checks the built output: exactly one non-duplicate `<title>`
per page, a distinct meta description, a self-referencing `rel="canonical"` that
`og:url` agrees with, an `og:image` that exists and is exactly 1280×640, JSON-LD that
parses, a sitemap whose URLs match the manifest, internal repository links that
resolve to real files, and — when `network_surfaces` is `[]` — that no script in
`scripts/` is quietly making network calls.

## Regenerating the social preview

`docs/assets/social-preview.svg` is the editable source. Render it at exactly the
1280×640 GitHub asks for:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --window-size=1280,640 \
  --screenshot=docs/assets/social-preview.png \
  docs/assets/social-preview.svg
```

The PNG is the Open Graph image automatically. Setting it as the *repository* social
preview is a manual step — GitHub exposes no API for it: **Settings → General → Social
preview → Upload an image**.

## One-time setup a human has to do

Three things cannot be automated, because they require credentials or ownership proof
that only the account holder can obtain.

**1. Google Search Console.** Verify the Pages URL as a URL-prefix property, download
the `google<token>.html` file, and commit it to `docs/`. Committing it (rather than
uploading it once) is the point: a deploy replaces the whole site, so an uncommitted
verification file disappears on the next push and the property silently unverifies.
Then submit the sitemap once — after setup, or after the sitemap's structure changes.
Not on every edit; resubmitting does not make crawling happen faster.

**2. Bing Webmaster Tools.** Either import the Search Console property or verify
separately, then commit `docs/BingSiteAuth.xml` for the same reason.

**3. IndexNow.** Already set up — the key lives in the manifest and `seo.py build`
writes `docs/<key>.txt`, which is the public proof of ownership the protocol requires.
Nothing to do.

`seo.py verify` warns until the first two files are present, so the gap stays visible.

## What this pipeline does not claim

- **No automation can guarantee indexing.** Google states there is no guarantee that
  any particular site will be added to its index.
- **A sitemap is a discovery signal, not an instruction.** Submitted URLs may not be
  crawled.
- **IndexNow does not reach Google.** It covers Bing, Naver, Yandex, Seznam, Yep and
  other participants. Google is not among them.
- **Google's Indexing API is not applicable here.** It is restricted to pages with
  `JobPosting` or a livestream `BroadcastEvent`, which these pages are not. Using it
  for ordinary pages is off-label, and this pipeline does not.
- **A 200 response means the notification was received**, not that a page was indexed.
- **Structured data does not guarantee a rich result.** It makes the page easier to
  interpret; search engines still decide what to show.

Track impressions, indexed-page coverage, queries, click-through rate and crawl errors
monthly. Submission count is not a success metric.

## Security notes

- Workflow permissions default to `contents: read`; only the deploy job gets
  `pages: write` and `id-token: write`.
- Every third-party action is pinned to a full-length commit SHA.
- The IndexNow key file is public by protocol design and authorises nothing else.
  Any real credential belongs in Actions secrets.
- `sync-metadata --apply` needs repository administration rights, which
  `GITHUB_TOKEN` cannot be granted. It is deliberately a human-run command.
