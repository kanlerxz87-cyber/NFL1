# data/depth_raw — raw official depth-chart text, retained per capture

Each file here is the **verbatim text** that the fetch tool returned for an official club
depth-chart page, saved unchanged so the parser can be re-run and audited against exactly
what the club published. A sidecar `.meta.json` records the URL, the fetch clock time (UTC),
the sha256 of the raw file, and the club's own publication date if the page prints one.

Why raw text is kept
--------------------
The brief requires that a parsing failure be fixed against the source rather than worked
around, and that every published cell be traceable to what the club actually printed. A
parser run over a transcript that has already been tidied cannot demonstrate either.

What is deliberately **not** here
---------------------------------
* No HTML. The fetch tool returns rendered text, so the raw bytes of the page cannot be
  recovered from it. That limit is recorded as `capture_method` in every sidecar and is
  flagged on the site rather than papered over.
* No hand transcription. Where a club publishes its chart only as an image, the image is
  recorded as an unrecoverable gap (with the image URL) and **no rows are produced**. The
  brief forbids transcribing by eye, and inventing rows from a picture is exactly that.
