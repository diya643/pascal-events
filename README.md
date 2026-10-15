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
