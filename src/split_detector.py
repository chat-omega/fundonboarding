"""Split detection functionality for PDF documents."""

import asyncio
import os
from typing import List, Optional, Dict
from collections import defaultdict

from llama_index.core.schema import TextNode
from llama_index.core.llms import LLM
from llama_index.core.async_utils import run_jobs
from llama_index.core.prompts import ChatPromptTemplate, ChatMessage
from llama_index.llms.openai import OpenAI

from .models import SplitCategories, SplitOutput, SplitsOutput


split_category_prompt = """\
You are an AI document assistant tasked with finding the 'split categories' given a user description and the document text.
- The split categories is a list of string tags from the document that correspond to the user description.
- Do not make up split categories. 
- Do not include category tags that don't fit the user description,\
for instance subcategories or extraneous titles.
- Do not exclude category tags that do fit the user description. 

For instance, if the user asks to "find all top-level sections of an ArXiv paper", then a sample output would be:
["1. Introduction", "2. Related Work", "3. Methodology", "4. Experiments", "5. Conclusion"]

The split description and document text are given below. 

Split description:
{split_description}

Here is the document text:
{document_text}
    
"""


split_prompt = """\
You are an AI document assistant tasked with extracting out splits from a document text according to a certain set of rules. 

You are given a chunk of the document text at a time. 
You are responsible for determining if the chunk of the document text corresponds to the beginning of a split. 

We've listed general rules below, and the user has also provided their own rules to find a split. Please extract
out the splits according to the defined schema. 

General Rules: 
- You should ONLY extract out a split if the document text contains the beginning of a split.
- If the document text contains the beginning of two or more splits (e.g. there are multiple sections on a single page), then \
return all splits in the output.
- If the text does not correspond to the beginning of any split, then return a blank list. 
- A valid split must be clearly delineated in the document text according to the user rules. \
Do NOT identify a split if it is mentioned, but is not actually the start of a split in the document text.
- If you do find one or more splits, please output the split_name according to the format \"{split_key}_X\", \
where X is a short tag corresponding to the split. 

Split key:
{split_key}

User-defined rules:
{split_rules}


Here is the chunk text:
{chunk_text}
    
"""


async def afind_split_categories(
    split_description: str,
    nodes: List[TextNode],
    llm: Optional[LLM] = None,
    page_limit: Optional[int] = 5,
) -> List[str]:
    """Find split categories given a user description and the page limit.
    
    These categories will then be used to find the exact splits of the document. 
    
    NOTE: with the page limit there is an assumption that the categories are found in the first few pages,\
    for instance in the table of contents. This does not account for the case where the categories are \
    found throughout the document. 
    
    """
    llm = llm or OpenAI(model="gpt-4o")

    chat_template = ChatPromptTemplate(
        [
            ChatMessage.from_str(split_category_prompt, "user"),
        ]
    )
    nodes_head = nodes[:page_limit] if page_limit is not None else nodes
    doc_text = "\n-----\n".join(
        [n.get_content(metadata_mode="all") for n in nodes_head]
    )

    result = await llm.astructured_predict(
        SplitCategories,
        chat_template,
        split_description=split_description,
        document_text=doc_text,
    )
    return result.split_categories


async def atag_splits_in_node(
    split_rules: str, split_key: str, node: TextNode, llm: Optional[LLM] = None
):
    """Tag split in a single node."""
    llm = llm or OpenAI(model="gpt-4o")

    chat_template = ChatPromptTemplate(
        [
            ChatMessage.from_str(split_prompt, "user"),
        ]
    )

    result = await llm.astructured_predict(
        SplitsOutput,
        chat_template,
        split_rules=split_rules,
        split_key=split_key,
        chunk_text=node.get_content(metadata_mode="all"),
    )
    return result.splits


async def afind_splits(
    split_rules: str, split_key: str, nodes: List[TextNode], llm: Optional[LLM] = None
) -> Dict:
    """Find splits."""

    # tag each node with split or no-split
    tasks = [atag_splits_in_node(split_rules, split_key, n, llm=llm) for n in nodes]
    async_results = await run_jobs(tasks, workers=8, show_progress=True)
    all_splits = [s for r in async_results for s in r]

    split_name_to_pages = defaultdict(list)

    split_idx = 0
    for idx, n in enumerate(nodes):
        cur_page = n.metadata["page_number"]

        # update the current split if needed
        while (
            split_idx + 1 < len(all_splits)
            and all_splits[split_idx + 1].page_number <= cur_page
        ):
            split_idx += 1

        # add page number to the current split
        if all_splits and split_idx < len(all_splits) and all_splits[split_idx].page_number <= cur_page:
            split_name = all_splits[split_idx].split_name
            split_name_to_pages[split_name].append(cur_page)

    return split_name_to_pages


async def afind_categories_and_splits(
    split_description: str,
    split_key: str,
    nodes: List[TextNode],
    additional_split_rules: Optional[str] = None,
    llm: Optional[LLM] = None,
    page_limit: int = 5,
    verbose: bool = False,
):
    """Find categories and then splits."""
    categories = await afind_split_categories(
        split_description, nodes, llm=llm, page_limit=page_limit
    )
    if verbose:
        print(f"Split categories: {categories}")
    full_split_rules = f"""Please split by these categories: {categories}"""
    if additional_split_rules:
        full_split_rules += f"\n\n\n{additional_split_rules}"

    return await afind_splits(full_split_rules, split_key, nodes, llm=llm)