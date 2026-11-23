// Write the deck's own theme colours into ppt/theme/theme1.xml.
// pptxgenjs sets the theme fonts but always writes Office's default palette, so
// scheme colours (pres.SchemeColor.*) would otherwise render in Office blue/orange.
// Also mends <c:crossesAt val="autoZero"/>, which pptxgenjs writes on charts and
// PowerPoint asks to repair (the schema wants <c:crosses val="autoZero"/>).
const fs = require("fs");
const JSZip = require(require.resolve("jszip", { paths: [require.resolve("pptxgenjs")] }));

const ORDER = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4",
  "accent5", "accent6", "hlink", "folHlink"];

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

async function applyTheme(file, theme) {
  for (const k of ORDER) {
    if (!/^[0-9A-Fa-f]{6}$/.test(theme.colors[k] || "")) throw new Error(`theme colour ${k} must be 6 hex digits`);
  }
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const themePath = Object.keys(zip.files).find((f) => /^ppt\/theme\/theme\d+\.xml$/.test(f));
  let xml = await zip.file(themePath).async("string");
  const block = `<a:clrScheme name="${esc(theme.name)}">` +
    ORDER.map((k) => `<a:${k}><a:srgbClr val="${theme.colors[k].toUpperCase()}"/></a:${k}>`).join("") +
    `</a:clrScheme>`;
  xml = xml.replace(/<a:clrScheme[\s\S]*?<\/a:clrScheme>/, block);
  xml = xml.replace(/(<a:theme[^>]*\bname=")[^"]*(")/, `$1${esc(theme.name)}$2`);
  zip.file(themePath, xml);
  for (const f of Object.keys(zip.files).filter((f) => /^ppt\/charts\/chart\d+\.xml$/.test(f))) {
    const c = await zip.file(f).async("string");
    zip.file(f, c.replace(/<c:crossesAt val="autoZero"\/>/g, '<c:crosses val="autoZero"/>'));
  }
  // copy files only: folder entries in the ZIP break opening through some cloud services
  const out = new JSZip();
  for (const [name, entry] of Object.entries(zip.files)) {
    if (!entry.dir) out.file(name, await entry.async("uint8array"), { createFolders: false });
  }
  fs.writeFileSync(file, await out.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

module.exports = { applyTheme };
