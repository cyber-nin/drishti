import click
import subprocess
from yaspin import yaspin
from datetime import datetime
from scrape import scrape_multiple
from search import get_search_results
from llm import get_llm, refine_query, filter_results, generate_summary


@click.group()
@click.version_option()
def drishti():
    """Drishti: AI-Powered Dark Web OSINT Tool."""
    pass


@drishti.command()
@click.option(
    "--model",
    "-m",
    default="llama3.1",
    show_default=True,
    type=click.Choice(
        ["llama3.1", "llama3.2", "gemma3", "gpt-5.1", "gpt-5-mini", "gpt-5-nano", "gpt-4.1",
         "claude-sonnet-4-5", "claude-sonnet-4-0", "deepseek-r1",
         "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]
    ),
    help="Select LLM model to use",
)
@click.option("--query", "-q", required=True, type=str, help="Dark web search query")
@click.option(
    "--threads",
    "-t",
    default=5,
    show_default=True,
    type=int,
    help="Number of threads to use for scraping (Default: 5)",
)
@click.option(
    "--output",
    "-o",
    type=str,
    help="Filename to save the final intelligence summary.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output to see detailed scraping progress",
)
def cli(model, query, threads, output, verbose):
    """Run Drishti in CLI mode.\n
    Example commands:\n
    - drishti -m llama3.1 -q "ransomware payments" -t 12\n
    - drishti --model llama3.1 --query "sensitive credentials exposure" --threads 8 --output filename\n
    - drishti -m gemma3 -q "zero days" -v\n
    """
    llm = get_llm(model)

    if verbose:
        click.echo("[VERBOSE] Starting investigation...\n")
        refined_query = refine_query(llm, query)
        click.echo(f"[VERBOSE] Refined query: {refined_query}\n")

        click.echo("[VERBOSE] Searching dark web engines...")
        search_results = get_search_results(
            refined_query.replace(" ", "+"), max_workers=threads
        )
        click.echo(f"[VERBOSE] Found {len(search_results)} results\n")

        click.echo("[VERBOSE] Filtering results with LLM...")
        search_filtered = filter_results(llm, refined_query, search_results)
        click.echo(f"[VERBOSE] Filtered to {len(search_filtered)} relevant results\n")

        scraped_results, all_artifacts = scrape_multiple(search_filtered, max_workers=threads, verbose=verbose)

        click.echo("[VERBOSE] Generating intelligence summary...\n")
    else:
        with yaspin(text="Processing...", color="cyan") as sp:
            refined_query = refine_query(llm, query)
            search_results = get_search_results(
                refined_query.replace(" ", "+"), max_workers=threads
            )
            search_filtered = filter_results(llm, refined_query, search_results)
            scraped_results, all_artifacts = scrape_multiple(search_filtered, max_workers=threads, verbose=verbose)
            sp.ok("✔")

    summary = generate_summary(llm, query, scraped_results, all_artifacts)

    if not output:
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"summary_{now}.md"
    else:
        filename = output + ".md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(summary)
        click.echo(f"\n\n[OUTPUT] Final intelligence summary saved to {filename}")
        if verbose:
            click.echo("[VERBOSE] Investigation complete!")


@drishti.command()
@click.option(
    "--ui-port",
    default=5000,
    show_default=True,
    type=int,
    help="Port for the Web UI",
)
@click.option(
    "--ui-host",
    default="0.0.0.0",
    show_default=True,
    type=str,
    help="Host for the Web UI",
)
def ui(ui_port, ui_host):
    """Run Drishti in Web UI mode."""
    from app import app
    import os
    os.makedirs('outputs', exist_ok=True)
    app.run(debug=False, host=ui_host, port=ui_port)


if __name__ == "__main__":
    drishti()
