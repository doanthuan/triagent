from exa_py import Exa

from triagent.config import settings
from triagent.logging import logger


def search_exa_literature(query: str):
    """
    Search for scientific literature, clinical trial, PubMed, and other information using Exa API and return formatted results with full text.
    Only use this tool to double check the facts that can not be verified from the web search.

    Args:
        query: The search query string

    Returns:
        A formatted string with search results including titles, URLs, dates, and full text content
    """

    try:
        exa = Exa(api_key=settings.exa_api_key)

        # Perform the search
        result = exa.search_and_contents(
            query,
            num_results=3,
            text=True,
            use_autoprompt=True,
            highlights=True,
        )

        # Access the JSON dictionary from the response
        # Access results directly from the response object
        results = result.results  # Access results directly as an attribute
        # Debug information
        logger.info(f"SEARCH: Found {len(results)} results for '{query}'")

        formatted_results = []
        for item in results:
            # Use direct attribute access
            title = getattr(item, "title", "No title")
            url = getattr(item, "url", "No URL")
            date = getattr(item, "published_date", "No date")
            text = getattr(item, "text", "No text available")

            # Simple print
            # print(f"SEARCH: Found article: {title}")

            formatted_result = (
                f"## {title}\n\nURL: {url}\nPublished: {date}\n\n{text}\n\n---\n\n"
            )
            formatted_results.append(formatted_result)

        # Combine all results
        full_content = "# Exa Search Results\n\n" + "\n".join(formatted_results)
        logger.info(f"SEARCH: Found {len(formatted_results)} results for '{query}'")
        return full_content

    except Exception as e:
        print(f"SEARCH ERROR: {str(e)}")
        return f"Error performing Exa search: {str(e)}"
