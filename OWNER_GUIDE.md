# EuroAfrica owner guide

Sign in at `/admin/` with an account created by the administrator. Content fields use plain text; separate paragraphs with a blank line. HTML and scripts are displayed as text, not executed.

## Where to edit

| Content | Admin location |
| --- | --- |
| Name, tagline, header/footer logos, favicon, email, phone, social links, footer copy, default SEO/social image | Brand, footer & SEO |
| Hero copy, image, CTA labels and paths; trade section intro; about preview; diversity feature; contact banner; optional section visibility | Homepage |
| Direction title, URL slug, introduction, banner, publication and SEO | Trade directions |
| Category summary, overview, image, hero, homepage feature toggle, publication and SEO | Trade categories |
| Product examples, extra sections and gallery | Inline rows at the bottom of each category |
| About and privacy body | About & content pages |
| Contact heading, introduction, confirmation and SEO | Contact page |
| Received submissions and staff notes | Enquiries |
| Navigation labels, local destination paths, grouping and visibility | Footer links |
| See every uploaded content image and open its editing screen | Images |

Interface labels such as “Products included”, navigation labels, and explanatory error messages are maintained in templates. Layout, colours, typography and spacing remain controlled in code.

## Images

Use landscape JPEG, PNG or WebP files under 6 MB. Uploads are decoded, checked, stripped of metadata and re-encoded. Prefer approximately 1600 × 1100 for a hero and 1000 × 750 for cards. Large images receive responsive sizes automatically. Add useful alt text describing the actual image. Do not identify a stock scene as a EuroAfrica facility. Record the licence and source in your own asset register. The uploaded public media folder is not a confidential document store.

The default logo is already extracted. Upload separate replacement header/footer assets if required. For a new brand master, use a transparent PNG or WebP export; arbitrary SVG uploads are deliberately unsupported.

## Categories and publishing

1. Add a trade category and select its direction. Write a unique title, URL slug, summary and useful overview.
2. Add the product examples, optional sections and images using the inline forms. Lower order numbers appear first.
3. Save as a draft, then use **Open private preview**. Preview access requires the corresponding content permission.
4. Check title, description, image rights and alt text. Publish only verified information. Mark **Featured** to show the category on the homepage.
5. Enable **Indexable** for pages that should appear in search. Both category and direction must be published; a non-indexable direction also makes its category pages non-indexable.

Every published category is linked from its direction. Changing a published category or direction slug creates a permanent redirect to its current URL; multiple changes resolve directly to the latest URL. Avoid reusing old URLs for different content. Do not update slugs using bulk database operations, which bypass model signals.

Privacy must be completed and reviewed before publication and before live enquiry collection. Do not publish the placeholder text as a legal notice.

## Enquiries and staff

Enquiries are saved before optional email notification. Check the admin even if email is unavailable. Update status to In progress or Resolved and keep internal staff notes there. Establish a retention schedule with the owner and delete expired enquiries according to that policy. Do not collect unnecessary sensitive data.

An administrator creates staff accounts, enables **Staff status**, and assigns the **Editor** group. Editors can maintain website content and enquiries but cannot administer users, groups, redirect internals or security settings. Never share the administrator password.

## Using the content studio

The navy workspace navigation provides direct editing links. On phones, open **Workspace menu** below the brand and account links. The dashboard shows real published-category, draft and new-enquiry counts. Use search and filters in lists to find a category; order fields use lower numbers first.

Every upload shows its current preview. To replace it, choose another file and save; the replacement receives a new URL to prevent a stale cached image. Existing files are retained. Choose Centre, Top, Bottom, Left or Right crop focus, add optional captions and check the public result. A category uses its card image as the detail hero when no separate hero is supplied. Gallery and product images can be edited in category inline rows or through Images/Products. Save before opening **Open private preview**.

The bundled photographs are illustrative stock images. Their licence/source register is in `assets/stock/README.md`. The starter-image installer only fills blank image fields; it does not replace your saved uploads.

Footer links use local paths such as `/about/` or `/africa-to-europe/`. Links to drafts or missing destinations are automatically hidden. If you rename a page URL, update its custom footer destination too. Edit the footer description, tagline, legal line and contact details in **Brand, footer & SEO**. Social links appear only when supplied. Public privacy links appear only after the policy is published.
