# Consistency audit

Generated on 2 Nov 2026 from `role-records.json`. Compared: Confirmed by the person (6 records), Official form (signed Aug 2019) (2 records), CV (6 records), LinkedIn (6 records), Website (2 records).

**4 high, 9 medium, 1 low.** Fix the high ones first: a raised title, a role nobody else lists or a claim the person denies reads as dishonesty to a recruiter or a background check.

## Suggested single source of truth

Use these values everywhere. Each one comes from the most trusted source that has it (Confirmed by the person, then Official form (signed Aug 2019), then CV, then LinkedIn, then Website). Where titles disagree and the person has not confirmed one, the more modest title is suggested. Check every line marked **confirm** with the person, against a document if possible.

| Role | Organisation | Title | Start | End | Taken from | |
|---|---|---|---|---|---|---|
| R01 | Example University | Bachelor of Science | 2001 | 2004 | Confirmed by the person |  |
| R02 | Fabrikam Air | Quality Officer | Feb 2005 | Jun 2008 | Confirmed by the person |  |
| R03 | Fabrikam Air | Deputy Quality Manager | Jul 2008 | Mar 2012 | Confirmed by the person |  |
| R04 | Northwind Consulting | Founder | Jan 2013 | Dec 2015 | Confirmed by the person |  |
| R05 | Woodgrove Bank | Operations Analyst | Jan 2016 | Aug 2019 | Confirmed by the person |  |
| R06 | Adventure Works | Advisory Board Member | 2018 | 2019 | LinkedIn | **confirm** |
| R07 | Tailspin Robotics | Program Manager | Sep 2019 | present | Confirmed by the person |  |

## Findings

### High

- **F01 Likely title inflation, R03.** Fabrikam Air: Confirmed by the person, Official form (signed Aug 2019) and CV say "Deputy Quality Manager"; LinkedIn says "Quality Manager". Likely inflation: "Quality Manager" leaves out "Deputy" (from "Deputy Quality Manager").
- **F02 Claim the person denies, R03.** Fabrikam Air, Deputy Quality Manager: LinkedIn says "Ran the airline's external audit program", but the person says this is not true.
- **F03 Likely title inflation, R05.** Woodgrove Bank: Confirmed by the person, Official form (signed Aug 2019), CV and LinkedIn say "Operations Analyst"; Website says "Operations Lead". Likely inflation: "Operations Lead" is a seniority step above "Operations Analyst".
- **F04 Role missing, R06.** "Advisory Board Member" at Adventure Works (2018 to 2019) is in LinkedIn but not in Confirmed by the person, Official form (signed Aug 2019) and CV. Only the person's own pages list it.

### Medium

- **F05 Dates differ, R03.** Fabrikam Air, Deputy Quality Manager: the end date differs (Confirmed by the person Mar 2012; Official form (signed Aug 2019) Mar 2012; CV Mar 2012; LinkedIn May 2012); they differ by up to 2 months.
- **F06 Claim in one place only, R03.** Fabrikam Air, Deputy Quality Manager: only CV says "Prepared the quality team for three regulator audits".
- **F07 Unexplained gap, R03 and R04.** No role, study or explained break from Apr 2012 to Dec 2012 (9 months).
- **F08 Dates differ, R04.** Northwind Consulting, Founder: the end date differs (Confirmed by the person Dec 2015; CV Dec 2015; LinkedIn Mar 2016); they differ by up to 3 months.
- **F09 Role missing, R04.** "Founder" at Northwind Consulting (Jan 2013 to Dec 2015) is in Confirmed by the person, CV and LinkedIn but not in Official form (signed Aug 2019).
- **F10 Dates differ, R05.** Woodgrove Bank, Operations Analyst: the end date differs (Confirmed by the person Aug 2019; Official form (signed Aug 2019) Aug 2019; CV Dec 2019; LinkedIn Aug 2019; Website 2019); they differ by up to 4 months.
- **F11 Claim differs, R07.** Tailspin Robotics, Program Manager: the same claim has different numbers (Confirmed by the person "Cut supplier defects by 30% in 2022"; CV "Cut supplier defects by 30% in 2022"; LinkedIn "Cut supplier defects by 40% in 2022").
- **F12 Claim in one place only, R07.** Tailspin Robotics, Program Manager: only CV says "Ran a weekly risk review for 4 product teams".
- **F13 Claim in one place only, R07.** Tailspin Robotics, Program Manager: only LinkedIn says "Managed a team of 12 engineers".

### Low

- **F14 Roles overlap, R05 and R06.** "Operations Analyst" at Woodgrove Bank and "Advisory Board Member" at Adventure Works overlap for 2 months (Dec 2018 to Jan 2019), and neither is marked concurrent.

## Fixes by source

### Confirmed by the person (questions to ask)

1. R06 Adventure Works: Ask the person whether they held "Advisory Board Member" at Adventure Works (2018 to 2019), and record the answer. (F04)

### Official form (signed Aug 2019) (cannot be edited)

1. R04 Northwind Consulting: Official form (signed Aug 2019) does not list "Founder" at Northwind Consulting and cannot be edited. Be ready to explain why. (F09)

### CV

1. R03 Fabrikam Air: Keep "Prepared the quality team for three regulator audits" only if a second source backs it (a referee, a document, a press article); otherwise remove or soften it. (F06)
2. R05 Woodgrove Bank: Change the end date from Dec 2019 to Aug 2019. (F10)
3. R07 Tailspin Robotics: Keep "Ran a weekly risk review for 4 product teams" only if a second source backs it (a referee, a document, a press article); otherwise remove or soften it. (F12)

### LinkedIn

1. R03 Fabrikam Air: Change the title from "Quality Manager" to "Deputy Quality Manager". (F01)
2. R03 Fabrikam Air: Remove "Ran the airline's external audit program": the person says it is not true. (F02)
3. R06 Adventure Works: Remove "Advisory Board Member" at Adventure Works unless the person confirms it and a document backs it. (F04)
4. R03 Fabrikam Air: Change the end date from May 2012 to Mar 2012. (F05)
5. R04 Northwind Consulting: Change the end date from Mar 2016 to Dec 2015. (F08)
6. R07 Tailspin Robotics: Change the claim from "Cut supplier defects by 40% in 2022" to "Cut supplier defects by 30% in 2022". (F11)
7. R07 Tailspin Robotics: Keep "Managed a team of 12 engineers" only if a second source backs it (a referee, a document, a press article); otherwise remove or soften it. (F13)

### Website

1. R05 Woodgrove Bank: Change the title from "Operations Lead" to "Operations Analyst". (F03)

### All sources

1. R03 Fabrikam Air: Explain Apr 2012 to Dec 2012 in one line on the CV and LinkedIn (for example study, a business, travel or a career break), then add it to explained_gaps. (F07)
2. R05 Woodgrove Bank: If R05 and R06 really ran at the same time, mark them concurrent in profile/role-records.json and make that clear on the CV; otherwise fix the dates. (F14)

## Next steps

- Draft the edits with `method/PROFILE_FIXES.md`. Nothing here changes any account; the person makes every change, or asks their agent to.
- Every high finding becomes a top priority plan action.
- After a source changes, copy it again into `profile/role-records.json` and re-run the audit. Before publishing, run it with `--tolerance-months 0` so every date matches exactly.
