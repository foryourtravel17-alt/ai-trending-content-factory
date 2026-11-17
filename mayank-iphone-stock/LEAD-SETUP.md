# Premium Deals — private lead inbox

- Premium Deals remains on its existing Render service and branch.
- Its public HTML no longer contains a recipient email address or a FormSubmit recipient URL.
- Lead delivery is being migrated to its own private Google Apps Script web app.
- In the Premium Apps Script project's Script Properties set LEAD_EMAIL = the dedicated Premium Deals business Gmail.
- Optional: SEND_CUSTOMER_ACK = true.
- Deploy as Web App, execute as Me, access Anyone. Paste its /exec URL into LEAD_ENDPOINT_URL in index.html.
- Do not advertise until a test enquiry reaches the dedicated Premium Deals business Gmail.
- This handler accepts POST enquiries only; no public lead-list/read endpoint exists.
