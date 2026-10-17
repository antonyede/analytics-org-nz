# Contact email and Eventbrite sync verification

Live preview: https://antonyede.github.io/analytics-org-nz/

Contact email and the separate newsletter passed on desktop, tablet and mobile. No email or form submission was sent.

**API sync is blocked:** EVENTBRITE_TOKEN is missing. Zero API-synced events; last success is null; 25 archived records remain. Daily 06:17 UTC and manual dispatch are installed. The real manual workflow tested this blocked state, committed safe diagnostics, retained the archive, and requested a successful Pages rebuild.

- [Workflow proof](workflow-verification.json)
- [Public source identity and supported API access](source-access.json)
- [19 local unit tests](local-unit-tests.txt)
- [Live functional checks](live-functional.json)
- [15 screenshot checks](live/results.json)

| Route | Viewport | Live screenshot |
| --- | --- | --- |
| `/contact/` | 1440 × 1000 | [capture](live/desktop-contact.png) |
| `/events/` | 1440 × 1000 | [capture](live/desktop-events.png) |
| `/events/?522c7db6_page=2` | 1440 × 1000 | [capture](live/desktop-events-page-2.png) |
| `/events/?522c7db6_page=3` | 1440 × 1000 | [capture](live/desktop-events-page-3.png) |
| `/about/` | 1440 × 1000 | [capture](live/desktop-about.png) |
| `/contact/` | 834 × 1112 | [capture](live/tablet-contact.png) |
| `/events/` | 834 × 1112 | [capture](live/tablet-events.png) |
| `/events/?522c7db6_page=2` | 834 × 1112 | [capture](live/tablet-events-page-2.png) |
| `/events/?522c7db6_page=3` | 834 × 1112 | [capture](live/tablet-events-page-3.png) |
| `/about/` | 834 × 1112 | [capture](live/tablet-about.png) |
| `/contact/` | 390 × 844 | [capture](live/mobile-contact.png) |
| `/events/` | 390 × 844 | [capture](live/mobile-events.png) |
| `/events/?522c7db6_page=2` | 390 × 844 | [capture](live/mobile-events-page-2.png) |
| `/events/?522c7db6_page=3` | 390 × 844 | [capture](live/mobile-events-page-3.png) |
| `/about/` | 390 × 844 | [capture](live/mobile-about.png) |
