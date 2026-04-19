const fs = require("fs");
const path = require("path");
const PptxGenJS = require("pptxgenjs");

const pptx = new PptxGenJS();
pptx.author = "MarketState";
pptx.company = "MarketState";
pptx.subject = "Investor Pitch Deck";
pptx.title = "MarketState Pitch Deck";
pptx.layout = "LAYOUT_WIDE";
pptx.theme = {
  headFontFace: "Playfair Display",
  bodyFontFace: "Public Sans",
  lang: "en-US",
};

const FONTS = {
  display: "Playfair Display",
  sans: "Public Sans",
};

const COLORS = {
  bg: "ECEBE6",
  ink: "2E313A",
  muted: "6A6E78",
  line: "8B8E96",
  accentA: "3B82F6",
  accentB: "14B8A6",
  accentC: "F59E0B",
  white: "FFFFFF",
};

const IMG_TYPICAL = path.join(__dirname, "typical_customer.png");
const IMG_STACK = path.join(__dirname, "tech_stack.png");

function addBrand(slide) {
  slide.addText("MarketState\nCompany", {
    x: 10.65,
    y: 6.18,
    w: 1.95,
    h: 0.62,
    fontFace: FONTS.display,
    fontSize: 13,
    color: COLORS.ink,
    breakLine: true,
    lineSpacingMultiple: 0.95,
    margin: 0.01,
  });

  slide.addShape(pptx.ShapeType.rect, {
    x: 12.0,
    y: 6.24,
    w: 0.38,
    h: 0.48,
    line: { color: COLORS.ink, pt: 1.1 },
    fill: { color: COLORS.bg, transparency: 100 },
  });
  slide.addShape(pptx.ShapeType.line, {
    x: 12.0,
    y: 6.39,
    w: 0.38,
    h: 0,
    line: { color: COLORS.ink, pt: 1 },
  });
  slide.addShape(pptx.ShapeType.line, {
    x: 12.0,
    y: 6.55,
    w: 0.38,
    h: 0,
    line: { color: COLORS.ink, pt: 1 },
  });
}

function addDecor(slide) {
  slide.background = { color: COLORS.bg };

  slide.addShape(pptx.ShapeType.ellipse, {
    x: 11.0,
    y: -0.65,
    w: 3.0,
    h: 3.0,
    fill: { color: COLORS.accentA, transparency: 88 },
    line: { color: COLORS.accentA, transparency: 100 },
  });

  slide.addShape(pptx.ShapeType.ellipse, {
    x: -1.0,
    y: 5.5,
    w: 2.6,
    h: 2.6,
    fill: { color: COLORS.accentB, transparency: 90 },
    line: { color: COLORS.accentB, transparency: 100 },
  });
}

function addSectionHeader(slide, title, index) {
  slide.addText(title.toUpperCase(), {
    x: 0.75,
    y: 0.5,
    w: 8.0,
    h: 0.38,
    fontFace: FONTS.sans,
    fontSize: 20,
    bold: true,
    charSpace: 4,
    color: COLORS.ink,
  });

  slide.addShape(pptx.ShapeType.line, {
    x: 0.75,
    y: 1.12,
    w: 11.85,
    h: 0,
    line: { color: COLORS.line, pt: 1 },
  });

  slide.addText(`${index}/10`, {
    x: 12.0,
    y: 0.12,
    w: 0.7,
    h: 0.2,
    fontFace: FONTS.sans,
    fontSize: 9,
    color: COLORS.muted,
    align: "right",
  });
}

function addImageBlock(slide, imgPath, x, y, w, h) {
  if (fs.existsSync(imgPath)) {
    slide.addShape(pptx.ShapeType.roundRect, {
      x: x - 0.06,
      y: y - 0.06,
      w: w + 0.12,
      h: h + 0.12,
      fill: { color: COLORS.white },
      line: { color: COLORS.line, pt: 1 },
      radius: 0.06,
    });
    slide.addImage({ path: imgPath, x, y, w, h });
  } else {
    slide.addShape(pptx.ShapeType.roundRect, {
      x,
      y,
      w,
      h,
      fill: { color: "D7DEE8" },
      line: { color: COLORS.line, pt: 1 },
      radius: 0.06,
    });
  }
}

function addCover() {
  const s = pptx.addSlide();
  addDecor(s);

  s.addText([{ text: "Pitch Deck", options: { fontFace: FONTS.display } }], {
    x: 0.62,
    y: 0.9,
    w: 6.7,
    h: 1.0,
    fontSize: 64,
    color: COLORS.ink,
    margin: 0.01,
  });

  s.addShape(pptx.ShapeType.line, {
    x: 0.75,
    y: 2.96,
    w: 8.0,
    h: 0,
    line: { color: COLORS.line, pt: 1 },
  });

  s.addText("MARKETSTATE INVESTMENT INTELLIGENCE PLATFORM", {
    x: 0.75,
    y: 3.18,
    w: 7.6,
    h: 0.42,
    fontFace: FONTS.sans,
    fontSize: 21,
    bold: true,
    charSpace: 4,
    color: COLORS.ink,
  });

  addImageBlock(s, IMG_TYPICAL, 8.9, 0.8, 3.35, 4.45);

  s.addShape(pptx.ShapeType.roundRect, {
    x: 8.9,
    y: 5.45,
    w: 3.35,
    h: 0.9,
    fill: { color: COLORS.white, transparency: 8 },
    line: { color: COLORS.line, pt: 1 },
    radius: 0.05,
  });
  s.addText("Focused on active investors\nwith fragmented portfolios", {
    x: 9.1,
    y: 5.62,
    w: 2.95,
    h: 0.55,
    fontFace: FONTS.sans,
    fontSize: 12,
    color: COLORS.ink,
    bold: true,
    breakLine: true,
  });

  s.addText("Prepared by: Founder Team\nDate: April 2026", {
    x: 0.75,
    y: 5.88,
    w: 4.2,
    h: 0.7,
    fontFace: FONTS.sans,
    fontSize: 16,
    color: COLORS.ink,
    breakLine: true,
    lineSpacingMultiple: 1.2,
  });

  addBrand(s);
  s.addText("1/10", {
    x: 12.0,
    y: 0.12,
    w: 0.7,
    h: 0.2,
    fontFace: FONTS.sans,
    fontSize: 9,
    color: COLORS.muted,
    align: "right",
  });
}

function addProblem() {
  const s = pptx.addSlide();
  addDecor(s);
  addSectionHeader(s, "The Problem", 2);

  s.addText(
    "Investors manage money across brokers,\npensions, and crypto apps,\nbut still lack one system that tells\nthem if they are actually on track.",
    {
      x: 0.75,
      y: 1.55,
      w: 6.9,
      h: 3.7,
      fontFace: FONTS.display,
      fontSize: 42,
      color: COLORS.ink,
      breakLine: true,
      lineSpacingMultiple: 1.05,
    }
  );

  s.addShape(pptx.ShapeType.roundRect, {
    x: 7.95,
    y: 1.6,
    w: 4.55,
    h: 3.3,
    fill: { color: COLORS.white, transparency: 6 },
    line: { color: COLORS.line, pt: 1 },
    radius: 0.06,
  });
  s.addText(
    "Consequences\n• Reactive decisions\n• Weak risk visibility\n• Spreadsheet chaos\n• Low confidence in next actions",
    {
      x: 8.23,
      y: 1.9,
      w: 4.0,
      h: 2.7,
      fontFace: FONTS.sans,
      fontSize: 18,
      bold: true,
      color: COLORS.ink,
      breakLine: true,
      lineSpacingMultiple: 1.2,
    }
  );

  addBrand(s);
}

function addSolution() {
  const s = pptx.addSlide();
  addDecor(s);
  addSectionHeader(s, "Our Solution", 3);

  s.addText(
    "MarketState is a goal-driven investor operating system.",
    {
      x: 0.75,
      y: 1.65,
      w: 10.8,
      h: 0.7,
      fontFace: FONTS.display,
      fontSize: 42,
      color: COLORS.ink,
    }
  );

  const cards = [
    { x: 0.75, color: COLORS.accentA, title: "Unify", body: "Portfolio and net-worth visibility across accounts." },
    { x: 4.53, color: COLORS.accentB, title: "Understand", body: "Risk and performance context tied to long-term goals." },
    { x: 8.31, color: COLORS.accentC, title: "Act", body: "Alert-driven workflow for timely, higher-conviction decisions." },
  ];

  cards.forEach((c) => {
    s.addShape(pptx.ShapeType.roundRect, {
      x: c.x,
      y: 2.72,
      w: 3.45,
      h: 2.95,
      fill: { color: COLORS.white },
      line: { color: COLORS.line, pt: 1 },
      radius: 0.08,
    });
    s.addShape(pptx.ShapeType.rect, {
      x: c.x,
      y: 2.72,
      w: 3.45,
      h: 0.2,
      fill: { color: c.color },
      line: { color: c.color },
    });
    s.addText(c.title, {
      x: c.x + 0.22,
      y: 3.02,
      w: 3.0,
      h: 0.45,
      fontFace: FONTS.sans,
      fontSize: 26,
      bold: true,
      color: COLORS.ink,
    });
    s.addText(c.body, {
      x: c.x + 0.22,
      y: 3.62,
      w: 3.0,
      h: 1.6,
      fontFace: FONTS.sans,
      fontSize: 16,
      color: COLORS.ink,
      breakLine: true,
      lineSpacingMultiple: 1.2,
    });
  });

  addBrand(s);
}

function addMarket() {
  const s = pptx.addSlide();
  addDecor(s);
  addSectionHeader(s, "Market Opportunity", 4);

  s.addText("Validated category. Focused wedge.", {
    x: 0.75,
    y: 1.58,
    w: 7.3,
    h: 0.7,
    fontFace: FONTS.display,
    fontSize: 38,
    color: COLORS.ink,
  });

  const bars = [
    { label: "Category demand", val: 10.7, color: COLORS.accentA },
    { label: "Willingness to pay", val: 9.0, color: COLORS.accentB },
    { label: "Niche fit clarity", val: 7.7, color: COLORS.accentC },
  ];

  bars.forEach((b, i) => {
    const y = 2.65 + i * 1.08;
    s.addText(b.label, {
      x: 0.9,
      y: y - 0.02,
      w: 2.7,
      h: 0.25,
      fontFace: FONTS.sans,
      fontSize: 14,
      bold: true,
      color: COLORS.ink,
    });
    s.addShape(pptx.ShapeType.roundRect, {
      x: 3.15,
      y,
      w: 8.45,
      h: 0.28,
      fill: { color: "DBE2EC" },
      line: { color: "DBE2EC" },
      radius: 0.05,
    });
    s.addShape(pptx.ShapeType.roundRect, {
      x: 3.15,
      y,
      w: b.val,
      h: 0.28,
      fill: { color: b.color },
      line: { color: b.color },
      radius: 0.05,
    });
  });

  addTextCallout(
    s,
    0.75,
    5.7,
    11.4,
    0.9,
    "Entry strategy: start with active multi-account investors and expand only after proving paid conversion + retention."
  );

  addBrand(s);
}

function addTextCallout(slide, x, y, w, h, text) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    fill: { color: COLORS.white, transparency: 6 },
    line: { color: COLORS.line, pt: 1 },
    radius: 0.08,
  });
  slide.addText(text, {
    x: x + 0.2,
    y: y + 0.22,
    w: w - 0.4,
    h: h - 0.2,
    fontFace: FONTS.sans,
    fontSize: 15,
    color: COLORS.ink,
    bold: true,
    breakLine: true,
  });
}

function addMvp() {
  const s = pptx.addSlide();
  addDecor(s);
  addSectionHeader(s, "MVP Product Scope", 5);

  s.addText("Five features that close the value loop", {
    x: 0.75,
    y: 1.58,
    w: 9.0,
    h: 0.6,
    fontFace: FONTS.display,
    fontSize: 36,
    color: COLORS.ink,
  });

  const features = [
    "Unified portfolio dashboard",
    "Watchlists + threshold alerts",
    "Risk analytics",
    "Monthly reporting export",
    "Paid subscription entitlements",
  ];

  features.forEach((f, i) => {
    const x = i < 3 ? 0.75 + i * 4.02 : 2.75 + (i - 3) * 4.02;
    const y = i < 3 ? 2.55 : 4.48;
    s.addShape(pptx.ShapeType.roundRect, {
      x,
      y,
      w: 3.65,
      h: 1.45,
      fill: { color: COLORS.white },
      line: { color: COLORS.line, pt: 1 },
      radius: 0.08,
    });
    s.addText(`${i + 1}`, {
      x: x + 0.22,
      y: y + 0.2,
      w: 0.5,
      h: 0.35,
      fontFace: FONTS.sans,
      fontSize: 20,
      bold: true,
      color: COLORS.accentA,
    });
    s.addText(f, {
      x: x + 0.72,
      y: y + 0.2,
      w: 2.8,
      h: 0.9,
      fontFace: FONTS.sans,
      fontSize: 16,
      bold: true,
      color: COLORS.ink,
      breakLine: true,
    });
  });

  addBrand(s);
}

function addBusinessModel() {
  const s = pptx.addSlide();
  addDecor(s);
  addSectionHeader(s, "Business Model", 6);

  s.addText("$10 / month SaaS with retention-first economics", {
    x: 0.75,
    y: 1.58,
    w: 11.0,
    h: 0.6,
    fontFace: FONTS.display,
    fontSize: 35,
    color: COLORS.ink,
  });

  const cards = [
    { title: "12-Month Validation", value: "2,000 paid users", note: "$20,000 MRR" },
    { title: "Scale Scenario", value: "100,000 paid users", note: "$1,000,000 MRR" },
    { title: "Model Discipline", value: "Paid-first onboarding", note: "higher quality signal" },
  ];

  cards.forEach((c, i) => {
    const x = 0.75 + i * 4.02;
    s.addShape(pptx.ShapeType.roundRect, {
      x,
      y: 2.62,
      w: 3.65,
      h: 2.75,
      fill: { color: COLORS.white },
      line: { color: COLORS.line, pt: 1 },
      radius: 0.08,
    });
    s.addShape(pptx.ShapeType.rect, {
      x,
      y: 2.62,
      w: 3.65,
      h: 0.16,
      fill: { color: i === 0 ? COLORS.accentA : i === 1 ? COLORS.accentB : COLORS.accentC },
      line: { color: i === 0 ? COLORS.accentA : i === 1 ? COLORS.accentB : COLORS.accentC },
    });
    s.addText(c.title, {
      x: x + 0.18,
      y: 2.88,
      w: 3.2,
      h: 0.28,
      fontFace: FONTS.sans,
      fontSize: 13,
      bold: true,
      color: COLORS.muted,
    });
    s.addText(c.value, {
      x: x + 0.18,
      y: 3.3,
      w: 3.2,
      h: 0.55,
      fontFace: FONTS.sans,
      fontSize: 27,
      bold: true,
      color: COLORS.ink,
      breakLine: true,
    });
    s.addText(c.note, {
      x: x + 0.18,
      y: 4.62,
      w: 3.2,
      h: 0.3,
      fontFace: FONTS.sans,
      fontSize: 14,
      bold: true,
      color: COLORS.ink,
    });
  });

  addBrand(s);
}

function addCompetition() {
  const s = pptx.addSlide();
  addDecor(s);
  addSectionHeader(s, "Competition & Positioning", 7);

  s.addText("We are the investor decision layer.", {
    x: 0.75,
    y: 1.58,
    w: 8.3,
    h: 0.6,
    fontFace: FONTS.display,
    fontSize: 36,
    color: COLORS.ink,
  });

  addImageBlock(s, IMG_STACK, 7.95, 1.58, 4.3, 2.4);

  const rows = [
    ["Broad finance apps", "High aggregation", "Low actionability"],
    ["Broker ecosystems", "Execution-centric", "Limited neutrality"],
    ["MarketState", "Goal + risk + alerts", "Decision clarity"],
  ];

  rows.forEach((r, i) => {
    const y = 4.22 + i * 0.72;
    s.addShape(pptx.ShapeType.roundRect, {
      x: 0.75,
      y,
      w: 11.5,
      h: 0.58,
      fill: { color: i === 2 ? "EAF5FF" : COLORS.white },
      line: { color: COLORS.line, pt: 1 },
      radius: 0.04,
    });
    s.addText(r[0], {
      x: 1.0,
      y: y + 0.15,
      w: 3.3,
      h: 0.25,
      fontFace: FONTS.sans,
      fontSize: 13,
      bold: i === 2,
      color: COLORS.ink,
    });
    s.addText(r[1], {
      x: 4.55,
      y: y + 0.15,
      w: 3.2,
      h: 0.25,
      fontFace: FONTS.sans,
      fontSize: 13,
      color: COLORS.ink,
      bold: i === 2,
    });
    s.addText(r[2], {
      x: 8.0,
      y: y + 0.15,
      w: 3.95,
      h: 0.25,
      fontFace: FONTS.sans,
      fontSize: 13,
      color: COLORS.ink,
      bold: i === 2,
    });
  });

  addBrand(s);
}

function addGtm() {
  const s = pptx.addSlide();
  addDecor(s);
  addSectionHeader(s, "Go-To-Market", 8);

  s.addText("Channel focus + weekly execution rhythm", {
    x: 0.75,
    y: 1.58,
    w: 9.0,
    h: 0.6,
    fontFace: FONTS.display,
    fontSize: 35,
    color: COLORS.ink,
  });

  const steps = [
    { label: "Audience", text: "Reddit + X finance communities" },
    { label: "Offer", text: "Paid beta for high-signal feedback" },
    { label: "Loop", text: "Content, demos, interviews, testimonials" },
    { label: "Scale", text: "Double down on channels with best CAC" },
  ];

  steps.forEach((st, i) => {
    const x = 0.85 + i * 3.05;
    s.addShape(pptx.ShapeType.roundRect, {
      x,
      y: 2.75,
      w: 2.78,
      h: 2.95,
      fill: { color: COLORS.white },
      line: { color: COLORS.line, pt: 1 },
      radius: 0.08,
    });
    s.addText(st.label, {
      x: x + 0.2,
      y: 3.0,
      w: 2.3,
      h: 0.35,
      fontFace: FONTS.sans,
      fontSize: 16,
      bold: true,
      color: COLORS.ink,
      align: "center",
    });
    s.addText(st.text, {
      x: x + 0.2,
      y: 3.42,
      w: 2.35,
      h: 1.7,
      fontFace: FONTS.sans,
      fontSize: 13,
      color: COLORS.ink,
      breakLine: true,
      align: "center",
      lineSpacingMultiple: 1.2,
    });
    if (i < 3) {
      s.addShape(pptx.ShapeType.line, {
        x: x + 2.82,
        y: 4.15,
        w: 0.18,
        h: 0,
        line: { color: COLORS.line, pt: 2 },
      });
    }
  });

  addBrand(s);
}

function addTeam() {
  const s = pptx.addSlide();
  addDecor(s);
  addSectionHeader(s, "Team & Execution", 9);

  s.addText("Four specialists. Clear ownership.", {
    x: 0.75,
    y: 1.58,
    w: 8.8,
    h: 0.6,
    fontFace: FONTS.display,
    fontSize: 35,
    color: COLORS.ink,
  });

  const roles = [
    "Frontend Product\n(activation + UX)",
    "Backend Product\n(auth + APIs)",
    "Data / Quant\n(ingestion + risk)",
    "Platform / SRE\n(reliability + security)",
  ];

  roles.forEach((r, i) => {
    const x = 0.85 + i * 3.05;
    s.addShape(pptx.ShapeType.roundRect, {
      x,
      y: 2.7,
      w: 2.78,
      h: 3.15,
      fill: { color: COLORS.white },
      line: { color: COLORS.line, pt: 1 },
      radius: 0.08,
    });
    s.addShape(pptx.ShapeType.ellipse, {
      x: x + 0.96,
      y: 2.98,
      w: 0.85,
      h: 0.85,
      fill: { color: i % 2 === 0 ? "DDEEFF" : "DDF7F2" },
      line: { color: COLORS.line, pt: 1 },
    });
    s.addText(r, {
      x: x + 0.2,
      y: 4.02,
      w: 2.35,
      h: 1.55,
      fontFace: FONTS.sans,
      fontSize: 14,
      bold: true,
      color: COLORS.ink,
      breakLine: true,
      align: "center",
      lineSpacingMultiple: 1.2,
    });
  });

  addBrand(s);
}

function addAsk() {
  const s = pptx.addSlide();
  addDecor(s);
  addSectionHeader(s, "Funding Ask", 10);

  s.addText("Raise to prove repeatable paid traction.", {
    x: 0.75,
    y: 1.58,
    w: 9.6,
    h: 0.7,
    fontFace: FONTS.display,
    fontSize: 40,
    color: COLORS.ink,
  });

  addTextCallout(
    s,
    0.75,
    2.6,
    5.7,
    3.2,
    "Use of funds\n\n• Product completion\n• Data reliability\n• GTM experiments\n• Security baseline"
  );
  addTextCallout(
    s,
    6.75,
    2.6,
    5.5,
    3.2,
    "Next milestones\n\n• Paid beta launch\n• Conversion baseline\n• Early retention proof\n• Investor update cycle"
  );

  s.addText("Contact: contact@marketstate", {
    x: 0.75,
    y: 6.05,
    w: 6.5,
    h: 0.35,
    fontFace: FONTS.sans,
    fontSize: 15,
    bold: true,
    color: COLORS.ink,
  });

  addBrand(s);
}

addCover();
addProblem();
addSolution();
addMarket();
addMvp();
addBusinessModel();
addCompetition();
addGtm();
addTeam();
addAsk();

pptx.writeFile({ fileName: "MarketState_MVP_Pitch_Deck_Pizazz_v3.pptx" });

