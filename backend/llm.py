import re
import json
import openai
import logging
from typing import Dict, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import warnings

logger = logging.getLogger(__name__)

try:
    from backend.llm_utils import _llm_config_map, _common_llm_params
    from backend.config import OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, NVIDIA_NIM_API_KEY, OPENROUTER_API_KEY
    from backend.prompt_manager import load as load_prompt
except ModuleNotFoundError:
    from llm_utils import _llm_config_map, _common_llm_params
    from config import OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, NVIDIA_NIM_API_KEY, OPENROUTER_API_KEY
    from prompt_manager import load as load_prompt

warnings.filterwarnings("ignore")


_CACHE: Dict[str, Dict[str, str]] = {
    "refine_query": {},
    "filter_results": {},
    "generate_summary": {},
}


def _normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def _safe_parse_indices(indices_str: str, max_results: int) -> List[int]:
    indices = []
    for part in indices_str.strip().split(','):
        part = part.strip().strip('.')
        if not part:
            continue
        if part.isdigit():
            v = int(part)
            if 1 <= v <= max_results:
                indices.append(v)
    return indices


def get_llm(model_choice):
    model_choice_lower = model_choice.lower()
    # Look up the configuration in the map
    config = _llm_config_map.get(model_choice_lower)

    if config is None:  # Extra error check
        # Provide a helpful error message listing supported models
        supported_models = list(_llm_config_map.keys())
        raise ValueError(
            f"Unsupported LLM model: '{model_choice}'. "
            f"Supported models (case-insensitive match) are: {', '.join(supported_models)}"
        )

    # Extract the necessary information from the configuration
    llm_class = config["class"]
    
    # Fast reachability check for local Ollama models
    from langchain_ollama import ChatOllama
    if llm_class == ChatOllama:
        try:
            from backend.config import OLLAMA_BASE_URL
        except ModuleNotFoundError:
            from config import OLLAMA_BASE_URL
            
        import urllib.request
        ollama_ok = False
        try:
            # Send a fast request to OLLAMA_BASE_URL (default http://localhost:11434)
            with urllib.request.urlopen(OLLAMA_BASE_URL, timeout=0.8) as conn:
                if conn.status == 200:
                    ollama_ok = True
        except Exception:
            ollama_ok = False
            
        if not ollama_ok:
            fallback_llm, fb_name = _get_fallback_llm()
            if fallback_llm:
                import logging
                log = logging.getLogger(__name__)
                log.warning(f"Local Ollama unreachable at {OLLAMA_BASE_URL}. Seamlessly falling back to Cloud model: {fb_name}")
                print(f"[!] Local Ollama unreachable at {OLLAMA_BASE_URL}. Seamlessly falling back to Cloud model: {fb_name}")
                return fallback_llm

    model_specific_params = config["constructor_params"]

    # Combine common parameters with model-specific parameters
    # Model-specific parameters will override common ones if there are any conflicts
    all_params = {**_common_llm_params, **model_specific_params}

    # Create the LLM instance using the gathered parameters
    llm_instance = llm_class(**all_params)

    return llm_instance


def _get_fallback_llm():
    """
    Finds a fallback cloud LLM based on configured API keys in config.py.
    Priority order:
      1. Google Gemini (fast, generous free quota)
      2. OpenAI GPT
      3. Anthropic Claude
      4. NVIDIA NIM
      5. OpenRouter paid models
      6. OpenRouter FREE tier (no credit card needed — last resort)
    """
    try:
        from backend.config import OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, NVIDIA_NIM_API_KEY, OPENROUTER_API_KEY
    except ModuleNotFoundError:
        from config import OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, NVIDIA_NIM_API_KEY, OPENROUTER_API_KEY
        
    def is_valid_key(key):
        return key and "your_" not in str(key) and str(key).strip() != ""
        
    log = logging.getLogger(__name__)
    
    if is_valid_key(GOOGLE_API_KEY):
        try:
            return get_llm("gemini-2.5-flash"), "gemini-2.5-flash"
        except Exception as e:
            log.debug(f"Failed to load fallback Gemini model: {e}")
            
    if is_valid_key(OPENAI_API_KEY):
        try:
            return get_llm("gpt-5-mini"), "gpt-5-mini"
        except Exception as e:
            log.debug(f"Failed to load fallback OpenAI model: {e}")
            
    if is_valid_key(ANTHROPIC_API_KEY):
        try:
            return get_llm("claude-sonnet-4-5"), "claude-sonnet-4-5"
        except Exception as e:
            log.debug(f"Failed to load fallback Anthropic model: {e}")

    if is_valid_key(NVIDIA_NIM_API_KEY):
        try:
            return get_llm("nemotron-70b-nim"), "nemotron-70b-nim"
        except Exception as e:
            log.debug(f"Failed to load fallback NVIDIA NIM model: {e}")

    if is_valid_key(OPENROUTER_API_KEY):
        try:
            return get_llm("llama-4-scout-or"), "llama-4-scout-or"
        except Exception as e:
            log.debug(f"Failed to load fallback OpenRouter paid model: {e}")

    # ── Last resort: completely free OpenRouter models ──
    # No credit card needed, just a free OpenRouter account.
    free_llm, free_name = _get_free_fallback_llm()
    if free_llm:
        log.warning(
            f"All paid providers unavailable. Falling back to FREE model: {free_name}. "
            f"Note: free models have rate limits (~20 req/min, ~200 req/day)."
        )
        return free_llm, free_name

    return None, None


def _get_free_fallback_llm():
    """
    Returns a completely FREE LLM from OpenRouter's free tier.
    Requires only a free OpenRouter account — no credit card, no paid plan.

    Tries models in order of capability. Falls back sequentially if one
    is rate-limited or unavailable (OpenRouter returns 429 or 404 in those cases).

    Get your free key at: https://openrouter.ai/keys
    """
    try:
        from backend.config import OPENROUTER_API_KEY
    except ModuleNotFoundError:
        from config import OPENROUTER_API_KEY

    def is_valid_key(key):
        return key and "your_" not in str(key) and str(key).strip() != ""

    log = logging.getLogger(__name__)

    if not is_valid_key(OPENROUTER_API_KEY):
        log.debug("No OPENROUTER_API_KEY configured — cannot use free tier fallback.")
        return None, None

    # Ordered priority: best free models first
    free_models = [
        ("auto-free-or",            "OpenRouter Auto (Free)"),
        ("llama-4-maverick-free-or","Llama 4 Maverick (Free/OR)"),
        ("llama-4-scout-free-or",   "Llama 4 Scout (Free/OR)"),
        ("deepseek-r1-free-or",     "DeepSeek R1 (Free/OR)"),
        ("deepseek-v4-flash-free-or","DeepSeek V4 Flash (Free/OR)"),
        ("qwen3-coder-free-or",     "Qwen3 Coder (Free/OR)"),
        ("gemma-4-31b-free-or",     "Gemma 4 31B (Free/OR)"),
        ("llama-3-3-70b-free-or",   "Llama 3.3 70B (Free/OR)"),
    ]

    for model_key, display_name in free_models:
        try:
            llm = get_llm(model_key)
            log.debug(f"Free fallback loaded: {display_name}")
            return llm, display_name
        except Exception as e:
            log.debug(f"Free model '{display_name}' unavailable: {e}. Trying next...")

    log.error("All free OpenRouter models failed. No LLM available.")
    return None, None


def refine_query(llm, user_input):
    normalized_input = _normalize_text(user_input)
    if normalized_input in _CACHE["refine_query"]:
        return _CACHE["refine_query"][normalized_input]

    system_prompt = load_prompt('refine_query')
    prompt_template = ChatPromptTemplate(
        [("system", system_prompt), ("user", "{query}")]
    )
    chain = prompt_template | llm | StrOutputParser()

    try:
        output = chain.invoke({"query": user_input}) or ""
        refined_query = _normalize_text(output.splitlines()[0]) if output.strip() else normalized_input
    except Exception as e:
        import logging
        log = logging.getLogger(__name__)
        log.warning(f"Ollama local model failed on refine_query: {e}. Attempting cloud model fallback...")
        fallback_llm, fb_name = _get_fallback_llm()
        if fallback_llm:
            try:
                fallback_chain = prompt_template | fallback_llm | StrOutputParser()
                output = fallback_chain.invoke({"query": user_input}) or ""
                refined_query = _normalize_text(output.splitlines()[0]) if output.strip() else normalized_input
                log.info(f"Successfully refined query using cloud fallback: {fb_name}")
            except Exception as fb_err:
                log.error(f"Cloud fallback query refinement also failed: {fb_err}")
                refined_query = normalized_input
        else:
            refined_query = normalized_input

    _CACHE["refine_query"][normalized_input] = refined_query
    return refined_query


def filter_results(llm, query, results):
    if not results:
        return []

    cache_key = f"{_normalize_text(query)}|{len(results)}"
    if cache_key in _CACHE["filter_results"]:
        return _CACHE["filter_results"][cache_key]

    system_prompt = load_prompt('filter_results').replace('{query}', query)

    final_str = _generate_final_string(results)

    prompt_template = ChatPromptTemplate(
        [("system", system_prompt), ("user", "{results}")]
    )
    chain = prompt_template | llm | StrOutputParser()

    try:
        result_indices = chain.invoke({"query": query, "results": final_str})
    except openai.RateLimitError as e:
        print(
            f"Rate limit error: {e} \n Truncating to Web titles only with 30 characters"
        )
        final_str = _generate_final_string(results, truncate=True)
        result_indices = chain.invoke({"query": query, "results": final_str})
    except Exception as e:
        import logging
        log = logging.getLogger(__name__)
        log.warning(f"Ollama local model failed on filter_results: {e}. Attempting cloud model fallback...")
        fallback_llm, fb_name = _get_fallback_llm()
        if fallback_llm:
            try:
                fallback_chain = prompt_template | fallback_llm | StrOutputParser()
                result_indices = fallback_chain.invoke({"query": query, "results": final_str})
                log.info(f"Successfully filtered results using cloud fallback: {fb_name}")
            except Exception as fb_err:
                log.error(f"Cloud fallback filtering also failed: {fb_err}")
                result_indices = ""
        else:
            result_indices = ""

    index_list = _safe_parse_indices(result_indices, len(results))
    if not index_list:
        index_list = list(range(1, min(20, len(results)) + 1))

    top_results = [results[i - 1] for i in index_list]

    _CACHE["filter_results"][cache_key] = top_results
    return top_results


def _generate_final_string(results, truncate=False):
    """
    Generate a formatted string from the search results for LLM processing.
    """

    if truncate:
        # Use only the first 35 characters of the title
        max_title_length = 30
        # Do not use link at all
        max_link_length = 0

    final_str = []
    for i, res in enumerate(results):
        # Use full link
        truncated_link = res["link"]
        title = re.sub(r"[^0-9a-zA-Z\-\.]", " ", res["title"])
        if truncated_link == "" and title == "":
            continue

        if truncate:
            # Truncate title to max_title_length characters
            title = (
                title[:max_title_length] + "..."
                if len(title) > max_title_length
                else title
            )
            # Truncate link to max_link_length characters
            truncated_link = (
                truncated_link[:max_link_length] + "..."
                if len(truncated_link) > max_link_length
                else truncated_link
            )

        final_str.append(f"{i+1}. {truncated_link} - {title}")

    return "\n".join(s for s in final_str)


def generate_summary(llm, query, content, artifacts=None):
    try:
        from backend.artifact_extractor import ArtifactExtractor
    except ModuleNotFoundError:
        from artifact_extractor import ArtifactExtractor

    normalized_query = _normalize_text(query)
    content_id = str(sorted(content.keys())[:5]) if isinstance(content, dict) else str(content)[:1024]
    cache_key = f"{normalized_query}|{content_id}"
    if cache_key in _CACHE["generate_summary"]:
        return _CACHE["generate_summary"][cache_key]

    try:
        system_prompt = load_prompt('generate_summary').replace('{query}', query)

        # Prepare content with extracted artifacts
        content_with_artifacts = (
            "\n\n".join(f"Source: {url}\n{text}" for url, text in content.items())
            if isinstance(content, dict) else str(content)
        ) if content else ""
        if artifacts:
            extractor = ArtifactExtractor()
            artifacts_formatted = extractor.format_artifacts(artifacts)
            content_with_artifacts += f"\n\n--- EXTRACTED ARTIFACTS ---\n{artifacts_formatted}"

            try:
                from enrichment import enrich_artifacts, format_enrichment
            except ModuleNotFoundError:
                try:
                    from backend.enrichment import enrich_artifacts, format_enrichment
                except ModuleNotFoundError:
                    enrich_artifacts = format_enrichment = None

            if enrich_artifacts and format_enrichment:
                try:
                    enriched = enrich_artifacts(artifacts)
                    enrichment_text = format_enrichment(enriched)
                    content_with_artifacts += f"\n\n{enrichment_text}"
                except Exception as enrich_ex:
                    logger.debug(f"Enrichment skipped: {enrich_ex}")

        prompt_template = ChatPromptTemplate(
            [("system", system_prompt), ("user", "{content}")]
        )
        chain = prompt_template | llm | StrOutputParser()

        try:
            raw_summary = chain.invoke({"query": query, "content": content_with_artifacts})
        except Exception as e:
            import logging
            log = logging.getLogger(__name__)
            log.warning(f"Ollama local model failed on generate_summary: {e}. Attempting cloud model fallback...")
            fallback_llm, fb_name = _get_fallback_llm()
            if fallback_llm:
                try:
                    fallback_chain = prompt_template | fallback_llm | StrOutputParser()
                    raw_summary = fallback_chain.invoke({"query": query, "content": content_with_artifacts})
                    log.info(f"Successfully generated summary using cloud fallback: {fb_name}")
                except Exception as fb_err:
                    log.error(f"Cloud fallback summary also failed: {fb_err}")
                    raw_summary = ""
            else:
                raw_summary = ""

        # Normalize the response to a string
        summary = ""
        if isinstance(raw_summary, dict):
            summary = (
                raw_summary.get("output_text")
                or raw_summary.get("text")
                or raw_summary.get("response")
                or raw_summary.get("answer")
                or json.dumps(raw_summary) if raw_summary else ""
            )
        elif isinstance(raw_summary, str):
            summary = raw_summary
        elif raw_summary is None:
            summary = ""
        else:
            try:
                summary = str(raw_summary)
            except Exception:
                summary = ""

        # Ensure we have a string
        if not isinstance(summary, str):
            summary = ""
        
        cleaned_summary = summary.strip() if summary else ""

        if not cleaned_summary:
            cleaned_summary = "No LLM summary was generated."

    except Exception as outer_ex:
        # If we hit ANY exception in the try block, still build the report
        cleaned_summary = f"LLM summary unavailable: {str(outer_ex)[:100]}"

    # Prepare flat text for classification & mapping
    flat_text = query
    if isinstance(content, dict):
        flat_text += " " + " ".join(str(text) for text in content.values())
    else:
        flat_text += " " + str(content)

    # 1. Threat Classification
    class_res = None
    try:
        try:
            from backend.classifier import classify_content
        except ModuleNotFoundError:
            from classifier import classify_content
        class_res = classify_content(llm if 'llm' in locals() else None, flat_text)
    except Exception as class_ex:
        logger.debug(f"Threat classification failed: {class_ex}")

    # 2. MITRE ATT&CK TTP Mapping
    mitre_techs = []
    try:
        try:
            from backend.mitre_mapper import extract_mitre_techniques
        except ModuleNotFoundError:
            from mitre_mapper import extract_mitre_techniques
        mitre_techs = extract_mitre_techniques(flat_text, llm=(llm if 'llm' in locals() else None), query=query)
    except Exception as mitre_ex:
        logger.debug(f"MITRE mapping failed: {mitre_ex}")

    # Always build report with sections - this is the GUARANTEED output
    try:
        section_lines = ["# Investigation Report", "", f"Query: {query}", ""]

        # Add Threat Classification if available
        if class_res:
            section_lines.append("## Threat Classification")
            section_lines.append(f"- **Primary Threat Category**: `{class_res.primary_category}` (Confidence: {int(class_res.confidence * 100)}%)")
            if class_res.secondary_categories:
                section_lines.append(f"- **Secondary Categories**: {', '.join(f'`{s}`' for s in class_res.secondary_categories)}")
            section_lines.append(f"- **Rationale**: {class_res.rationale}")
            section_lines.append("")

        # Add MITRE ATT&CK TTPs if available
        if mitre_techs:
            section_lines.append("## MITRE ATT&CK TTP Mapping")
            for tech in mitre_techs:
                confidence_str = f" (Confidence: {tech['confidence'].upper()})" if "confidence" in tech else ""
                rationale_str = f"\n  - *Rationale*: {tech['rationale']}" if tech.get("rationale") else ""
                section_lines.append(f"- **{tech['id']} - {tech['name']}** [{tech['tactic']}]{confidence_str}{rationale_str}")
            section_lines.append("")

        if isinstance(content, dict) and content:
            section_lines.append("## Source Links")
            for source in sorted(content.keys()):
                section_lines.append(f"- {source}")
            section_lines.append("")

        if artifacts:
            section_lines.append("## Extracted Artifacts")
            for src in sorted(artifacts.keys()):
                art = artifacts.get(src, {})
                if art:
                    section_lines.append(f"### Source: {src}")
                    for artifact_type in sorted(art.keys()):
                        values = art.get(artifact_type, set())
                        if values:
                            try:
                                value_list = sorted(list(values))[:10]
                                section_lines.append(f"- {artifact_type}: {', '.join(str(v) for v in value_list)}")
                            except Exception:
                                pass
                    section_lines.append("")

        # Add LLM summary
        section_lines.append("## LLM Summary")
        section_lines.append(str(cleaned_summary) if cleaned_summary else "No LLM summary available.")

        final_summary = "\n".join(str(line) for line in section_lines)
    except Exception as build_ex:
        # Last resort fallback
        final_summary = f"""# Investigation Report

Query: {query}

Found {len(content) if isinstance(content, dict) else 0} results.

Error building detailed report: {str(build_ex)[:200]}"""

    _CACHE["generate_summary"][cache_key] = final_summary
    return final_summary
