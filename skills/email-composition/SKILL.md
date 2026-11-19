---
name: email-composition
description: Prepare a professional manager email draft with a PDF sales report attached, without sending the email.
requires: sales-analysis, report-generation
---

# Email Composition

## Purpose

Prepare a concise, professional email draft for a manager that summarizes sales results and identifies the generated PDF report as an attachment.

## When to Use This Skill

Use this skill after a sales report PDF has been generated and the sales summary is available.

## Input Requirements

- The generated PDF report file path.
- A sales summary containing:
  - Total revenue.
  - Total quantity sold.
  - Highest-performing product.
  - Lowest-performing product.
  - Key business insights.
- Optional manager name or recipient name.
- Optional reporting period.

## Step-by-Step Instructions

1. Confirm that the PDF report file path is available.
2. Create a clear, professional subject line describing the sales report.
3. Address the manager appropriately.
4. Briefly summarize the overall sales result.
5. Mention the highest-performing product and lowest-performing product if available.
6. Highlight one or two important business insights.
7. Explain that the PDF report is attached to the email.
8. Include the attachment path exactly in the draft metadata or attachment section.
9. End with a concise professional closing.
10. Prepare the complete draft without invoking any email service.

## Expected Output

Provide an email draft containing:

- A subject line.
- A professional email body.
- The report attachment path.
- A clear indication that the message is a draft.

Example structure:

- Subject: Sales Performance Report
- Body: Greeting, sales summary, key insights, attachment statement, and closing.
- Attachment: `outputs/sales_report.pdf`

## Execution Guidance

- This skill only prepares a draft; it must not send, schedule, or deliver emails.
- Do not include a fake recipient address unless one is explicitly provided.
- Do not imply that the email has already been sent.
- Keep the subject and body concise, factual, and professional.
- Use the sales summary and PDF report supplied by earlier skills.
- Do not create or execute Gmail, SMTP, or other email integrations.
