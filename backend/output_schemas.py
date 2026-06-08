"""
Structured output schemas for Drishti LLM operations.
Uses Pydantic models to enforce strict JSON output from LLMs.
"""

from typing import List, Dict, Optional, Set
from pydantic import BaseModel, Field
from datetime import datetime


class QueryRefinement(BaseModel):
    """Schema for refined queries."""
    original_query: str
    refined_query: str
    keywords_added: List[str] = Field(default_factory=list)
    keywords_removed: List[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    """Schema for individual search result."""
    index: int
    title: str
    link: str
    relevance_score: Optional[float] = None


class FilteredResults(BaseModel):
    """Schema for filtered search results."""
    total_results: int
    selected_count: int
    selected_indices: List[int]
    results: List[SearchResult]


class Section(BaseModel):
    """Schema for a report section."""
    heading: str
    content: str
    subsections: List[Dict[str, str]] = Field(default_factory=list)


class IOCIndicator(BaseModel):
    """Schema for IOC (Indicator of Compromise)."""
    type: str  # email, btc, eth, domain, ip, etc.
    value: str
    context: Optional[str] = None
    confidence: Optional[str] = Field(default="medium")  # low, medium, high


class InvestigationArtifacts(BaseModel):
    """Schema for extracted investigation artifacts."""
    source: str
    extraction_timestamp: datetime = Field(default_factory=datetime.now)
    artifacts_by_type: Dict[str, List[str]] = Field(default_factory=dict)
    ioc_list: List[IOCIndicator] = Field(default_factory=list)


class KeyInsight(BaseModel):
    """Schema for key insight in the report."""
    title: str
    description: str
    evidence: List[str] = Field(default_factory=list)
    confidence: str = Field(default="medium")  # low, medium, high


class NextStep(BaseModel):
    """Schema for recommended next investigation step."""
    action: str
    suggested_query: Optional[str] = None
    rationale: str
    priority: str = Field(default="medium")  # low, medium, high


class InvestigationSummary(BaseModel):
    """Complete structured investigation report."""
    query: str
    timestamp: datetime = Field(default_factory=datetime.now)
    source_links: List[str] = Field(default_factory=list)
    summary_text: Optional[str] = None
    artifacts: InvestigationArtifacts
    key_insights: List[KeyInsight] = Field(default_factory=list)
    next_steps: List[NextStep] = Field(default_factory=list)
    metadata: Dict[str, any] = Field(default_factory=dict)

    def to_markdown(self) -> str:
        """Convert structured summary to markdown report."""
        lines = []
        lines.append(f"# Investigation Report")
        lines.append(f"**Query:** {self.query}")
        lines.append(f"**Generated:** {self.timestamp.isoformat()}")
        lines.append("")

        if self.source_links:
            lines.append("## Source Links Referenced")
            for link in self.source_links:
                lines.append(f"- {link}")
            lines.append("")

        if self.artifacts and self.artifacts.ioc_list:
            lines.append("## Investigation Artifacts")
            by_type = {}
            for ioc in self.artifacts.ioc_list:
                if ioc.type not in by_type:
                    by_type[ioc.type] = []
                by_type[ioc.type].append(ioc.value)
            
            for artifact_type, values in sorted(by_type.items()):
                lines.append(f"### {artifact_type.title()}")
                for val in values[:20]:
                    lines.append(f"- {val}")
            lines.append("")

        if self.key_insights:
            lines.append("## Key Insights")
            for i, insight in enumerate(self.key_insights, 1):
                lines.append(f"### {i}. {insight.title}")
                lines.append(insight.description)
                if insight.evidence:
                    lines.append("**Evidence:**")
                    for ev in insight.evidence:
                        lines.append(f"- {ev}")
                lines.append("")

        if self.next_steps:
            lines.append("## Next Steps")
            for i, step in enumerate(self.next_steps, 1):
                lines.append(f"### {i}. {step.action}")
                lines.append(step.rationale)
                if step.suggested_query:
                    lines.append(f"**Suggested Query:** `{step.suggested_query}`")
                lines.append("")

        return "\n".join(lines)


class CrawlResult(BaseModel):
    """Schema for deep crawl results."""
    start_url: str
    pages_crawled: int
    max_depth: int
    artifacts_types: Dict[str, List[str]] = Field(default_factory=dict)
    links_discovered: List[str] = Field(default_factory=list)
    forms_discovered: List[Dict[str, any]] = Field(default_factory=list)
