# Weekly visual run (Sunday)

Purpose: attach a branded 1080 x 1350 image to each Vitelize Health Facebook post scheduled in Metricool for the coming Monday to Sunday.

## Steps

1. Clone this repository (gurjohal-sudo/vitelize-social-assets). Install the renderer once per run: `pip install --break-system-packages playwright && python3 -m playwright install chromium`.
2. Read the Metricool brand settings (brand "Vitelize Health", blogId 7525739, timezone America/Vancouver). Get the scheduled posts from Monday 00:00 to Sunday 23:59 of the coming week.
3. Skip any post that already has media. For each remaining post, write one spec object in `specs/<monday-date>.json` (format documented at the top of `tools/render.py`). Rules:
   * `id` is the post date, `YYYY-MM-DD`.
   * `program`: "peptide" if the post is about the Peptide Program only, "glp1" if about GLP-1 plus Training only, otherwise "both".
   * Headline: 6 to 14 words, taken from or closely paraphrasing the post's own opening. Wrap the second half in `[[ ]]` for the orange accent.
   * Body: at most 2 short sentences, drawn only from the post text. Optional.
   * Use `tiles` (up to 4, max 3 words each) when the post lists benefits, steps or options; use `stat` only when the post itself cites a statistic, copying the figure and source exactly.
   * Never add claims, numbers, drug brand names, compound names, prices, revenue-share percentages, or competitor names that are not in the post. No em or en dashes.
4. Render: `python3 tools/render.py specs/<monday-date>.json posts`. Any line printing OVERFLOW must be shortened and re-rendered. View every image before publishing it.
5. Commit and push `posts/` and `specs/` to `main`. Confirm each image returns HTTP 200 at `https://raw.githubusercontent.com/gurjohal-sudo/vitelize-social-assets/main/posts/<id>.png`.
6. For each post, call Metricool updateScheduledPost with the post's full original content unchanged, adding the image URL to `media` and a one-sentence description to `mediaAltText`. Never change text, date, time or autoPublish.
7. Send Gur a short summary: dates covered, headline used for each image, anything skipped or failed.
