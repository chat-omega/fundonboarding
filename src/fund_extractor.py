"""Main fund extraction functionality."""

import asyncio
from typing import List, Optional, Dict

from llama_index.core.schema import TextNode
from llama_index.core.llms import LLM
from llama_index.core.async_utils import run_jobs
from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Context,
    Workflow,
    step,
)
from llama_cloud_services import LlamaParse, LlamaExtract
from llama_cloud_services.extract import SourceText
from llama_cloud import ExtractConfig
from llama_cloud.core.api_error import ApiError

import pandas as pd

from .models import FundData, FundComparisonData
from .split_detector import afind_categories_and_splits


class ParseDocEvent(Event):
    nodes: List[TextNode]


class DocSplitEvent(Event):
    split_name_to_pages: Dict[str, List[int]]
    nodes: List[TextNode]


async def aextract_data_over_split(
    split_name: str,
    page_numbers: List[int],
    nodes: List[TextNode],
    extract_agent: LlamaExtract,
    llm: Optional[LLM] = None,
) -> FundData:
    """Extract fund data for a given split."""

    # combine node text that matches the page numbers
    filtered_nodes = [n for n in nodes if n.metadata["page_number"] in page_numbers]
    filtered_text = "\n-------\n".join(
        [n.get_content(metadata_mode="all") for n in filtered_nodes]
    )
    result_dict = (
        await extract_agent.aextract(SourceText(text_content=filtered_text))
    ).data

    fund_data = FundData.model_validate(result_dict)

    return fund_data


async def aextract_data_over_splits(
    split_name_to_pages: Dict[str, List],
    nodes: List[TextNode],
    extract_agent: LlamaExtract,
    llm: Optional[LLM] = None,
):
    """Extract fund data for each split, aggregate."""
    tasks = [
        aextract_data_over_split(split_name, page_numbers, nodes, extract_agent, llm=llm)
        for split_name, page_numbers in split_name_to_pages.items()
    ]
    all_fund_data = await run_jobs(tasks, workers=8, show_progress=True)
    return FundComparisonData(funds=all_fund_data)


class FidelityFundExtraction(Workflow):
    """
    Workflow to extract data from a Fidelity fund document.
    """

    def __init__(
        self,
        parser: LlamaParse,
        extract_agent: LlamaExtract,
        split_description: str,
        split_rules: str,
        split_key: str,
        llm: Optional[LLM] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.parser = parser
        self.extract_agent = extract_agent
        self.split_description = split_description
        self.split_rules = split_rules
        self.split_key = split_key
        self.llm = llm

    @step
    async def parse_doc(self, ctx: Context, ev: StartEvent) -> ParseDocEvent:
        """Parse document into markdown nodes."""
        print("Parsing document...")
        result = await self.parser.aparse(file_path=ev.file_path)
        markdown_nodes = await result.aget_markdown_nodes(split_by_page=True)
        print(f"Document parsed into {len(markdown_nodes)} pages")
        return ParseDocEvent(nodes=markdown_nodes)

    @step
    async def find_splits(self, ctx: Context, ev: ParseDocEvent) -> DocSplitEvent:
        """Find document splits."""
        print("Finding document splits...")
        split_name_to_pages = await afind_categories_and_splits(
            self.split_description,
            self.split_key,
            ev.nodes,
            additional_split_rules=self.split_rules,
            llm=self.llm,
            verbose=True,
        )
        print(f"Found {len(split_name_to_pages)} splits")
        return DocSplitEvent(
            split_name_to_pages=split_name_to_pages,
            nodes=ev.nodes,
        )

    @step
    async def run_extraction(self, ctx: Context, ev: DocSplitEvent) -> StopEvent:
        """Run data extraction on each split."""
        print("Extracting fund data...")
        all_fund_data = await aextract_data_over_splits(
            ev.split_name_to_pages, ev.nodes, self.extract_agent, llm=self.llm
        )
        all_fund_data_df = pd.DataFrame(all_fund_data.to_csv_rows())
        print(f"Extracted data for {len(all_fund_data.funds)} funds")
        return StopEvent(
            result={
                "all_fund_data": all_fund_data,
                "all_fund_data_df": all_fund_data_df,
                "split_name_to_pages": ev.split_name_to_pages,
            }
        )


def setup_extract_agent(
    project_id: str = None,
    organization_id: str = None,
    agent_name: str = "FundDataExtractor2"
) -> LlamaExtract:
    """Set up the LlamaExtract agent."""
    kwargs = {
        "show_progress": True,
        "check_interval": 5,
    }
    if project_id:
        kwargs["project_id"] = project_id
    if organization_id:
        kwargs["organization_id"] = organization_id
        
    llama_extract = LlamaExtract(**kwargs)

    # Clean up existing agent if it exists
    try:
        existing_agent = llama_extract.get_agent(name=agent_name)
        if existing_agent:
            print(f"Deleting existing agent: {agent_name}")
            llama_extract.delete_agent(existing_agent.id)
    except ApiError as e:
        if e.status_code == 404:
            pass
        else:
            raise

    # Create new agent
    extract_config = ExtractConfig(
        extraction_mode="BALANCED",
    )

    extract_agent = llama_extract.create_agent(
        agent_name, data_schema=FundData, config=extract_config
    )
    print(f"Created extraction agent: {agent_name}")
    
    return extract_agent