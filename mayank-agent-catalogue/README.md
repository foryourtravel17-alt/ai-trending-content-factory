# Mayank Deals — separate sales-agent website

- Separate Render static site/service from Premium Deals.
- Separate branch: site/mayank-agent.
- Catalogue/prices follow the common catalogue supplied for the sales network. iPhone 15 is ₹12,999.
- Public website does not contain a lead recipient email address.
- Lead delivery uses a private Google Apps Script web app. Configure its Script Property LEAD_EMAIL as mayanksharmaa1201@gmail.com, then deploy as Web App (Execute as Me, access Anyone). Copy its /exec URL into LEAD_ENDPOINT_URL in index.html.
- Optional Script Property SEND_CUSTOMER_ACK=true sends a simple email receipt to the customer.
- Leads are delivered to that brand's dedicated Gmail only. No public lead-list or read endpoint exists.
- Do not advertise this page until the Apps Script URL is configured and a real test enquiry reaches the intended inbox.
- Instagram profile link should use a brand-specific UTM query, e.g. ?utm_source=instagram&utm_medium=organic&utm_campaign=mayank_profile.
