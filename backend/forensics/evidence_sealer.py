"""
Drishti Forensic Evidence Sealing Module.
Secures threat reports with SHA-256 hashing, SQLite seals, optional blockchain anchors,
and Section 65B Indian Evidence Act compliant PDF certificates.
"""
import sqlite3
import os
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

try:
    from backend.config import (
        DATABASE_URL, BLOCKCHAIN_ENABLED, POLYGON_RPC_URL, WALLET_PRIVATE_KEY
    )
except ModuleNotFoundError:
    try:
        from config import (
            DATABASE_URL, BLOCKCHAIN_ENABLED, POLYGON_RPC_URL, WALLET_PRIVATE_KEY
        )
    except ModuleNotFoundError:
        DATABASE_URL = None
        BLOCKCHAIN_ENABLED = False
        POLYGON_RPC_URL = WALLET_PRIVATE_KEY = None

# Safe import for Web3
try:
    from web3 import Web3
except ImportError:
    Web3 = None

# Safe import for ReportLab PDF Generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

logger = logging.getLogger(__name__)

class EvidenceSealer:
    """Handles cryptographic sealing and court-ready anchoring of investigations."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        elif DATABASE_URL and DATABASE_URL.startswith("sqlite:///"):
            self.db_path = DATABASE_URL.replace("sqlite:///", "")
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_path = os.path.join(base_dir, "data", "drishti.db")

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize evidence seals database table."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS evidence_seals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        report_id TEXT UNIQUE NOT NULL,
                        sha256_hash TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        tx_hash TEXT,
                        seal_method TEXT NOT NULL
                    )
                """)
                conn.commit()
            logger.info("Forensic Evidence Seals DB table initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Evidence Sealer DB: {e}")

    def seal_report(self, report_id: str, report_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cryptographically seal an investigation report.

        1. Serialize report to canonical JSON
        2. Hash with SHA-256
        3. Anchor to local SQLite evidence_seals table
        4. Attempt to write hash to Polygon chain if enabled
        """
        # 1. Canonical JSON serialization (sorted keys)
        canonical_str = json.dumps(report_dict, sort_keys=True, default=str)
        
        # 2. SHA-256 Hashing
        sha256_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
        time_str = datetime.now(timezone.utc).isoformat()
        
        seal_method = "local"
        tx_hash = None

        # 3. Optional Blockchain anchoring
        if BLOCKCHAIN_ENABLED and Web3 and POLYGON_RPC_URL and WALLET_PRIVATE_KEY:
            try:
                w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))
                if w3.is_connected():
                    # Set up transaction with hash in hex data
                    account = w3.eth.account.from_key(WALLET_PRIVATE_KEY)
                    sender_address = account.address
                    
                    nonce = w3.eth.get_transaction_count(sender_address)
                    gas_price = w3.eth.gas_price
                    
                    # Construct transacion writing report hash inside 'data' field
                    tx = {
                        'nonce': nonce,
                        'to': sender_address,  # Send to self
                        'value': 0,
                        'gas': 25000,
                        'gasPrice': gas_price,
                        'data': w3.to_hex(text=f"DRISHTI_SEAL:{report_id}:{sha256_hash}"),
                        'chainId': w3.eth.chain_id
                    }
                    
                    signed_tx = w3.eth.account.sign_transaction(tx, WALLET_PRIVATE_KEY)
                    tx_hash_bytes = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                    tx_hash = w3.to_hex(tx_hash_bytes)
                    seal_method = "blockchain"
                    logger.info(f"Report {report_id} anchored to Polygon blockchain. TX: {tx_hash}")
                else:
                    logger.warning("Failed to connect to Polygon RPC network. Falling back to local seal.")
            except Exception as e:
                logger.error(f"Blockchain anchoring failed: {e}. Defaulting to local-only seal.")

        # 4. Save to SQLite database
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO evidence_seals (report_id, sha256_hash, timestamp, tx_hash, seal_method)
                    VALUES (?, ?, ?, ?, ?)
                """, (report_id, sha256_hash, time_str, tx_hash, seal_method))
                conn.commit()
            logger.info(f"Recorded local forensic seal for report {report_id}.")
        except Exception as e:
            logger.error(f"Failed to record evidence seal to SQLite: {e}")

        verification_url = f"/api/forensics/verify/{report_id}"

        return {
            "report_id": report_id,
            "sha256_hash": sha256_hash,
            "timestamp": time_str,
            "tx_hash": tx_hash,
            "seal_method": seal_method,
            "verification_url": verification_url
        }

    def verify_report(self, report_dict: Dict[str, Any], seal_record: Dict[str, Any]) -> bool:
        """Verify that a report matches the stored cryptographic seal."""
        try:
            canonical_str = json.dumps(report_dict, sort_keys=True, default=str)
            computed_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
            return computed_hash == seal_record["sha256_hash"]
        except Exception as e:
            logger.error(f"Verification process failed: {e}")
            return False

    def get_seal(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Fetch stored seal by report_id."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM evidence_seals WHERE report_id = ?", (report_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching seal: {e}")
            return None

    def export_certificate(self, report_id: str, output_filepath: str) -> bool:
        """
        Generate a legally admissible Section 65B Indian Evidence Act certificate PDF.
        Falls back to formatted markdown file if ReportLab is not available.
        """
        seal = self.get_seal(report_id)
        if not seal:
            logger.error(f"No forensic seal found for report {report_id}.")
            return False

        if not REPORTLAB_AVAILABLE:
            # Fallback to rich markdown certificate file
            cert_content = f"""# CERTIFICATE UNDER SECTION 65B OF THE INDIAN EVIDENCE ACT, 1872
            
## Operational Metadata
- **Report Identifier:** {seal['report_id']}
- **Cryptographic Hash (SHA-256):** `{seal['sha256_hash']}`
- **Evidence Sealed Timestamp:** {seal['timestamp']}
- **Anchoring Verification Method:** {seal['seal_method'].upper()}
- **Blockchain Transaction Proof:** {seal['tx_hash'] or 'N/A'}

## Legal Declaration
I, the undersigned, hereby declare that the electronic report details above were generated and compiled by the **Drishti Dark Web OSINT Platform**. During the execution, the computing systems, network devices, and Tor proxies were functioning normally. The cryptographic hash provides immutable mathematical proof that no alterations have occurred to the stored evidence.

**Signature of Certifying Authority:**
____________________________________
Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
Time: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC
"""
            try:
                os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
                with open(output_filepath.replace(".pdf", ".md"), "w", encoding="utf-8") as f:
                    f.write(cert_content)
                logger.info(f"Markdown forensic certificate exported as fallback to {output_filepath.replace('.pdf', '.md')}")
                return True
            except Exception as e:
                logger.error(f"Failed to write fallback certificate: {e}")
                return False

        # Generate a beautiful PDF using ReportLab
        try:
            os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
            doc = SimpleDocTemplate(output_filepath, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CertTitle',
                parent=styles['Heading1'],
                textColor=colors.HexColor('#1a237e'),
                spaceAfter=15,
                alignment=1 # Center
            )
            h2_style = ParagraphStyle(
                'CertH2',
                parent=styles['Heading2'],
                textColor=colors.HexColor('#0d47a1'),
                spaceBefore=10,
                spaceAfter=5
            )
            body_style = ParagraphStyle(
                'CertBody',
                parent=styles['Normal'],
                fontSize=10,
                leading=14,
                spaceAfter=8
            )

            story = []
            
            # Logo header title
            story.append(Paragraph("<b>DRISHTI CYBER OSINT PLATFORM</b>", title_style))
            story.append(Paragraph("<i>CENTRAL FORENSICS UNIT — INDIAN LAW ENFORCEMENT</i>", ParagraphStyle('Sub', parent=styles['Normal'], alignment=1, spaceAfter=20)))
            story.append(Spacer(1, 10))
            
            story.append(Paragraph("CERTIFICATE UNDER SECTION 65B OF THE INDIAN EVIDENCE ACT", ParagraphStyle('Cert', parent=styles['Heading2'], alignment=1, textColor=colors.HexColor('#b71c1c'), spaceAfter=15)))
            
            intro_text = (
                "This certificate is issued under the provisions of Section 65B of the Indian Evidence Act, 1872 "
                "to validate the digital integrity and admissibility of electronically gathered threat intelligence "
                "evidence stored inside the Drishti system logs."
            )
            story.append(Paragraph(intro_text, body_style))
            story.append(Spacer(1, 10))

            story.append(Paragraph("<b>1. EVIDENCE METADATA</b>", h2_style))
            
            table_data = [
                [Paragraph("<b>Report ID:</b>", body_style), Paragraph(seal["report_id"], body_style)],
                [Paragraph("<b>Cryptographic Seal:</b>", body_style), Paragraph(f"<code>{seal['sha256_hash']}</code>", body_style)],
                [Paragraph("<b>Timestamp:</b>", body_style), Paragraph(seal["timestamp"], body_style)],
                [Paragraph("<b>Seal Method:</b>", body_style), Paragraph(seal["seal_method"].upper(), body_style)],
                [Paragraph("<b>Blockchain TX:</b>", body_style), Paragraph(seal["tx_hash"] or "N/A (Local Cryptographic Hash Only)", body_style)]
            ]
            
            t = Table(table_data, colWidths=[120, 360])
            t.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f5f5f5')),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 15))

            story.append(Paragraph("<b>2. TECHNICAL SYSTEM DECLARATION</b>", h2_style))
            dec_text = (
                "I hereby declare and certify that the computing systems, network components, Tor proxies, and "
                "automated database pipelines of the Drishti platform were operating normally and at all material "
                "times during the acquisition of this evidence. The integrity of the electronic record has been "
                "immutably preserved and verified mathematically using the SHA-256 cryptographic hashing standard."
            )
            story.append(Paragraph(dec_text, body_style))
            story.append(Spacer(1, 20))

            # Signature block
            sig_data = [
                ["", ""],
                ["Signature of System Administrator:", "Date: " + datetime.now(timezone.utc).strftime("%Y-%m-%d")],
                ["Designation: Cyber Threat Investigator", "Time: " + datetime.now(timezone.utc).strftime("%H:%M:%S") + " UTC"]
            ]
            sig_table = Table(sig_data, colWidths=[240, 240])
            sig_table.setStyle(TableStyle([
                ('LINEBELOW', (0,0), (0,0), 1, colors.black),
                ('PADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(sig_table)

            doc.build(story)
            logger.info(f"Legally-admissible PDF forensic certificate exported to {output_filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to generate PDF forensic certificate: {e}", exc_info=True)
            return False
