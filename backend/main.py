import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Optional
import logging
from io import BytesIO
from datetime import datetime

from backend.config import settings
from backend.models.schemas import (
    SearchRequest,
    NetworkData,
    GapPromptRequest,
    GapPromptResponse,
    ConfigResponse,
    DataSnapshot,
    ComparisonResult,
    ComparisonDimension,
    ThresholdConfig,
    NotificationConfig,
    Alert,
    ReportRequest,
    ReportResult,
    ReportFormat
)
from backend.services import (
    semantic_scholar_service,
    SemanticScholarService,
    entity_extractor,
    network_analyzer,
    data_comparator,
    monitoring_service,
    report_service
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


# ==================== 数据快照管理 API ====================

@app.post("/api/snapshots", response_model=DataSnapshot)
async def create_snapshot(snapshot: DataSnapshot):
    try:
        saved_snapshot = data_comparator.save_snapshot(snapshot)
        logger.info(f"创建数据快照: {saved_snapshot.name} (ID: {saved_snapshot.id})")
        return saved_snapshot
    except Exception as e:
        logger.error(f"创建快照失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建快照失败: {str(e)}")


@app.get("/api/snapshots", response_model=List[DataSnapshot])
async def list_snapshots():
    return data_comparator.list_snapshots()


@app.get("/api/snapshots/{snapshot_id}", response_model=DataSnapshot)
async def get_snapshot(snapshot_id: str):
    snapshot = data_comparator.get_snapshot(snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="快照不存在")
    return snapshot


@app.delete("/api/snapshots/{snapshot_id}")
async def delete_snapshot(snapshot_id: str):
    if data_comparator.delete_snapshot(snapshot_id):
        return {"message": "快照已删除", "id": snapshot_id}
    raise HTTPException(status_code=404, detail="快照不存在")


# ==================== 多源数据交叉对标 API ====================

@app.post("/api/compare", response_model=ComparisonResult)
async def compare_snapshots(
    snapshot_ids: List[str] = Body(..., embed=True),
    dimensions: Optional[List[ComparisonDimension]] = Body(None)
):
    if len(snapshot_ids) < 2:
        raise HTTPException(status_code=400, detail="需要至少两个快照进行比较")
    
    try:
        result = data_comparator.compare_snapshots(snapshot_ids, dimensions)
        logger.info(f"完成快照比较: {snapshot_ids}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"快照比较失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"比较失败: {str(e)}")


# ==================== 阈值配置管理 API ====================

@app.post("/api/thresholds", response_model=ThresholdConfig)
async def create_threshold(threshold: ThresholdConfig):
    try:
        saved_threshold = monitoring_service.create_threshold(threshold)
        logger.info(f"创建阈值配置: {saved_threshold.name}")
        return saved_threshold
    except Exception as e:
        logger.error(f"创建阈值失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建阈值失败: {str(e)}")


@app.get("/api/thresholds", response_model=List[ThresholdConfig])
async def list_thresholds():
    return monitoring_service.list_thresholds()


@app.get("/api/thresholds/{threshold_id}", response_model=ThresholdConfig)
async def get_threshold(threshold_id: str):
    threshold = monitoring_service.get_threshold(threshold_id)
    if threshold is None:
        raise HTTPException(status_code=404, detail="阈值配置不存在")
    return threshold


@app.put("/api/thresholds/{threshold_id}", response_model=ThresholdConfig)
async def update_threshold(threshold_id: str, threshold: ThresholdConfig):
    updated = monitoring_service.update_threshold(threshold_id, threshold)
    if updated is None:
        raise HTTPException(status_code=404, detail="阈值配置不存在")
    return updated


@app.delete("/api/thresholds/{threshold_id}")
async def delete_threshold(threshold_id: str):
    if monitoring_service.delete_threshold(threshold_id):
        return {"message": "阈值配置已删除", "id": threshold_id}
    raise HTTPException(status_code=404, detail="阈值配置不存在")


# ==================== 通知配置管理 API ====================

@app.post("/api/notifications", response_model=NotificationConfig)
async def create_notification(notification: NotificationConfig):
    try:
        saved_notification = monitoring_service.create_notification(notification)
        logger.info(f"创建通知配置: {saved_notification.name}")
        return saved_notification
    except Exception as e:
        logger.error(f"创建通知配置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建通知配置失败: {str(e)}")


@app.get("/api/notifications", response_model=List[NotificationConfig])
async def list_notifications():
    return monitoring_service.list_notifications()


@app.get("/api/notifications/{notification_id}", response_model=NotificationConfig)
async def get_notification(notification_id: str):
    notification = monitoring_service.get_notification(notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="通知配置不存在")
    return notification


@app.put("/api/notifications/{notification_id}", response_model=NotificationConfig)
async def update_notification(notification_id: str, notification: NotificationConfig):
    updated = monitoring_service.update_notification(notification_id, notification)
    if updated is None:
        raise HTTPException(status_code=404, detail="通知配置不存在")
    return updated


@app.delete("/api/notifications/{notification_id}")
async def delete_notification(notification_id: str):
    if monitoring_service.delete_notification(notification_id):
        return {"message": "通知配置已删除", "id": notification_id}
    raise HTTPException(status_code=404, detail="通知配置不存在")


# ==================== 预警检查 API ====================

@app.post("/api/monitor/check/{snapshot_id}", response_model=List[Alert])
async def check_snapshot_thresholds(snapshot_id: str):
    snapshot = data_comparator.get_snapshot(snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="快照不存在")
    
    try:
        alerts = monitoring_service.check_snapshot(snapshot)
        logger.info(f"检查快照 {snapshot_id}，触发 {len(alerts)} 个预警")
        return alerts
    except Exception as e:
        logger.error(f"预警检查失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"预警检查失败: {str(e)}")


@app.get("/api/alerts", response_model=List[Alert])
async def get_alerts(
    include_read: bool = Query(False, description="是否包含已读预警"),
    limit: int = Query(100, description="返回数量限制", ge=1, le=1000)
):
    return monitoring_service.get_alerts(include_read=include_read, limit=limit)


@app.put("/api/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str):
    if monitoring_service.mark_alert_read(alert_id):
        return {"message": "预警已标记为已读", "id": alert_id}
    raise HTTPException(status_code=404, detail="预警不存在")


@app.put("/api/alerts/read-all")
async def mark_all_alerts_read():
    count = monitoring_service.mark_all_alerts_read()
    return {"message": f"已标记 {count} 个预警为已读", "count": count}


@app.get("/api/monitor/summary")
async def get_monitoring_summary():
    return monitoring_service.get_monitoring_summary()


# ==================== 报告生成 API ====================

@app.post("/api/reports/generate", response_model=ReportResult)
async def generate_report(request: ReportRequest):
    if len(request.snapshot_ids) == 0:
        raise HTTPException(status_code=400, detail="需要至少一个快照生成报告")
    
    snapshots = []
    for sid in request.snapshot_ids:
        snapshot = data_comparator.get_snapshot(sid)
        if snapshot is None:
            raise HTTPException(status_code=404, detail=f"快照不存在: {sid}")
        snapshots.append(snapshot)
    
    comparison_result = None
    if len(snapshots) >= 2:
        try:
            comparison_result = data_comparator.compare_snapshots(request.snapshot_ids)
        except Exception as e:
            logger.warning(f"报告生成时比较失败: {str(e)}")
    
    try:
        report = report_service.generate_report(
            request=request,
            snapshots=snapshots,
            comparison_result=comparison_result
        )
        logger.info(f"生成报告: {report.title} (ID: {report.report_id})")
        return report
    except Exception as e:
        logger.error(f"报告生成失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"报告生成失败: {str(e)}")


@app.get("/api/reports", response_model=List[dict])
async def list_reports():
    return report_service.list_reports()


@app.get("/api/reports/{report_id}")
async def download_report(report_id: str):
    report = report_service.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    if report.content is None:
        raise HTTPException(status_code=404, detail="报告内容不存在")
    
    media_types = {
        ReportFormat.PDF: "application/pdf",
        ReportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ReportFormat.JSON: "application/json"
    }
    
    media_type = media_types.get(report.format, "application/octet-stream")
    
    if report.format == ReportFormat.PDF:
        file_extension = "pdf"
    elif report.format == ReportFormat.EXCEL:
        file_extension = "csv"
    else:
        file_extension = "json"
    
    filename = f"{report.title.replace(' ', '_')}.{file_extension}"
    
    return StreamingResponse(
        BytesIO(report.content),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Content-Length": str(len(report.content))
        }
    )


@app.delete("/api/reports/{report_id}")
async def delete_report(report_id: str):
    if report_service.delete_report(report_id):
        return {"message": "报告已删除", "id": report_id}
    raise HTTPException(status_code=404, detail="报告不存在")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
