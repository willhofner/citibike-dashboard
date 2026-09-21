// Static server for willhofner.com with an optional password gate.
//
// Set SITE_USER and SITE_PASS in the Railway service to require HTTP Basic
// Auth for every request. Leave them unset and the site is served openly,
// so a deploy never locks anyone out before the variables exist.
//
// Local: SITE_USER=me SITE_PASS=secret PORT=8787 node server.js

const http = require("http");
const handler = require("serve-handler");

const PORT = process.env.PORT || 3000;
const USER = process.env.SITE_USER || "";
const PASS = process.env.SITE_PASS || "";
const GATED = Boolean(USER && PASS);

function authorized(req) {
  const header = req.headers.authorization || "";
  if (!header.startsWith("Basic ")) return false;
  const decoded = Buffer.from(header.slice(6), "base64").toString("utf8");
  const idx = decoded.indexOf(":");
  if (idx < 0) return false;
  return decoded.slice(0, idx) === USER && decoded.slice(idx + 1) === PASS;
}

const server = http.createServer((req, res) => {
  // Cheap health check for Railway, never gated.
  if (req.url === "/healthz") {
    res.writeHead(200, { "Content-Type": "text/plain" });
    return res.end("ok");
  }
  if (GATED && !authorized(req)) {
    res.writeHead(401, {
      "WWW-Authenticate": 'Basic realm="willhofner.com", charset="UTF-8"',
      "Content-Type": "text/plain",
      "Cache-Control": "no-store",
    });
    return res.end("This site is private.");
  }
  return handler(req, res, {
    public: __dirname,
    cleanUrls: false,
    headers: [{ source: "**/*", headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }] }],
  });
});

server.listen(PORT, () => {
  console.log(`Serving on :${PORT} (${GATED ? "password gate ON" : "open, set SITE_USER/SITE_PASS to gate"})`);
});
