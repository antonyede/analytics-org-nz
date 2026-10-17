# Eventbrite HTTP 400 fix and successful live sync

The existing token was reused. The failing discovery request rejected `page_size=50`; the helper now sends that parameter only to the documented event-list endpoint. Organisation discovery uses `page` alone. No organisation-ID variable was needed.

**Successful sync: 23 public listed events, 0 upcoming / 23 past, 19 hosted images, 2026-10-17 03:55:13 UTC.** Four events supplied no image; none was invented.

- [Successful authenticated workflow](https://github.com/antonyede/analytics-org-nz/actions/runs/39000586274)
- [Successful Pages deployment](https://github.com/antonyede/analytics-org-nz/actions/runs/39000619137)
- [Safe diagnosis and verification record](verification.json)
- [20 passing unit tests](unit-tests.txt)
- [Live functional tests](functional.json)
- [All 23 ticket links and 19 image hashes](resources.json)
- [Responsive content/date/image checks](results.json)

Every rendered event link, UTC timestamp and image path was checked against the validated API dataset on desktop 1440 × 1000, tablet 834 × 1112 and mobile 390 × 844. All available images loaded; no horizontal overflow or JavaScript error was observed. No emails, forms, subscriptions or bookings were sent. The contact email, separate newsletter and TRA/Antony removals remain verified.

| Route | Viewport | Live screenshot |
| --- | --- | --- |
| `/contact/` | 1440 × 1000 | [capture](desktop-contact.png) |
| `/events/` | 1440 × 1000 | [capture](desktop-events.png) |
| `/events/?522c7db6_page=2` | 1440 × 1000 | [capture](desktop-events-page-2.png) |
| `/events/?522c7db6_page=3` | 1440 × 1000 | [capture](desktop-events-page-3.png) |
| `/about/` | 1440 × 1000 | [capture](desktop-about.png) |
| `/contact/` | 834 × 1112 | [capture](tablet-contact.png) |
| `/events/` | 834 × 1112 | [capture](tablet-events.png) |
| `/events/?522c7db6_page=2` | 834 × 1112 | [capture](tablet-events-page-2.png) |
| `/events/?522c7db6_page=3` | 834 × 1112 | [capture](tablet-events-page-3.png) |
| `/about/` | 834 × 1112 | [capture](tablet-about.png) |
| `/contact/` | 390 × 844 | [capture](mobile-contact.png) |
| `/events/` | 390 × 844 | [capture](mobile-events.png) |
| `/events/?522c7db6_page=2` | 390 × 844 | [capture](mobile-events-page-2.png) |
| `/events/?522c7db6_page=3` | 390 × 844 | [capture](mobile-events-page-3.png) |
| `/about/` | 390 × 844 | [capture](mobile-about.png) |
