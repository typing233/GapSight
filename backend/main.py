import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Optional
import logging

from backend.config import settings
from backend.models.schemas import (
    SearchRequest,
    NetworkData,
    GapPromptRequest,
    GapPromptResponse,
    ConfigResponse
)
from backend.services import (
    semantic_scholar_service,
    SemanticScholarService,
    entity_extractor,
    network_analyzer
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GapSight - 跨学科知识盲区探测工具",
    description="利用文献共现网络与结构洞算法，自动探测并可视化跨学科知识盲区",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = project_root / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


@app.get("/")
async def read_root():
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "GapSight API is running. Please visit /docs for API documentation."}


@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    return ConfigResponse(
        has_api_key=settings.SEMANTIC_SCHOLAR_API_KEY is not None,
        max_papers_limit=settings.MAX_PAPERS,
        default_years_back=settings.DEFAULT_YEARS_BACK,
        scispacy_model=settings.SCISPACY_MODEL
    )


@app.post("/api/search", response_model=NetworkData)
async def search_and_analyze(request: SearchRequest):
    if not request.keywords or len(request.keywords) == 0:
        raise HTTPException(status_code=400, detail="请提供至少一个关键词")
    
    if len(request.keywords) > 2:
        raise HTTPException(status_code=400, detail="最多支持2个关键词")
    
    max_papers = min(request.max_papers or 100, settings.MAX_PAPERS)
    years_back = request.years_back or settings.DEFAULT_YEARS_BACK
    
    logger.info(f"开始搜索关键词: {request.keywords}, 论文数量: {max_papers}, 年份: {years_back}")
    
    try:
        ss_service = semantic_scholar_service
        if request.api_key:
            ss_service = SemanticScholarService(api_key=request.api_key)
        
        papers = await ss_service.search_papers(
            keywords=request.keywords,
            max_papers=max_papers,
            years_back=years_back
        )
        
        if not papers:
            raise HTTPException(status_code=404, detail="未找到相关论文，请尝试其他关键词")
        
        logger.info(f"获取到 {len(papers)} 篇论文")
        
        entities = entity_extractor.extract_entities_from_papers(
            papers=papers,
            min_count=2
        )
        
        if not entities:
            raise HTTPException(status_code=404, detail="未能从论文中提取有效学术实体，请尝试其他关键词")
        
        logger.info(f"提取到 {len(entities)} 个学术实体")
        
        cooccurrence = entity_extractor.build_cooccurrence_matrix(
            papers=papers,
            entities=entities
        )
        
        logger.info(f"构建共现矩阵完成")
        
        network_analyzer.build_network(
            papers=papers,
            entities=entities,
            cooccurrence_matrix=cooccurrence,
            keywords=request.keywords
        )
        
        network_data = network_analyzer.generate_network_data(
            keywords=request.keywords
        )
        
        logger.info(f"网络分析完成: {len(network_data.nodes)} 个节点, {len(network_data.edges)} 条边, {len(network_data.gap_pairs)} 个知识盲区")
        
        return network_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索分析过程出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")


@app.post("/api/gap-prompt", response_model=GapPromptResponse)
async def generate_gap_prompt(request: GapPromptRequest):
    if not request.concept1 or not request.concept2:
        raise HTTPException(status_code=400, detail="请提供两个概念")
    
    try:
        response = network_analyzer.generate_gap_prompt_response(request)
        return response
    except Exception as e:
        logger.error(f"生成提示词出错: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成提示词时出错: {str(e)}")


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
