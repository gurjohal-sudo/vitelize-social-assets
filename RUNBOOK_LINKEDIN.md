# LinkedIn carousel build

1. `pip install --break-system-packages playwright && python3 -m playwright install chromium`
2. Write `linkedin/<date>_<slug>.json`: a list of 8 to 12 slides. Types: cover, point, person, bullets, recap, cta. Model: `linkedin/2026-10-30_glp1-muscle.json`. Wrap the accent phrase in [[ ]].
   * person photos: tools/people/team-gray.jpg, team-craig.jpg (team-cerf.jpg only with Gur's approval).
   * cover photo: any file in tools/photos/photos.json (no identifiable patient for medication topics).
3. `python3 tools/li_carousel.py . /tmp/out.html linkedin/<date>_<slug>.json`
4. Print to PDF with Playwright: page.goto(file), page.pdf(width='1080px', height='1350px', print_background=True, prefer_css_page_size=True).
5. Check every page (pdftoppm -r 30, contact sheet) for overflow before sending.
6. Commit the spec and PDF under linkedin/.
