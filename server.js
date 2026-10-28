// Static server for willhofner.com with an optional password gate.
//
// Set SITE_USER and SITE_PASS in the Railway service to require HTTP Basic
// Auth for every request. Leave them unset and the site is served openly,
// so a deploy never locks anyone out before the variables exist.
//
// Local: SITE_USER=me SITE_PASS=secret PORT=8787 node server.js

const http = require("http");
const fs = require("fs");
const path = require("path");
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

// Paths that live in the repo but are not part of the site.
const HIDDEN = /^\/(\.|node_modules(\/|$)|server\.js$|package(-lock)?\.json$|railway\.json$|CLAUDE\.md$|ROADMAP\.md$|thoughts\.md$|references(\/|$))/;

function notFound(res) {
  res.writeHead(404, { "Content-Type": "text/plain" });
  res.end("Not found");
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://localhost");
  let pathname = decodeURIComponent(url.pathname);

  // Cheap health check for Railway, never gated.
  if (pathname === "/healthz") {
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
  // HofCamps moved from /gear to /camp; keep old links working.
  if (pathname === "/gear" || pathname.startsWith("/gear/")) {
    res.writeHead(301, { Location: "/camp" + pathname.slice(5) + url.search });
    return res.end();
  }
  // NYC.game lives at /nyc; these are friendlier aliases.
  if (/^\/(knowyournewyork|nyc\.game)\/?$/i.test(pathname)) {
    res.writeHead(301, { Location: "/nyc/" + url.search });
    return res.end();
  }
  // SUBWAY.game lives at /subway.game/; accept any capitalization and a longer alias.
  if (/^\/(subway\.game|knowyoursubway)\/?$/i.test(pathname) && pathname !== "/subway.game/") {
    res.writeHead(301, { Location: "/subway.game/" + url.search });
    return res.end();
  }
  // HofDose was renamed NYC.explore and moved from /dose to /explore; keep old links working.
  if (pathname === "/dose" || pathname.startsWith("/dose/")) {
    res.writeHead(301, { Location: "/explore" + pathname.slice(5) + url.search });
    return res.end();
  }
  if (HIDDEN.test(pathname) || pathname.includes("..")) return notFound(res);

  // Resolve directory requests to their index.html ourselves; never list directories.
  const abs = path.join(__dirname, pathname);
  if (fs.existsSync(abs) && fs.statSync(abs).isDirectory()) {
    if (!pathname.endsWith("/")) {
      res.writeHead(301, { Location: pathname + "/" + url.search });
      return res.end();
    }
    if (!fs.existsSync(path.join(abs, "index.html"))) return notFound(res);
    req.url = pathname + "index.html" + url.search;
  }

  res.setHeader("X-Robots-Tag", "noindex, nofollow");
  return handler(req, res, { public: __dirname, cleanUrls: false, directoryListing: false });
});

server.listen(PORT, () => {
  console.log(`Serving on :${PORT} (${GATED ? "password gate ON" : "open, set SITE_USER/SITE_PASS to gate"})`);
});
