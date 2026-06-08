"""
Drishti Law Enforcement Agency (LEA) Escalation Template Generator.
Generates Indian Cyber Crime FIR drafts (IT Act 2000), INTERPOL notices, CERT-In reports,
and hosting takedown letters, exporting as rich Markdown and PDFs.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

logger = logging.getLogger(__name__)

class EscalationGenerator:
    """Generates official agency notification reports, complaint forms, and takedown letters."""

    def __init__(self, output_dir: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.output_dir = output_dir or os.path.join(base_dir, "outputs", "reports")
        os.makedirs(self.output_dir, exist_ok=True)

    def _render_pdf(self, title: str, subtitle: str, content_blocks: list, output_filename: str) -> str:
        """Helper to render content blocks into a professional PDF layout using ReportLab."""
        filepath = os.path.join(self.output_dir, output_filename)
        if not REPORTLAB_AVAILABLE:
            logger.warning("ReportLab not available. PDF export skipped.")
            return ""

        try:
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'DocTitle',
                parent=styles['Heading1'],
                textColor=colors.HexColor('#002884'),
                spaceAfter=5,
                alignment=1
            )
            sub_style = ParagraphStyle(
                'DocSub',
                parent=styles['Normal'],
                fontSize=8,
                leading=10,
                textColor=colors.HexColor('#3f51b5'),
                spaceAfter=15,
                alignment=1
            )
            h2_style = ParagraphStyle(
                'DocH2',
                parent=styles['Heading2'],
                textColor=colors.HexColor('#b71c1c'),
                spaceBefore=10,
                spaceAfter=5
            )
            body_style = ParagraphStyle(
                'DocBody',
                parent=styles['Normal'],
                fontSize=9,
                leading=13,
                spaceAfter=6
            )

            story = []
            story.append(Paragraph(f"<b>{title}</b>", title_style))
            story.append(Paragraph(f"<i>{subtitle}</i>", sub_style))
            story.append(Spacer(1, 10))

            for block in content_blocks:
                b_type = block.get("type", "body")
                b_text = block.get("text", "")
                
                if b_type == "h2":
                    story.append(Paragraph(f"<b>{b_text}</b>", h2_style))
                elif b_type == "spacer":
                    story.append(Spacer(1, block.get("size", 10)))
                elif b_type == "table":
                    t_data = []
                    for row in block.get("data", []):
                        t_row = [Paragraph(str(cell), body_style) for cell in row]
                        t_data.append(t_row)
                    
                    t = Table(t_data, colWidths=block.get("col_widths", [120, 360]))
                    t.setStyle(TableStyle([
                        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#e8eaf6')),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('PADDING', (0,0), (-1,-1), 5),
                    ]))
                    story.append(t)
                else:
                    story.append(Paragraph(b_text.replace("\n", "<br/>"), body_style))

            doc.build(story)
            logger.info(f"Escalation report PDF rendered successfully: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error rendering escalation PDF: {e}", exc_info=True)
            return ""

    def generate_fir_complaint(self, investigation_report: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate a detailed First Information Report (FIR) complaint draft.
        Violations mapped to IT Act 2000 Sections 66C, 66D, 67, 67B.
        """
        query = investigation_report.get("query", "Unknown OSINT Scan")
        summary = investigation_report.get("summary", "No details available.")
        artifacts = investigation_report.get("artifacts", {})
        
        # Formulate applied legal sections
        sections = ["Section 66 (Computer related offences)"]
        if "identity" in query.lower() or "passport" in query.lower() or "credentials" in query.lower():
            sections.append("Section 66C (Punishment for identity theft)")
            sections.append("Section 66D (Punishment for cheating by personation by using computer resource)")
        if "drug" in query.lower() or "expl" in query.lower() or "contraband" in query.lower():
            sections.append("Section 67 (Punishment for publishing or transmitting obscene material in electronic form)")

        sections_str = ", ".join(sections)
        time_str = datetime.now(timezone.utc).strftime("%d/%m/%Y, %H:%M:%S UTC")

        # Flat artifacts list
        flat_iocs = []
        for src, types in artifacts.items():
            for t, vals in types.items():
                for val in vals:
                    flat_iocs.append(f"{t.upper()}: {val} (extracted from source: {src})")
        
        flat_iocs_str = "\n".join(f"- {ioc}" for ioc in flat_iocs[:10])

        md_content = f"""# DRAFT COMPLAINT FOR FIRST INFORMATION REPORT (FIR)
**Subject:** Technical Complaint against Dark Web threat/illegal activity matching: "{query}"  
**Advisory Agency:** Central Cyber Crime Cell, India  
**Date of Filing:** {datetime.now(timezone.utc).strftime("%d/%m/%Y")}  
**Incident Reference:** DRISHTI-FIR-{int(datetime.now().timestamp())}  

---

## 1. COMPLAINT DETAILS
- **Complainant:** Cyber Intelligence & Security Architect, Drishti OSINT Platform
- **Addressed To:** Station House Officer (SHO), Cyber Crime Police Station
- **Date & Time of Detection:** {time_str}
- **Applicable Statutes:** Information Technology (IT) Act, 2000 ({sections_str})

---

## 2. NATURE & SUMMARY OF THE OFFENSE
An automated OSINT investigation run by the Drishti Dark Web Monitoring tool detected high-severity malicious operations.
Brief investigative summary of findings:
{summary}

---

## 3. IDENTIFIED DIGITAL INDICES / EVIDENCE (IOCS)
The following indicators of compromise and illegal transactional addresses were captured:
{flat_iocs_str or "- No specific indicators recorded."}

---

## 4. LEGAL SUBMISSION / REQUEST FOR ACTION
Based on the immutable forensic evidence retrieved and sealed (pursuant to Section 65B of the Indian Evidence Act, 1872), it is requested that:
1. An First Information Report (FIR) be registered under the aforementioned sections of the IT Act, 2000.
2. A formal investigation be initiated to locate and apprehend the perpetrators.
3. Steps be taken to coordinate with global partners to issue takedown/preservation requests.

---
**Signature of Filing Investigator:**  
____________________________________  
*(Cyber Crime OSINT Analyst, Drishti platform)*
"""

        # Generate files
        ref_id = int(datetime.now().timestamp())
        md_filename = f"fir_draft_{ref_id}.md"
        pdf_filename = f"fir_draft_{ref_id}.pdf"
        
        md_path = os.path.join(self.output_dir, md_filename)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # PDF Blocks
        blocks = [
            {"type": "body", "text": "<b>ADDRESSED TO:</b> The Station House Officer (SHO), Cyber Crime Police Station"},
            {"type": "body", "text": f"<b>DATE & TIME OF DISCOVERY:</b> {time_str}"},
            {"type": "body", "text": f"<b>APPLICABLE STATUTES:</b> Information Technology (IT) Act 2000 ({sections_str})"},
            {"type": "spacer", "size": 10},
            {"type": "h2", "text": "1. INVESTIGATIVE STATEMENT"},
            {"type": "body", "text": summary},
            {"type": "spacer", "size": 10},
            {"type": "h2", "text": "2. DIGITALLY EXTRACTED FORENSIC INDICATORS (IOCs)"},
            {"type": "body", "text": flat_iocs_str or "No indicators extracted."},
            {"type": "spacer", "size": 15},
            {"type": "body", "text": "<b>LEGAL DECLARATION:</b> The technical findings above have been gathered inside a secure sandbox with continuous SOCKS5 anonymization, and hashes are anchored to the local system and Polygon blockchain registers under Section 65B of the Indian Evidence Act, 1872."}
        ]
        
        pdf_path = self._render_pdf(
            "COMPLAINT FOR FIRST INFORMATION REPORT (FIR)",
            f"Filing Reference: DRISHTI-FIR-{ref_id} | India Cyber Portal Portal",
            blocks,
            pdf_filename
        )

        return {
            "markdown_path": md_path,
            "pdf_path": pdf_path or "N/A (Reportlab disabled)"
        }

    def generate_interpol_notice(self, actor_profile: Dict[str, Any]) -> Dict[str, str]:
        """Generate a formatted draft for an INTERPOL Diffusion / Red Notice threat briefing."""
        ref_id = int(datetime.now().timestamp())
        name = actor_profile.get("primary_handle", "Unknown Actor")
        aliases_str = ", ".join(actor_profile.get("linked_pseudonyms", []))
        
        # Group artifacts
        flat_iocs = []
        for t, vals in actor_profile.get("linked_iocs", {}).items():
            for val in vals:
                flat_iocs.append(f"{t.upper()}: {val}")
        
        flat_iocs_str = "\n".join(f"- {ioc}" for ioc in flat_iocs[:10])

        md_content = f"""# DRAFT BRIEFING FOR INTERPOL NOTICE / DIFFUSION
**Classification:** Restricted LEA Intelligence  
**Target Subject:** Threat Actor Profile: "{name}"  
**Subject Aliases:** {aliases_str}  
**Assessed Threat Level:** {actor_profile.get('threat_level', 50)} / 100  
**Notice Reference:** DRISHTI-IPOL-{ref_id}  

---

## 1. SUBJECT BIO & WRITING FOOTPRINTS
- **Primary Handle / Avatar:** {name}
- **Affiliated Forums / Marketplaces:** Darknet Markets, Forums
- **Heuristic Writing Style Attributes:**
  - Average Sentence Length: {actor_profile.get('writing_style', {}).get('avg_sentence_length', 'N/A')} words
  - Key Phrase Footprints: {', '.join(actor_profile.get('writing_style', {}).get('common_phrases', [])) or 'None'}

---

## 2. KNOWN DIGITAL TRAILS & TRANSACTION TRAILS
The subject is actively associated with the following indicators of compromise:
{flat_iocs_str or "- No linked crypto addresses or emails recorded."}

---

## 3. ASSESSED MITRE ATT&CK TACTICS (TTPs)
The following malicious techniques are utilized by this subject:
{', '.join(actor_profile.get('ttp_tags', [])) or 'None'}

---
**Compiled by Central Cyber Forensics, India**  
*Verification sealed via Drishti Cryptographic Registry.*
"""

        md_filename = f"interpol_diffusion_{ref_id}.md"
        pdf_filename = f"interpol_diffusion_{ref_id}.pdf"
        
        md_path = os.path.join(self.output_dir, md_filename)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # PDF Blocks
        blocks = [
            {"type": "body", "text": f"<b>TARGET SUBJECT HANDLE:</b> {name}"},
            {"type": "body", "text": f"<b>KNOWN ALIASES / IDENTITIES:</b> {aliases_str}"},
            {"type": "body", "text": f"<b>THREAT LEVEL ASSESSMENT:</b> {actor_profile.get('threat_level', 50)} / 100"},
            {"type": "spacer", "size": 10},
            {"type": "h2", "text": "1. PROFILE SUMMARY"},
            {"type": "body", "text": f"Subject is a cyberthreat actor classified under Drishti OSINT monitoring. Writing style metrics indicate an average sentence length of {actor_profile.get('writing_style', {}).get('avg_sentence_length', 'N/A')} words per post."},
            {"type": "spacer", "size": 10},
            {"type": "h2", "text": "2. IDENTIFIED CRYPTOCURRENCY & DIGITAL TRAILS"},
            {"type": "body", "text": flat_iocs_str or "No digital trails indexed."},
            {"type": "spacer", "size": 10},
            {"type": "h2", "text": "3. ASSOCIATED MITRE ATT&CK TECHNIQUES"},
            {"type": "body", "text": ", ".join(actor_profile.get("ttp_tags", [])) or "No mapped techniques."}
        ]

        pdf_path = self._render_pdf(
            "INTERPOL DIFFUSION BRIEFING DRAFT",
            f"Filing Reference: DRISHTI-IPOL-{ref_id} | RESTRICTED LEA",
            blocks,
            pdf_filename
        )

        return {
            "markdown_path": md_path,
            "pdf_path": pdf_path or "N/A"
        }

    def generate_cert_in_report(self, investigation_report: Dict[str, Any]) -> Dict[str, str]:
        """Generate a CERT-In Incident Reporting Form complaint document."""
        ref_id = int(datetime.now().timestamp())
        query = investigation_report.get("query", "Unknown OSINT Scan")
        summary = investigation_report.get("summary", "No details.")
        
        md_content = f"""# CERT-In INCIDENT REPORTING COMPLAINT FORM
**To:** Indian Computer Emergency Response Team (CERT-In)  
**Filing Date:** {datetime.now(timezone.utc).strftime("%d/%m/%Y, %H:%M:%S UTC")}  
**Incident Reference:** DRISHTI-CERTIN-{ref_id}  

---

## 1. INCIDENT DESCRIPTION & TARGET DETAILS
- **Type of Incident:** Dark Web threat / database leak / network vulnerability
- **Target Organization / Sector:** Indian Government / Critical Infrastructure / Financial Sector (assessed)
- **Source Platform / Onion Link:** Mapped onion sources
- **Impact Assessment:** Risk of identity theft, database breaches, or credential leaks

---

## 2. DETAILS OF INCIDENT / THREAT ANALYSIS
{summary}

---

## 3. REMEDIAL ACTION RECOMMENDED
1. Monitor registered domains for spoofing.
2. Force credential rotation for affected corporate emails.
3. Ingest extracted IOCs into local SIEM (Splunk/Sentinel) firewall lists.

---
**Report compiled via Drishti Threat Intelligence Engine**  
*Central Forensics Unit, Govt of India*
"""

        md_filename = f"certin_report_{ref_id}.md"
        pdf_filename = f"certin_report_{ref_id}.pdf"
        
        md_path = os.path.join(self.output_dir, md_filename)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # PDF Blocks
        blocks = [
            {"type": "body", "text": f"<b>REPORTING AGENCY:</b> Central Forensics Unit, Drishti Cyber Center"},
            {"type": "body", "text": f"<b>INCIDENT CLASSIFICATION:</b> Dark Web Leak / Attack Planning Monitoring"},
            {"type": "spacer", "size": 10},
            {"type": "h2", "text": "1. THREAT INTELLIGENCE SUMMARY"},
            {"type": "body", "text": summary},
            {"type": "spacer", "size": 10},
            {"type": "h2", "text": "2. ADVISORY MITIGATION STEPS"},
            {"type": "body", "text": "1. Block identified threat domains on all network firewalls.\n2. Enable security monitoring on linked corporate domains.\n3. Log hash seals on all incident files."}
        ]

        pdf_path = self._render_pdf(
            "CERT-In INCIDENT REPORTING ADVISORY",
            f"Filing Reference: DRISHTI-CERTIN-{ref_id}",
            blocks,
            pdf_filename
        )

        return {
            "markdown_path": md_path,
            "pdf_path": pdf_path or "N/A"
        }

    def generate_takedown_request(self, source_url: str, evidence_summary: str) -> Dict[str, str]:
        """Generate a formal Abuse Takedown Request letter for registrars / hosting providers."""
        ref_id = int(datetime.now().timestamp())
        
        md_content = f"""# ABUSE TAKEDOWN REQUEST / CEASE & DESIST LETTER
**To:** Abuse Department / Domain Registrar  
**Date:** {datetime.now(timezone.utc).strftime("%d/%m/%Y")}  
**Filing Reference:** DRISHTI-TAKEDOWN-{ref_id}  

---

Dear Abuse Officer,

I am writing to you on behalf of the Central Cyber Forensics division of Drishti. It has come to our attention that one of your hosted services/domains is actively involved in illegal activities violating terms of service and global laws.

- **Infringing Target URL:** {source_url}
- **Nature of Abuse:** Sale of stolen Indian PII, counterfeit documents, or attack orchestration
- **Evidence summary:**
{evidence_summary}

We request that you immediately **suspend hosting services** and **lock domain registration** for the aforementioned URL to prevent further cybercrime damage. Furthermore, please preserve all logs, access metrics, and billing records for law enforcement agencies.

Thank you for your prompt cooperation.

Sincerely,  
**Chief Cyber Threat Investigator**  
*Central Forensics Unit, Govt of India*
"""

        md_filename = f"takedown_abuse_{ref_id}.md"
        pdf_filename = f"takedown_abuse_{ref_id}.pdf"
        
        md_path = os.path.join(self.output_dir, md_filename)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # PDF Blocks
        blocks = [
            {"type": "body", "text": f"<b>ABUSE SOURCE URL:</b> {source_url}"},
            {"type": "spacer", "size": 10},
            {"type": "body", "text": "Dear Abuse Officer,\n\nWe request the immediate suspension of domain registration and hosting capabilities for the target server listed above. Forensic intelligence scans show that this platform is actively hosting illegal threat marketplaces or illicit material violating global computer safety standards."},
            {"type": "spacer", "size": 10},
            {"type": "h2", "text": "INVESTIGATION FINDINGS EVIDENCE SUMMARY"},
            {"type": "body", "text": evidence_summary},
            {"type": "spacer", "size": 15},
            {"type": "body", "text": "<b>IMPORTANT NOTICE:</b> Please preserve all routing, billing, login, and registration records linked to this account for further agency analysis and court prosecutions."}
        ]

        pdf_path = self._render_pdf(
            "FORMAL ABUSE TAKEDOWN REQUEST",
            f"Filing Reference: DRISHTI-TAKEDOWN-{ref_id}",
            blocks,
            pdf_filename
        )

        return {
            "markdown_path": md_path,
            "pdf_path": pdf_path or "N/A"
        }
