// Use headless Chrome to measure the real drawn size and background of every
// image in the merged catalog HTML. The JSON feeds build_print_sources.py,
// which decides at what pixel size and on what background to redo each image.
const fs = require("fs");
const path = require("path");

const MM_PER_PX = 25.4 / 96;

const CHROME_CANDIDATES = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
];

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (!arg.startsWith("--")) continue;
    const next = argv[i + 1];
    if (next === undefined || next.startsWith("--")) {
      out[arg.slice(2)] = true;
    } else {
      out[arg.slice(2)] = next;
      i += 1;
    }
  }
  return out;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const skillDir = path.resolve(__dirname, "..");
  const root = path.resolve(args.root || ".");
  const html = path.resolve(args.html || path.join(root, path.basename(root) + ".html"));
  const out = path.resolve(args.out || path.join(skillDir, "tmp", "asset-usage.json"));
  const playwrightDir = path.resolve(args.playwright || path.join(skillDir, "tmp", "pw"));

  if (!fs.existsSync(html)) throw new Error("catalog HTML not found: " + html);
  const { chromium } = require(path.join(playwrightDir, "node_modules", "playwright-core"));
  const executablePath =
    (args.chrome && path.resolve(args.chrome)) ||
    CHROME_CANDIDATES.find((candidate) => fs.existsSync(candidate));
  const browser = await chromium.launch(
    executablePath ? { executablePath, headless: true } : { headless: true }
  );
  const page = await browser.newPage({
    viewport: { width: 794, height: 1123 },
    deviceScaleFactor: 1,
  });
  await page.goto(encodeURI("file:///" + html.replace(/\\/g, "/")), { waitUntil: "load" });
  await page.waitForTimeout(1500);

  const data = await page.evaluate(() => {
    const bgOf = (el) => {
      const own = getComputedStyle(el);
      if (own.backgroundColor && !/^rgba?\(0,\s*0,\s*0,\s*0\)$/.test(own.backgroundColor)) {
        return own.backgroundColor;
      }
      let n = el.parentElement;
      while (n) {
        const cs = getComputedStyle(n);
        if (cs.backgroundImage && cs.backgroundImage !== "none") return "image";
        if (cs.backgroundColor && !/^rgba?\(0,\s*0,\s*0,\s*0\)$/.test(cs.backgroundColor)) {
          return cs.backgroundColor;
        }
        n = n.parentElement;
      }
      return "rgb(255, 255, 255)";
    };

    const rows = [];
    for (const img of document.querySelectorAll("img")) {
      const rect = img.getBoundingClientRect();
      if (!rect.width || !rect.height) continue;
      const cs = getComputedStyle(img);
      const nw = img.naturalWidth;
      const nh = img.naturalHeight;
      const fit = cs.objectFit || "fill";
      const bw = rect.width;
      const bh = rect.height;

      // 图片本身在版面上被画出来的大小（CSS px），跟裁切无关
      let drawnW = bw;
      let drawnH = bh;
      if (nw && nh) {
        if (fit === "contain") {
          const s = Math.min(bw / nw, bh / nh);
          drawnW = nw * s;
          drawnH = nh * s;
        } else if (fit === "cover") {
          const s = Math.max(bw / nw, bh / nh);
          drawnW = nw * s;
          drawnH = nh * s;
        }
      }

      rows.push({
        src: img.getAttribute("src"),
        boxW: bw,
        boxH: bh,
        drawnW,
        drawnH,
        naturalW: nw,
        naturalH: nh,
        bg: bgOf(img),
        // 加了滤镜/透明度的图不能被压到背景色上（例如封底 logo 用 invert 变白）
        filtered:
          cs.filter !== "none" ||
          parseFloat(cs.opacity) < 1 ||
          (cs.mixBlendMode && cs.mixBlendMode !== "normal"),
      });
    }
    return rows;
  });

  await browser.close();
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify({ mmPerPx: MM_PER_PX, rows: data }, null, 1), "utf8");
  console.log(`OK ${out}  imgs=${data.length}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
