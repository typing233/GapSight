import asyncio
import aiohttp
from typing import List, Optional, Dict, Any
from datetime import datetime
import time

from backend.config import settings
from backend.models.schemas import Paper


class SemanticScholarService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.SEMANTIC_SCHOLAR_API_KEY
        self.base_url = settings.SEMANTIC_SCHOLAR_BASE_URL
        self.last_request_time = 0
        self.min_interval = 1.0 / 100

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "User-Agent": "GapSight/1.0 (Research Tool; Academic Literature Analysis)"
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    async def _rate_limit(self):
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    async def search_papers(
        self,
        keywords: List[str],
        max_papers: int = 100,
        years_back: int = 5
    ) -> List[Paper]:
        query = " ".join(keywords)
        current_year = datetime.now().year
        min_year = current_year - years_back

        papers = []
        offset = 0
        limit_per_request = min(100, max_papers)

        async with aiohttp.ClientSession() as session:
            while len(papers) < max_papers:
                await self._rate_limit()
                
                url = f"{self.base_url}/paper/search"
                params = {
                    "query": query,
                    "limit": limit_per_request,
                    "offset": offset,
                    "fields": "paperId,title,abstract,year,authors,venue,citationCount,url",
                    "year": f"{min_year}-",
                    "sort": "relevance"
                }

                async with session.get(
                    url,
                    params=params,
                    headers=self._get_headers()
                ) as response:
                    if response.status == 429:
                        await asyncio.sleep(2)
                        continue
                    elif response.status != 200:
                        break

                    data = await response.json()
                    if "data" not in data or not data["data"]:
                        break

                    for item in data["data"]:
                        paper = self._parse_paper(item)
                        if paper:
                            papers.append(paper)
                            if len(papers) >= max_papers:
                                break

                    offset += limit_per_request
                    if len(data["data"]) < limit_per_request:
                        break

        return papers

    async def get_paper_details(
        self,
        paper_ids: List[str],
        fields: Optional[List[str]] = None
    ) -> List[Paper]:
        if not paper_ids:
            return []

        default_fields = ["paperId", "title", "abstract", "year", "authors", "venue", "citationCount", "url"]
        fields = fields or default_fields
        fields_str = ",".join(fields)

        papers = []
        batch_size = 500

        async with aiohttp.ClientSession() as session:
            for i in range(0, len(paper_ids), batch_size):
                batch = paper_ids[i:i + batch_size]
                await self._rate_limit()

                url = f"{self.base_url}/paper/batch"
                params = {"fields": fields_str}
                json_data = {"ids": batch}

                async with session.post(
                    url,
                    params=params,
                    json=json_data,
                    headers=self._get_headers()
                ) as response:
                    if response.status == 429:
                        await asyncio.sleep(2)
                        i -= batch_size
                        continue
                    elif response.status != 200:
                        continue

                    data = await response.json()
                    for item in data:
                        paper = self._parse_paper(item)
                        if paper:
                            papers.append(paper)

        return papers

    def _parse_paper(self, item: Dict[str, Any]) -> Optional[Paper]:
        try:
            paper_id = item.get("paperId")
            if not paper_id:
                return None

            authors = []
            if item.get("authors"):
                authors = [author.get("name", "") for author in item["authors"] if author.get("name")]

            return Paper(
                paper_id=paper_id,
                title=item.get("title", "") or "",
                abstract=item.get("abstract"),
                year=item.get("year"),
                authors=authors,
                venue=item.get("venue"),
                citations=item.get("citationCount", 0) or 0,
                url=item.get("url")
            )
        except Exception:
            return None


semantic_scholar_service = SemanticScholarService()
