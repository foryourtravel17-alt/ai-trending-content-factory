/**
 * MAYANK DEALS — private enquiry delivery endpoint.
 * One-time setup:
 * 1. Open script.google.com while signed in to the dedicated Mayank business Gmail.
 * 2. Create a project and paste this complete file.
 * 3. In Project Settings → Script Properties, add LEAD_EMAIL = mayanksharmaa1201@gmail.com (keep this value in Script Properties, not in website code).
 * 4. Optional: add SEND_CUSTOMER_ACK = true.
 * 5. Deploy → New deployment → Web app; Execute as: Me; Who has access: Anyone.
 * 6. Copy the /exec URL into LEAD_ENDPOINT_URL in the Mayank website.
 * This web app accepts enquiry POSTs only. It does not expose a list/read endpoint.
 */
const BRAND_NAME = "Mayank Deals";
const ALLOWED_MODELS = ["iPhone 15","iPhone 16","iPhone 17","iPhone Air (17 Air)","iPhone 17 Pro","iPhone 17 Pro Max","iPhone 18 Pro","iPhone Duo"];
const ALLOWED_STORAGE = ["128GB","256GB","512GB","1TB","2TB","Need advice"];

function doGet() {
  return HtmlService.createHtmlOutput("<main style='font:16px system-ui;padding:24px'><h2>Mayank Deals enquiry endpoint</h2><p>Endpoint is online. Enquiries are accepted by POST only. Customer lead records are not publicly readable.</p></main>");
}

function doPost(e) {
  try {
    const p = (e && e.parameter) ? e.parameter : {};
    if (String(p.website || "").trim() !== "") return receipt_("Thank you", "Your request has been received.");
    const name = clean_(p["Customer name"], 80);
    const phone = clean_(p["Phone number"], 10);
    const email = clean_(p.email, 160).toLowerCase();
    const model = clean_(p.Model, 60);
    const storage = clean_(p.Storage, 20);
    const colour = clean_(p["Preferred colour"], 60);
    const city = clean_(p.City, 80);
    const query = clean_(p["Customer query"], 700);
    const consent = clean_(p["Contact consent"], 120);
    const source = clean_(p.source, 40) || "direct";
    const campaign = clean_(p.campaign, 80) || "none";

    if (name.length < 2 || !/^[6-9][0-9]{9}$/.test(phone) ||
        !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ||
        ALLOWED_MODELS.indexOf(model) < 0 || ALLOWED_STORAGE.indexOf(storage) < 0 ||
        city.length < 2 || !consent) {
      return receipt_("Please check your details", "Some required details are missing or invalid. Go back and check the form fields.");
    }

    const props = PropertiesService.getScriptProperties();
    const recipient = props.getProperty("LEAD_EMAIL");
    if (!recipient || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recipient)) {
      return receipt_("Enquiry setup pending", "The sales inbox has not been configured yet. Please contact the page owner through the official social profile.");
    }

    const cache = CacheService.getScriptCache();
    const throttleKey = "lead_" + Utilities.base64EncodeWebSafe(
      Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, phone)
    ).slice(0, 32);
    if (cache.get(throttleKey)) {
      return receipt_("Enquiry already received", "A recent enquiry from this number was already received. The sales team will contact you.");
    }
    cache.put(throttleKey, "1", 60);

    const submitted = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "dd MMM yyyy, hh:mm a");
    const body = [
      "New customer enquiry — " + BRAND_NAME,
      "",
      "Name: " + name,
      "Phone: " + phone,
      "Customer email: " + email,
      "Model: " + model,
      "Storage: " + storage,
      "Colour: " + (colour || "Not specified"),
      "City: " + city,
      "Customer query: " + (query || "None"),
      "Source: " + source,
      "Campaign: " + campaign,
      "Submitted: " + submitted,
      "",
      "Reply directly to this email to contact the customer."
    ].join("\n");

    MailApp.sendEmail({
      to: recipient,
      subject: "New lead [" + source + "] — " + BRAND_NAME + " — " + model,
      body: body,
      replyTo: email,
      name: BRAND_NAME + " Enquiries"
    });

    if (props.getProperty("SEND_CUSTOMER_ACK") === "true") {
      MailApp.sendEmail({
        to: email,
        subject: "We received your enquiry — " + BRAND_NAME,
        body: "Hello " + name + ",\n\nThank you for contacting " + BRAND_NAME +
          ". We have received your enquiry for " + model + " (" + storage +
          "). Our sales team will contact you to confirm price, availability and order details. " +
          "This email is not an order or payment confirmation. Please do not transfer money until you receive confirmed order instructions.\n\n" +
          BRAND_NAME
      });
    }
    return receipt_("Enquiry received", "Thank you, " + escape_(name) + ". Your enquiry has been sent to the Mayank sales team. They will contact you to confirm the details.");
  } catch (err) {
    return receipt_("Could not submit enquiry", "Please try again later or contact the business through its official social profile.");
  }
}

function clean_(value, max) {
  return String(value == null ? "" : value).replace(/[\u0000-\u001F\u007F]/g, " ").trim().slice(0, max);
}
function escape_(s) {
  return String(s).replace(/[&<>"]/g, function(c) {
    return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c];
  });
}
function receipt_(title, message) {
  return HtmlService.createHtmlOutput(
    "<!doctype html><html><meta name='viewport' content='width=device-width,initial-scale=1'><body style='margin:0;min-height:100vh;display:grid;place-items:center;background:#080a0e;color:#f5f7fb;font:16px/1.6 system-ui'><main style='max-width:520px;margin:24px;padding:30px;border:1px solid #354154;border-radius:20px;background:#111722;text-align:center'><div style='color:#e8c77e;font-weight:800;letter-spacing:.12em'>MAYANK DEALS ✦</div><h1>" + escape_(title) + "</h1><p>" + escape_(message) + "</p><a href='https://mayank-deals.onrender.com/' style='display:inline-block;margin-top:12px;padding:12px 18px;border-radius:999px;background:#e8c77e;color:#1b160b;text-decoration:none;font-weight:800'>Back to catalogue</a></main></body></html>"
  );
}
