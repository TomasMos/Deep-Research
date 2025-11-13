from gettext import find
import time
from tracemalloc import start
from agents import Runner, agent_output, trace
from rich.box import MARKDOWN
from rich.console import Console
from rich.panel import Panel
from models import SearchResult
from research_agents.search_agent import search_agent
from research_agents.query_agent import query_agent
from research_agents.synthesis_agent import synthesis_agent
from research_agents.query_agent import QueryResponse
from ddgs import DDGS
from rich.markdown import Markdown

console = Console()

class ResearchCoordinator:
    def __init__(self, query: str):
        self.query = query
        self.search_results = []
    
    async def research(self) -> str:
        with trace("Deep Research Workflow"):
            query_response = await self.generate_queries()

            # Pass list of queries to perform_research_for_queries
            await self.perform_research_for_queries(query_response.final_output.queries)

            final_report = await self.synthesis_report()

            console.print("\n [bold green]Research complete![/bold green]\n")
            console.print(Markdown(final_report))

            return final_report
    
    async def generate_queries(self) -> QueryResponse:
        with console.status("[bold cyan] Analyzing query...[/bold cyan]") as status:

            # Run the query agent
            result = await Runner.run(query_agent, input=self.query)

            # Display the results
            console.print(Panel(f"[bold cyan]Query Analysis[/bold cyan]"))
            console.print(f"[yellow]Thoughts:[/yellow] {result.final_output.thoughts}")
            console.print("\n[yellow]Generated Search Queries:[/yellow]")
            for i, query in enumerate(result.final_output.queries, 1):
                console.print(f" {i}. {query}")

            return result
            
    async def duckduckgo_search(self, query: str):
        try:
            results = DDGS().text(query, region="us-en", safesearch="Off", timelimit="y", max_results=1)
            return results
        except Exception as ex:
            console.print(f"[bold red]Search error: [/bold red] {str(ex)}")
            return []
    
    async def perform_research_for_queries(self, queries: list[str]):
        # get all of the search results for each query

        all_search_results = {}

        for query in queries:
            results = await self.duckduckgo_search(query)
            all_search_results[query] = results

        for query in queries: 
            console.print(f"\n[bold cyan]Searching for:[/bold cyan] {query}")

            for result in all_search_results[query]:
                console.print(f"   [green]Result:[/green] {result['title']}")
                console.print(f"   [dim]URL:[/dim] {result['href']}")
                console.print(f"   [cyan]Analyzing content...[/cyan]")

                start_analysis_time = time.time()
                search_input = f"Title: {result['title']}\nURL: {result['href']}"
                agent_result = await Runner.run(search_agent, input=search_input)
                analysis_time = time.time() - start_analysis_time

                search_result = SearchResult(
                    title=result['title'],
                    url=result['href'],
                    summary=agent_result.final_output
                )

                self.search_results.append(search_result)

                summary_preview = agent_result.final_output[:100] + ("..." if len(agent_result.final_output) > 100 else "")

                console.print(f"   [green]Summary: [/green] {summary_preview}")
                console.print(f"   [dim]Analysis completed in {analysis_time:.2f}s[/dim]\n")
        
        console.print(f"\n[bold green]Research run complete[/bold green] Found {len(all_search_results)} sources across {len(queries)} queries.")

    async def synthesis_report(self) -> str:
        with console.status("[bold cyan]Synthesizing research findings...[/bold cyan]") as status:
            findings_text = f"Query: {self.query}\n\nSearch Results: \n"
            for i, result in enumerate(self.search_results, 1):
                findings_text += f"\n{i}. Title: {result.title}\n    URL: {result.url}\n    Summary: {result.summary}\n"
            
            result = await Runner.run(synthesis_agent, input=findings_text)

            return result.final_output