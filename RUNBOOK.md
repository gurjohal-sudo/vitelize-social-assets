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
   * Partner benefit emphasis: when a post mentions both the partner's new revenue and the co-branded page, lead the headline or tiles with the revenue (for example "A new revenue stream for your gym"), not the branded page. Never state a percentage, amount or guarantee.
   * Compound names may appear on an image only when the post itself lists them (the formulary and exclusion posts). Never pair a compound with a benefit, result or dose.
4. Render: `python3 tools/render.py specs/<monday-date>.json posts`. The renderer (v2) puts a real photograph from `tools/photos/` on every image and rotates four layouts (fullbleed, splittop, framed, splitside) and four brand themes (light, grey, ink, teal) by date, so leave `layout`, `theme`, `band` and `photo` out of the spec unless an image needs a specific choice. It logs each photo in `tools/photos/used.json` to avoid repeats; commit that file too. Any line printing OVERFLOW must be shortened and re-rendered. View every image before publishing it.
   * Photo rules: only photos from `tools/photos/photos.json` (Unsplash License, sources listed there). Posts about medication, peptides, GLP-1s or patients never use a photo of an identifiable member or patient; the renderer enforces this. To add photos, download from Unsplash free-license images, add an entry to `photos.json` with tag, face, photographer and source, and view it first.
5. Commit and push `posts/` and `specs/` to `main`. Confirm each image returns HTTP 200 at `https://raw.githubusercontent.com/gurjohal-sudo/vitelize-social-assets/main/posts/<id>.png`.
6. For each post, call Metricool updateScheduledPost with the post's full original content unchanged, adding the image URL to `media` and a one-sentence description to `mediaAltText`. Never change text, date, time or autoPublish.
7. Send Gur a short summary: dates covered, headline used for each image, anything skipped or failed.

## Reels (two per week)

1. From the week's posts, pick the two with the strongest hooks or lists for Reels (prefer one Peptide Program post and, from November 11 onward, one GLP-1 plus Training post). Skip any post that is already a Reel. All other posts get images as above.
2. Extra install: `pip install --break-system-packages soundfile numpy`. No voice model is needed.
3. Write `reel_specs/<post-date>.json` in the format at the top of `tools/render_reel.py`, following `reel_specs/2026-10-26.json` as the approved model:
   * `"music": true`, `"music_style": "drive"` (the high-energy 128 BPM bed in `tools/audio.py`).
   * No voiceover of any kind: never add `intro_vo` or a scene `vo`.
   * Scenes: hook, one or two lists, a closing hook, then cta. Use only the post's own words. 18 to 25 seconds total.
4. Render: `python3 tools/render_reel.py reel_specs/<post-date>.json reels`. Check sample frames (ffmpeg) before publishing.
5. Push `reels/<date>.mp4` and `reels/<date>_cover.jpg` (when replacing a Reel already attached in Metricool, use a new file name such as `<date>_v2.mp4`, because Metricool keeps its own copy), confirm both return HTTP 200 on raw.githubusercontent.com.
6. In Metricool, update the post with its full original text unchanged, `media` = the mp4 raw URL, `videoThumbnailUrl` = the cover raw URL, `mediaAltText` = [], and `facebookData` = {"type": "REEL"}.
