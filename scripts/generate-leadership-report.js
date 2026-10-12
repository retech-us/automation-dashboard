#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const {
  AlignmentType,
  BorderStyle,
  Document,
  HeadingLevel,
  Packer,
  Paragraph,
  ShadingType,
  Table,
  TableCell,
  TableRow,
  TextRun,
  WidthType,
} = require('docx');

const [format, inputFile, outputFile] = process.argv.slice(2);
if (format !== 'docx' || !inputFile || !outputFile) {
  console.error('Usage: generate-leadership-report.js docx <input.json> <output>');
  process.exit(2);
}

const brief = JSON.parse(fs.readFileSync(inputFile, 'utf8'));
const clean = (value, fallback = 'Not available') => {
  const text = String(value ?? '').replace(/&/g, 'and').replace(/\s+/g, ' ').trim();
  return text || fallback;
};
const sentenceLabel = (value) => {
  const text = clean(value).replace(/[-_]+/g, ' ');
  if (text === text.toUpperCase()) return `${text.charAt(0)}${text.slice(1).toLowerCase()}`;
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}`;
};
const bulletText = (value) => clean(value).replace(/\.+$/, '');
const generatedDate = brief.generated_at
  ? new Date(brief.generated_at).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })
  : new Date().toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });

const COLORS = {
  blue: '0074E8',
  teal: '00EAC3',
  pink: 'FB24A9',
  orange: 'FF8500',
  ink: '121212',
  white: 'FFFFFF',
  line: 'DEDEDF',
  mist: 'F7F7F8',
};

async function createDocx() {
  const border = { style: BorderStyle.SINGLE, size: 4, color: COLORS.line };
  const bodySpacing = { after: 160, line: 380, lineRule: 'exact' };
  const cell = (text, width, options = {}) => new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: options.fill || COLORS.white },
    borders: { top: border, bottom: border, left: border, right: border },
    margins: { top: 120, bottom: 120, left: 140, right: 140 },
    children: [new Paragraph({
      spacing: { line: 380, lineRule: 'exact' },
      children: [new TextRun({
        text: clean(text),
        bold: Boolean(options.bold),
        color: options.color || COLORS.ink,
        font: 'Arial',
        size: 28,
      })],
    })],
  });

  const children = [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 900, after: 220 },
      children: [new TextRun({ text: sentenceLabel(brief.title), bold: true, color: COLORS.ink, font: 'Arial', size: 56 })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 400, line: 420, lineRule: 'exact' },
      children: [new TextRun({ text: `${clean(brief.context)} · Leadership briefing · ${generatedDate}`, color: COLORS.blue, font: 'Arial', size: 28 })],
    }),
    new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [3120, 3120, 3120],
      rows: [
        new TableRow({
          children: [
            cell(`Verdict: ${sentenceLabel(brief.verdict)}`, 3120, { bold: true, fill: COLORS.mist }),
            cell(`Confidence: ${sentenceLabel(brief.confidence)}`, 3120, { fill: COLORS.mist }),
            cell(`Context: ${clean(brief.context)}`, 3120, { fill: COLORS.mist }),
          ],
        }),
      ],
    }),
    new Paragraph({ text: 'Executive summary', heading: HeadingLevel.HEADING_1, spacing: { before: 500, after: 160 } }),
    new Paragraph({ text: clean(brief.executive_summary), spacing: bodySpacing }),
    new Paragraph({
      spacing: bodySpacing,
      children: [
        new TextRun({ text: 'Leadership question: ', bold: true, color: COLORS.blue, font: 'Arial', size: 28 }),
        new TextRun({ text: clean(brief.question), font: 'Arial', size: 28, color: COLORS.ink }),
      ],
    }),
  ];

  if (brief.metrics?.length) {
    children.push(new Paragraph({ text: 'Key metrics', heading: HeadingLevel.HEADING_1, spacing: { before: 420, after: 160 } }));
    children.push(new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [6240, 3120],
      rows: [
        new TableRow({
          children: [
            cell('Metric', 6240, { bold: true, color: COLORS.white, fill: COLORS.ink }),
            cell('Value', 3120, { bold: true, color: COLORS.white, fill: COLORS.ink }),
          ],
        }),
        ...brief.metrics.map((metric, index) => new TableRow({
          children: [
            cell(metric.label, 6240, { fill: index % 2 ? COLORS.mist : COLORS.white }),
            cell(metric.value, 3120, { bold: true, fill: index % 2 ? COLORS.mist : COLORS.white }),
          ],
        })),
      ],
    }));
  }

  children.push(new Paragraph({ text: 'Evidence and findings', heading: HeadingLevel.HEADING_1, spacing: { before: 420, after: 160 } }));
  if (!brief.findings.length) {
    children.push(new Paragraph({ text: 'No detailed findings were returned for this analysis.' }));
  }
  brief.findings.forEach((finding, index) => {
    children.push(new Paragraph({
      spacing: { before: 220, after: 80 },
      children: [
        new TextRun({
          text: `${index + 1}. ${clean(finding.title)}`,
          bold: true,
          color: finding.severity === 'critical' ? COLORS.pink : finding.severity === 'warning' ? COLORS.orange : COLORS.blue,
          font: 'Arial',
          size: 28,
        }),
      ],
    }));
    children.push(new Paragraph({ text: clean(finding.detail), spacing: bodySpacing }));
    if (finding.evidence?.length) {
      children.push(new Paragraph({
        spacing: bodySpacing,
        children: [new TextRun({
          text: `Evidence: ${finding.evidence.map((item) => `${clean(item.source)}: ${clean(JSON.stringify(item.value))}`).join(' · ')}`,
          color: COLORS.ink,
          font: 'Arial',
          size: 28,
        })],
      }));
    }
  });

  children.push(new Paragraph({ text: 'Recommended leadership actions', heading: HeadingLevel.HEADING_1, spacing: { before: 420, after: 160 } }));
  const recommendations = brief.recommendations.length
    ? brief.recommendations
    : ['No escalation or leadership action was recommended by the available evidence'];
  recommendations.forEach((item) => children.push(new Paragraph({
    text: bulletText(item),
    bullet: { level: 0 },
    spacing: bodySpacing,
  })));

  children.push(
    new Paragraph({ text: 'Sources and traceability', heading: HeadingLevel.HEADING_1, spacing: { before: 420, after: 160 } }),
    new Paragraph({ text: brief.sources.map((item) => clean(item)).join(' · ') || 'No source labels were returned.', spacing: bodySpacing }),
    new Paragraph({
      spacing: bodySpacing,
      children: [new TextRun({ text: `Agent run: ${clean(brief.run_id, 'not available')}`, color: COLORS.ink, font: 'Arial', size: 28 })],
    }),
  );

  const doc = new Document({
    creator: 'SymphonyAI',
    title: sentenceLabel(brief.title),
    description: 'SymphonyAI leadership report generated from grounded dashboard analysis',
    styles: {
      default: { document: { run: { font: 'Arial', size: 28, color: COLORS.ink } } },
      paragraphStyles: [
        {
          id: 'Heading1',
          name: 'Heading 1',
          basedOn: 'Normal',
          next: 'Normal',
          quickFormat: true,
          run: { font: 'Arial', size: 32, bold: true, color: COLORS.blue },
          paragraph: { spacing: { before: 360, after: 160, line: 420, lineRule: 'exact' }, outlineLevel: 0 },
        },
      ],
    },
    sections: [{
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 900, right: 900, bottom: 900, left: 900 },
        },
      },
      headers: {},
      children,
    }],
  });
  fs.writeFileSync(outputFile, await Packer.toBuffer(doc));
}

(async () => {
  fs.mkdirSync(path.dirname(outputFile), { recursive: true });
  await createDocx();
})().catch((error) => {
  console.error(error?.stack || String(error));
  process.exit(1);
});
