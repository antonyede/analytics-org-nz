# Production-readiness audit — 17 October 2026

**The preview is deployed, but it is not ready for a production domain cutover.** Contact delivery is disabled. Mailchimp is configured to use the original service, but no signup, list acceptance, confirmation email, or delivery has been verified. Its existing browser-validation gap also remains. No real contact or subscription request was sent during this audit.

Live preview: <https://antonyede.github.io/analytics-org-nz/>

## Requested changes are live

The TRA sponsor label, logo and external sponsor link have been removed from every rendered footer and the builder. The empty layout wrapper remains so privacy/social links retain their placement. Antony Ede's complete About card, including his portrait, role, company and LinkedIn link, has been removed from the generated About page and builder. The remaining nine profiles are unchanged and reflow in the existing responsive grid.

These changes were published in [785702d](https://github.com/antonyede/analytics-org-nz/commit/785702d91f2f0558225c6e14ad0be6eea277d5e3) and [2cf17cd](https://github.com/antonyede/analytics-org-nz/commit/2cf17cd4337b910439fb06c91290653b16b0e900). Their Pages builds [38988332822](https://github.com/antonyede/analytics-org-nz/actions/runs/38988332822) and [38988368831](https://github.com/antonyede/analytics-org-nz/actions/runs/38988368831) succeeded. Live HTML, rather than only local output, was checked for both removals. Archived source captures retain the original site for provenance; they are not the deployed About page.

## Every form and what it actually does

There are **four form elements, three visible**, across the five live pages. Events, About and Privacy policy have no forms.

| Page / form | Visible? | Browser behaviour verified | Actual delivery |
| --- | --- | --- | --- |
| Contact — `#email-form` | Yes | Full Name is required. A nonempty malformed email fails native email validity, but email and message are not marked required. The form uses a non-submitting method and a local handler that shows the unavailable message and `help@analytics.org.nz`. The no-JavaScript fallback also cannot transmit data. | **Disabled. No message is delivered.** A working endpoint and confirmed recipient still need to be chosen. The displayed help inbox was published in the source privacy statement; inbox deliverability was not tested. |
| Home — `#mc-embedded-subscribe-form` | Yes | Original HTTPS Mailchimp POST action, `EMAIL`/`FNAME`/`LNAME` fields, new-tab target and honeypot are retained. `novalidate` bypasses automatic browser validation. Email has a `required` CSS class but **no HTML `required` attribute**; no Mailchimp validation script/global was found. Empty form passes `checkValidity()`; malformed nonempty email fails a direct validity probe but automatic validation is bypassed on submission. | **Configured, not proven end to end.** Native form POST is directed at the original Mailchimp account. No request was made to the action, so acceptance, double opt-in, list membership and confirmation/delivery remain unverified. Server-side validation is also unverified. |
| Contact — `#mc-embedded-subscribe-form` | Yes | Same original action, fields, target, honeypot and browser-validation gap as the Home signup. | **Configured, not proven end to end**, under the same restrictions. |
| Home — old Webflow `#email-form` | No | Hidden legacy form. First and Last Name are required; email is not. It is deliberately non-submitting under static hosting. It is separate from the visible Mailchimp signup. | **Disabled and not part of the visible signup flow.** |

The Mailchimp action is `https://analytics.us9.list-manage.com/subscribe/post?u=1a3a91f39ef59858d7c75f6ba&id=db8c88dafd`. This public embed configuration is preserved; its presence alone is not proof of delivery. Validation probes set temporary test values only in the DOM and never invoke a signup submission. [Machine-readable form inventory](evidence/deployed-2026-10-17/audit.json).

Before cutover, connect or replace the contact flow, confirm the intended recipient, correct the signup's browser-validation behaviour, and perform an explicitly authorised controlled Mailchimp delivery test. No new accounts, credentials, backend, or form provider were created during this task.

## Live routing and assets

- **59 deployed files** returned HTTP 200 and matched the local publishable bytes, including all HTML, CSS, JavaScript, font and image files checked. There are 47 referenced source assets; two previously published asset files remain unreferenced and harmless to page rendering.
- All **10 distinct internal anchor destinations** returned HTTP 200, including original Events query URLs and direct no-JavaScript archive fallbacks. The separate functional check covered **37 linked resource/page URLs** and all 47 referenced asset files.
- Mobile menu navigation, Events next/previous, query-page reload and browser history passed on the deployed site. The archive contains all 25 original event records.
- Three nonexistent paths, including a nested Events path and `/sitemap.xml`, returned **real HTTP 404** with the expected styled page. All three response bodies matched the deployed custom 404 file.
- **35 external destinations** were checked with read-only GETs: 27 returned HTTP 200. Eight LinkedIn profile URLs returned HTTP 999 to automated requests, so their final profile availability remains **inconclusive**, rather than established as broken. An HTTP 200 check establishes reachability, not event booking or account functionality.

Detailed statuses, final redirect URLs, response hashes and page/form properties are recorded in [the deployed audit](evidence/deployed-2026-10-17/audit.json). [Deployed functional results](evidence/deployed-2026-10-17/functional.json) record zero form network submissions and no unexpected external resource requests in the exercised flows.

## Responsive screenshots

The deployed comparison matrix covers desktop **1440 × 1000**, tablet **834 × 1112**, and mobile **390 × 844**, at device scale factor 1 in Linux Chromium. It includes all five live pages, all Events pagination states, the explicit page-1 alias, and the real deployed 404. Normal pages also include an open menu; Events includes hover states; Home and Contact include a focused signup field.

The original source and deployed screenshots are both retained. A second source screenshot applies only the two requested removals in the browser DOM, without changing Webflow. Comparison against that expected screenshot uses every RGB channel with zero tolerance and **no masks**. **All 66 deployed comparisons passed with identical pixels against the expected source with those edits**, with matching dimensions and zero recorded HTTP or JavaScript errors. This separates the requested content differences from unintended layout changes. [Full screenshot index and results](evidence/deployed-2026-10-17/README.md).

## Other substantive limitations and inherited issues

| Finding | Verified state / impact | Required decision or follow-up |
| --- | --- | --- |
| Analytics | The source's Webflow first-party telemetry proxy and tracking initialisation are omitted. The preview does not provide the source's tracking. | Decide whether to configure analytics for the future production origin. |
| Event “Read more” placeholder | The 2024 “Over Coming the Data Dilemma” record points to `#` on both the source and copy. It does not open event details. | Supply the correct destination, or explicitly remove/disable that event link. |
| Mobile footer | At 390 px, the inherited footer CSS produces a **1 px-high overflow-hidden container** around 45 px-high social links. The Privacy policy link is `display:none`. The source has the same issue; the sponsor removal does not cause it. | Fix mobile footer visibility/navigation before calling the mobile experience production-ready. Unrelated CSS was not altered in this requested content edit. |
| Keyboard menu access | The inherited hamburger is a `div` with no button role or tab stop (`tabIndex = -1`). It cannot be reached through normal Tab navigation. | Add proper keyboard-accessible menu behaviour. |
| Privacy statement | The copied statement still describes WordPress, Akismet and Wordfence, while this copy runs on GitHub Pages and omits the source tracking setup. | Update it to describe the actual hosting and data flows before cutover. |
| CMS updates | Events and committee profiles are static snapshots. Future Webflow edits do not sync automatically. | Use Git edits or a deliberate recapture/rebuild workflow. The two owner-requested removals persist in the builder. |
| JavaScript | The original menu and animation behaviour needs JavaScript. Query-based archive selection also needs JavaScript; direct archive fallback links work without it. | Accept this behaviour or author a separate accessibility/progressive-enhancement change. |
| Hidden template leftovers | An unused Events overlay retains placeholder links and a template mailto address inherited from the source. It is not the active menu or a form destination. | Optional cleanup after the fidelity migration review. |
| Other browsers | Chromium is verified at the listed sizes. Safari, Firefox, other sizes and transient animation timing have not been tested. | Complete any browser support checks required for launch. |

These findings were audited, not silently fixed outside the requested sponsor/profile removals. The source Webflow site, DNS and custom domains remain unchanged. No new blanket asset licence was added.
