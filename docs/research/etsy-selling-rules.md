# Etsy selling rules for a one-off-priced desktop installer (research)

Retrieved 2026-10-11 from primary sources only (Etsy policy and help pages, ATO, ACCC). Each page was read in full on that date unless marked otherwise. "Updated" is the date the page itself shows. Anything not from a primary source is labelled **unverified**. This is research, not legal or tax advice.

## Summary

1. **Software / external links:** No Etsy policy mentions standalone software or installers either way. A digital item must be "made and/or designed by you", and the listing file types do **not** include .exe or .dmg (a .zip and .pdf are allowed). Etsy has no rule on a PDF that links to an external host, but the off-platform policy bans QR codes that direct members off Etsy. Treat as **unconfirmed; ask Etsy Support in writing**.
2. **Tax:** Etsy collects and remits VAT/GST on digital downloads from buyers in about 40 listed countries and regions, **including Australia**, "no matter where your shop is located". US state sales tax is collected where marketplace facilitator laws apply. Whether Etsy's collection removes an **Australian** seller's own GST obligation is **not stated** by Etsy, and the ATO only transfers it to a platform for Australian merchants under a written agreement.
3. **Currency:** One shop currency; default USD; 22 currencies are supported for Etsy Payments, including AUD. Buyers see prices converted at market rates. Listing in a currency other than the bank account's costs a **2.5%** conversion fee. Payouts are in the bank account's domestic currency (AUD for an Australian account).
4. **Subscriptions:** No generic rule on seller recurring billing was found. Etsy prohibits selling "access to software or app membership subscriptions", and no recurring-billing feature for sellers appears in the pages read. One-off pricing is the only evidently supported model.
5. **Refunds / ACL:** Return policies cannot be set on digital listings; the seller decides how to resolve issues, and Etsy's case system and Purchase Protection can still force a refund. Etsy states no Australian Consumer Law (ACL) requirement; it only says sellers must comply with applicable laws. The ACCC says "no refunds" policies cannot remove statutory refund rights.

---

## 1. Is standalone software allowed, and what about external download links?

**What Etsy says**

- Digital items "must be made and/or designed by you, the seller"; they can be premade files or custom files. Source: <https://help.etsy.com/hc/en-us/articles/115015628347-How-to-Manage-Your-Digital-Listings> (retrieved 2026-10-11).
- Creativity Standards, "Designed by a seller": qualifies are "digital downloads of sellers' original designs", defined as "original content created by the seller, sold as a digital download". Examples given are a graphic design, audio, text document or scan of artwork. Disqualified are other people's work and AI prompt bundles. Software is not named either way. Source: <https://www.etsy.com/legal/creativity/> (updated 10 Jun 2025; retrieved 2026-10-11).
- Prohibited Items Policy (updated 6 Oct 2026): the eight prohibited categories (alcohol/drugs, animal products, dangerous items, hate items, illegal/highly regulated items, internationally regulated items, nudity, violence) do not mention software. Relevant general lines: sellers must follow applicable laws, and for cross-border sales "you are responsible for complying with laws and regulations of the country of destination". Source: <https://www.etsy.com/legal/prohibited/> (retrieved 2026-10-11).
- Services policy (updated 9 Jun 2026) prohibits "Access to software or app membership subscriptions (e.g., Adobe)" and virtual gaming assets, including "game access codes or licenses". A one-off installer is not obviously either, but a listing whose product is "access" to something hosted elsewhere is closest to this wording. Source: <https://www.etsy.com/legal/policy/services/242665313101> (retrieved 2026-10-11).
- Supported digital file types listed by Etsy: .bmp .doc .gif .jpeg .jpg .mobi .mov .mp3 .mpeg .pdf .png .psp .rtf .stl .txt .zip .ePUB .iBook. **.exe and .dmg are not listed.** Limits: up to 5 files, 20 MB each; file names max 70 characters; no variations on digital listings. Source: same digital listings help page as above. The page does not say whether the list is exhaustive or enforced on upload.
- The digital listings page also lets a seller add "a note for buyers" that buyers "can see on their Downloads page" after purchase. This is a possible place for the download instructions in addition to the PDF. Source: same page.

**External links and off-platform delivery**

- Etsy Seller Policy (updated 5 Oct 2026): sellers must "Not facilitate off-platform transactions", and may not upload content that "Encourages or facilitates an off-platform transaction". Source: <https://www.etsy.com/legal/sellers>.
- Off-Platform Transactions Policy (updated 5 Oct 2026) defines the banned conduct as: instructing a member to pay or purchase outside Etsy checkout, sharing contact details to complete a transaction, off-platform discounts or incentives, and "using a QR code to direct members off Etsy". It also bans charging extra after checkout. It says nothing about delivering a purchased product via an external link. Source: <https://www.etsy.com/legal/policy/off-platform-transactions/1254654515806>.
- Fees & Payments Policy section 2 repeats that "any action to move a transaction off the Etsy platform is strictly prohibited". Source: <https://www.etsy.com/legal/fees/> (updated 5 Oct 2026).

**Not found / unverified**

- No primary Etsy page states that a delivered PDF may or may not contain an external download link, or that large files must be delivered another way. **Not found / unverified.**
- The QR-code ban is written for directing members to transact off Etsy, not for delivery of an already-bought file, but it is the closest written rule. Safest reading: use a plain text link (not a QR code), and do not mention buying, discounts or contact details elsewhere in the PDF or listing. This is an inference, **unverified**.
- Whether Etsy treats a .exe/.dmg inside a .zip as acceptable: **not found / unverified**. Whether a PDF-with-link satisfies "digital item delivered" for the VAT rules (which apply to items "delivered via automatic download"): **not found / unverified**.
- Recommended before listing: ask Etsy Support (in writing) whether a downloadable desktop application, delivered as a PDF with a host link, is acceptable. Also covered by the project's existing note in `docs/retail-edition-design-notes.md` Q5.

---

## 2. VAT / GST / sales tax on digital goods

### What Etsy collects and remits

- "Etsy collects and remits VAT on digital items purchased by buyers located in certain countries." The listed buyer locations (digital items delivered by automatic download): Armenia, Australia, Bosnia, Canada, Chile, Colombia, Egypt, the EU, Georgia, Ghana, Kazakhstan, Kyrgyzstan, Iceland, India, Indonesia, Kenya, Malaysia, Mexico, Moldova, Morocco, New Zealand, Nigeria, Norway, Peru, Philippines, Saudi Arabia, Serbia, Singapore, South Africa, South Korea, Switzerland, Taiwan, Tanzania, Thailand, Turkiye, Uganda, Ukraine, the UAE, the UK, Uzbekistan, Vietnam. The page uses "VAT" to cover GST, HST, JCT etc. Source: <https://help.etsy.com/hc/en-us/articles/115015587567-How-VAT-Works-on-Digital-Items> (retrieved 2026-10-11).
- Applies "no matter where your shop is located". Buyers pay VAT on top of the listing price, shown in the total; "Sellers are not responsible for adding VAT to their digital listing prices." With Etsy Payments the VAT is deducted before funds reach the seller's payment account. Same source.
- Fees & Payments Policy section 5 "Digital VAT Fees": Etsy is "required to collect and remit VAT" on digital items delivered by automatic download in certain countries, and "you will not have to take any further action" for Etsy Payments sales. Source: <https://www.etsy.com/legal/fees/>.
- US: Etsy calculates, collects and remits sales tax on orders to US customers, in states with marketplace laws. For digital items some states apply by buyer billing address (the policy names Washington). Etsy uses the **category the seller assigns to each listing** to calculate tax, and the seller indemnifies Etsy for miscategorisation. Source: <https://www.etsy.com/legal/fees/>, section 5.A and 5.C.
- Etsy's older Seller Handbook statement that "Etsy is responsible for collecting and remitting tax on digital downloads on your behalf" and that the buyer receipt "is not an official VAT invoice" (seller must supply a compliant invoice where required). Source: <https://www.etsy.com/au/seller-handbook/article/changes-to-how-included-tax-is/43920518590> (undated, written when the sales tax tool was restricted; treat as historical).

### What stays with the seller

- Fees policy section 5: "Aside from the limited circumstances set out below, you are responsible for collecting and paying any taxes associated with using and making sales through Etsy's services." Terms of Use likewise: you are "solely responsible for collecting and/or paying any applicable taxes" except where Etsy collects and remits. Sources: <https://www.etsy.com/legal/fees/>; <https://www.etsy.com/au/legal/terms-of-use>.
- The seller's own income tax, any sales/VAT in countries not on the list above, and (outside the US) the 6.5% transaction fee applies to the listing price including any taxes the seller is responsible for. Source: <https://www.etsy.com/legal/fees/> (Transaction Fees).
- Etsy may charge VAT/GST on its own seller fees depending on seller location and status. Source: <https://www.etsy.com/legal/fees/>, "VAT on Seller Fees".
- If a sale does not go through Etsy Payments (e.g. stand-alone PayPal), the buyer's VAT is added to the seller's payment account and the seller must pay it to Etsy. Source: How VAT Works on Digital Items page above.
- Etsy tells sellers to consult a tax advisor; it does not give tax advice. The countries/regions where a US-style state registration might still be required of the seller (economic nexus) are described only generally for physical goods; **digital-goods nexus rules: not found / unverified**.

### Australian seller: Australian GST

**GST registration threshold (ATO, updated 14 Sep 2026)**

- Must register for GST when GST turnover is **A$75,000 or more** (current month plus previous 11 months, or projected current plus next 11), within 21 days of exceeding it. Registration needs an ABN first. Registering below the threshold is optional (minimum 12 months once registered). Source: <https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/registering-for-gst> (retrieved 2026-10-11).
- GST turnover for the threshold **includes GST-free export sales that are "connected with Australia"**, even though they are GST-free (ATO example of an online business with half its sales overseas). Source: <https://www.ato.gov.au/businesses-and-organisations/international-tax-for-business/australians-doing-business-overseas/exports-and-gst> (updated 28 Jul 2023; retrieved 2026-10-11).
- **Possible no-threshold trigger, needs a tax adviser:** the same registration page lists "if you earn income through the sharing economy or digital platforms (for example, food delivery services or other platform-based work)" as a reason to register. The ATO's sharing economy page (updated 2 Jul 2026) lists "selling digital goods (intangibles), such as digital products or goods (for example, videos, eBooks, virtual items...)" as a sharing economy activity, while saying "online selling or classifieds" is not. Whether selling a software installer via Etsy falls under that registration rule is **not stated and unverified**. Source: <https://www.ato.gov.au/businesses-and-organisations/income-deductions-and-concessions/sharing-economy-and-tax/types-of-activities-in-the-sharing-economy>. That page also says EDP operators report to the ATO under the Sharing Economy Reporting Regime, so Etsy sales will likely be visible to the ATO.

**Sales to overseas Buyers**

- Exports are generally GST-free. For supplies other than goods (services, rights, other intangibles), the ATO test is that the recipient is outside Australia and use is outside Australia; the supply is not GST-free if provided in Australia. A registered business can still claim credits on its purchases. Source: Exports and GST page above.
- The ATO page's examples cover services and content subscriptions (an Australian creator sorting platform sales into GST-free offshore buyers and taxable Australian buyers). It does not give an example for a **downloadable software licence**, and it says if buyer location cannot be obtained "all her sales will be taxable". Classification of a software download as GST-free export: **likely under the "other than goods" rule, but not confirmed by the page; unverified**. See the ATO ruling reference on the page (GSTR 2019/1) for the formal test.
- Etsy supplies buyer location (it computes VAT by buyer location, per the VAT help page), but whether Etsy's reports are sufficient evidence for the ATO: **not found / unverified**.

**Sales to Australian Buyers and the EDP rules**

- ATO, "If you are an electronic distribution platform operator" (updated 11 Sep 2025): an EDP operator is generally responsible for GST on a sale of an imported service or digital product to an Australian consumer when the merchant is **outside** Australia, if the operator is registered or required to be registered. For **Australian-based merchants**, an EDP operator "can also agree to be responsible for GST" only if all of these apply: sales are digital products/services made electronically, there is a **written agreement with the merchant before the sale**, and the operator is registered for GST. Otherwise the merchant remains responsible. Source: <https://www.ato.gov.au/businesses-and-organisations/international-tax-for-business/gst-for-non-resident-businesses/how-to-charge-gst/if-you-are-an-edp-operator> (retrieved 2026-10-11).
- Etsy says it collects the VAT/GST from Australian buyers of digital items "no matter where your shop is located" (page above), but nothing read states that Etsy has made, or the seller has accepted, an EDP written agreement taking over an **Australian seller's** GST liability. Terms of Use section on taxes only says Etsy "will calculate, collect and remit value-added tax or VAT" where applicable. **Whether an Australian ABN seller must still report/pay GST on those Australian sales, and whether they count towards the A$75,000 threshold: not found / unverified. Ask a tax agent or the ATO.**
- If the seller is **not** required to register (under A$75,000), nothing read says the seller must register just because Etsy collects Australian GST from buyers.

**Seller invoices:** Etsy's receipt is not a tax invoice (Seller Handbook page above); Australian tax invoice rules for GST-registered sellers: **not covered here; unverified**.

---

## 3. Currencies

- **Shop currency** is a single universal setting for all listings; "each new listing you create will be priced in that currency"; if none chosen the default is **USD**. Change at Shop Manager > Finances > Payment Settings > Currency; can revert within 14 days. Source: <https://help.etsy.com/hc/en-us/articles/360000336747-How-to-List-Items-in-Your-Preferred-Currency> (retrieved 2026-10-11).
- **Currencies supported for Etsy Payments (22):** USD, AUD, GBP, CAD, CNY, DKK, EUR, HKD, IDR, ILS, MYR, MXN, MAD, NZD, NOK, PHP, SGD, ZAR, SEK, CHF, TRY, VND. Source: <https://help.etsy.com/hc/en-us/articles/360000337767-Currencies-Supported-for-Etsy-Payments> (retrieved 2026-10-11). The page does not say whether a shop can list in a currency outside this list; the listing page above only says "Shoppers on Etsy can view prices in any of our supported browsing currencies".
- **Buyer view:** Buyers viewing in one of the 22 currencies "can complete Etsy Payments orders in that currency. Item prices will be automatically converted based on current market rates." Buyers viewing in another browsing currency "will see the seller's original listing currency when completing an order", and their bank may charge an international transaction fee. Source: Currencies Supported page above.
- **Buyer conversion charge:** Etsy "applies an additional currency conversion charge" when a conversion is required, rates updated regularly, and displayed rates are informational only; the amount of the buyer-side charge: **not found**. PayPal buyers get PayPal's conversion at PayPal's rates. Source: <https://help.etsy.com/hc/en-us/articles/115015520608-How-to-Change-Your-Currency-Settings-for-Shopping-on-Etsy>.
- **Seller conversion fee:** If the shop currency differs from the payment account currency, Etsy converts and charges **2.5%** of the sale amount, subtracted before funds reach the payment account; it is not possible to time conversion. Etsy recommends listing in the payment account's currency. Sources: <https://help.etsy.com/hc/en-us/articles/360000344668-Currency-Conversion-Fees>; <https://www.etsy.com/legal/fees/> (Currency Conversion).
- **Payout currency:** In Australia (among others), Available Funds "can only be deposited into bank accounts, in the domestic currency of the account" (AUD for an Australian bank account). Source: <https://www.etsy.com/legal/etsy-payments/> (retrieved 2026-10-11). Etsy Payments is available to sellers in Australia (same page).
- **Other fees on an AUD shop:** US$0.20 listing fee (4-month expiry, auto-renew), 6.5% transaction fee, plus Etsy Payments processing fees by country (per-country amounts are in the Etsy Payments Policy, not extracted here). The transaction fee is assessed in the shop currency and converted to the payment account currency. Source: <https://www.etsy.com/legal/fees/>.
- **Implication (inference):** an AUD shop with an AUD bank account avoids the 2.5% fee; overseas buyers still see converted prices in their own currency when it is one of the 22. Prices shown to buyers in Etsy VAT-collected countries include VAT on top of the listed price.

---

## 4. Subscriptions (recurring billing)

- Seller Policy (updated 5 Oct 2026): no mention of buyer subscriptions or recurring billing by sellers. Source: <https://www.etsy.com/legal/sellers>.
- Services policy (updated 9 Jun 2026), prohibited "Membership Subscriptions": access to streaming platform subscriptions, **"Access to software or app membership subscriptions (e.g., Adobe)"**, and gaming subscriptions. Source: <https://www.etsy.com/legal/policy/services/242665313101>.
- Fees & Payments Policy: the only "Subscription Fees" described are Etsy's own seller programmes (Etsy Plus, US$10/month; Pattern, US$15/month) billed by Etsy to the seller. Source: <https://www.etsy.com/legal/fees/>.
- Listings are one-off purchases (digital items: no variations, one download purchase per order). Source: digital listings help page. No seller-side recurring-billing feature was found in any page read.
- **Conclusion:** A generic ban on "subscriptions" is **not found** in the Seller Policy or the pages read; software/app membership access is explicitly banned, and recurring billing is not offered as a feature, so a one-off price is the only supported model. Statement from the project's notes ("Etsy reportedly prohibits subscriptions") is therefore only partly confirmed.

---

## 5. Refunds for digital items and Australian Consumer Law

**Etsy rules**

- "It's not possible to set return or exchange policies on your digital listings. If a buyer contacts you about an issue with a digital item they've purchased, you can still choose to resolve the issue as you see fit." Source: <https://help.etsy.com/hc/en-us/articles/7869401615255-How-do-I-Set-Return-Policies-on-My-Listings> (retrieved 2026-10-11). A return policy is only required for physical items.
- Each seller is responsible for their own refund/return policy; a return agreement made with a buyer must be honoured. Source: <https://help.etsy.com/hc/en-us/articles/360000572888-Refunds-Returns-and-Exchanges-for-Sellers>.
- Seller Policy: sellers must resolve order issues directly; after the buyer contacts the seller, the seller has **48 hours** before the buyer can open a case; buyers can open cases for items that "do not match the listing description"; Etsy may refund the buyer and recoup funds from the seller's account. "Canceling an order is the only way to revoke a buyer's access to a file after it has been purchased" (digital listings help page). Sources: <https://www.etsy.com/legal/sellers>; digital listings page.
- Purchase Protection (cases opened from 7 May 2026): Etsy covers up to US$250 of a refund and any remainder is charged to the seller; situations listed include an item that matches the listing but the buyer says it does not. Whether digital orders are eligible on the same terms: the page does not say; **not found**. Source: Refunds for Sellers page above.
- EU/UK buyers: Etsy says the EU Omnibus Directive's 14-day withdrawal right "excludes ... digital items" (Etsy summary of the law; the Seller Policy adds that rights for digital items vary by EU member state or the UK). Etsy also says it cannot advise on compliance. Sources: <https://help.etsy.com/hc/en-us/articles/5703129136407-How-Do-I-Follow-EU-Law-Regarding-Returns-and-Refunds>; <https://www.etsy.com/legal/sellers>.
- Reviews: buyers of digital items can review for 100 days from first download or 12 months from purchase, whichever comes first (Seller Policy).

**Australian Consumer Law**

- Etsy does not state any ACL-specific obligation for sellers that I could find. Relevant lines: sellers are "responsible for complying with all applicable laws" (Seller Policy, Seller Standards); the Terms of Use for users in Australia are governed by Australian law and courts, and consumers "may be entitled to invoke the mandatory consumer protection laws of your country of residence" (Terms of Use section 12). Sources: <https://www.etsy.com/legal/sellers>; <https://www.etsy.com/au/legal/terms-of-use>. **ACL-specific Etsy requirement: not found.**
- ACCC (page read 2026-10-11): consumers are entitled to a repair, replacement or refund when a product does not meet the consumer guarantees; "Businesses can't take away a consumer's right to a refund or replacement for faulty products or services"; it is illegal to rely on terms such as "no refunds"; a major problem (unsafe, very different from description, or one that would have stopped the purchase, or cannot be used for its normal purpose and cannot easily be fixed in reasonable time) lets the consumer choose a refund (full amount, no deduction for use), replacement or compensation for the drop in value; minor problems must be fixed free. Change of mind is not covered unless the business has its own change-of-mind policy, which it must then follow. Source: <https://www.accc.gov.au/consumers/problem-with-a-product-or-service-you-bought/repair-replace-refund-cancel>.
- The ACCC page does not mention software or digital downloads. That software counts as "goods" under the ACL, and the extent to which the guarantees apply to an Australian business selling to **overseas** buyers, are **not confirmed by a primary source here (unverified)**.
- Implication for the project's EULA/refund policy (inference): the "no warranty / limited liability" EULA cannot exclude statutory guarantees for Australian consumers, and the Etsy digital listing cannot carry a formal return policy, so refund terms belong in the listing description and the PDF/EULA.

---

## Open items to resolve before listing

1. Written confirmation from Etsy Support that a desktop application (PDF delivering an external installer link) is an allowed digital item; confirm .zip/.exe handling and the QR-code point in Section 1.
2. Tax agent / ATO advice on: whether the sharing-economy "digital platform" registration rule applies; whether Etsy-collected Australian GST changes the seller's GST reporting; and treatment of overseas sales as GST-free exports (Section 2).
3. Etsy Payments per-country processing fee for Australia (see <https://www.etsy.com/legal/etsy-payments/>; not extracted here).
