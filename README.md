# Pascal AI Labs: Events

Static build of the Pascal events pages (preview: https://pascal-events-preview.vercel.app).

- `public/events/` – the events listing page (`/events`)
- `public/events/hong-kong-2026/` – "From Front to Back Office" roundtable dinner, Hong Kong, 27 Oct 2026
- `public/assets/pages/events.css`, `events.js` – page styles and the "Request an invitation" form
- `public/assets/photos/` – Hong Kong hero photo (CC0, see CREDITS.txt) and speaker headshots
- `public/assets/logos/bare-cove-technology.svg` – co-host logo

Integration notes
- Only add **News > Events** to the site navigation; leave the rest of the live nav and footer unchanged.
- The form posts JSON to `/api/mail` with `formType: "event_invite_request"` (fields: event, eventName, eventCity, eventDate, pageUrl, name, email, organization, jobTitle, countryCode, countryName, phoneNumber, topics, recaptchaToken). The mail route needs to handle this form type.
- `src/` holds the generator (`events.py`) used to produce the pages, plus the CSS/JS sources.

## Event recaps (added 26 Nov 2026)

The `/events` page now lists recaps of past events in two sections, invite-only roundtables and conferences, with one page per event under `/events/<slug>`.

Preview: https://pascal-event-recaps-preview.vercel.app/events

New files:
- `public/events/<slug>/index.html`: 11 recap pages. Each has its own meta, canonical, OG/Twitter tags and JSON-LD (BlogPosting, Event, FAQPage, BreadcrumbList), plus a visible FAQ.
- `public/events/index.html`: the updated events page (recap cards, FAQ, CollectionPage/ItemList schema).
- `public/assets/pages/recaps.css`: recap and card styles. Load it after `site.css` and `events.css`.
- `public/assets/photos/recaps/`: optimised photos. Credits for the Wikimedia Commons images are shown on the pages.
- `public/sitemap-events.xml`: add these URLs to the main sitemap.
- `public/llms-events.txt`: add these lines to the main llms.txt.
- `src/recaps/`: the generator (`content.py` copy, `build.py`, `recaps.css`), for reference.

Integration notes:
- Copy `public/events/` and `public/assets/{pages/recaps.css,photos/recaps/}`. Leave the live nav, footer, robots.txt and sitemap.xml as they are.
- Product links inside the recaps are absolute (`https://pascalailabs.com/...`) and point to live pages.
- `/events/hong-kong-2026` (the pre-event invite page) is no longer linked from `/events`. Please add a 301 redirect from it to `/events/bare-cove-roundtable-dinner-hong-kong-2026`.
