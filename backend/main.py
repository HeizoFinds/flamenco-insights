import os
import sys
import httpx
import json
import configparser
import asyncio
import re
from datetime import datetime
from collections import Counter
from typing import List
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

CONFIG_FILE = "config.ini"

def create_default_config():
    config = configparser.ConfigParser()
    config['Settings'] = {
        '# 请在这里填入你的 Flamenco Manager 的完整地址 (例如: http://192.168.1.100:8080)': '',
        'flamenco_url': 'http://localhost:8080',
        '# Web UI 的监听端口，确保这个端口没有被其他程序占用': '',
        'listen_port': '8000'
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
        config.write(configfile)
    print(f"'{CONFIG_FILE}' not found. A default one has been created.")
    print("Application will run with default settings. You can edit this file later to change them.")

config = configparser.ConfigParser()
if not os.path.exists(CONFIG_FILE):
    create_default_config()
config.read(CONFIG_FILE, encoding='utf-8')

try:
    FLAMENCO_URL = config.get('Settings', 'flamenco_url')
    LISTEN_PORT = config.getint('Settings', 'listen_port')
except (configparser.NoSectionError, configparser.NoOptionError):
    print(f"'{CONFIG_FILE}' is corrupted. Recreating it with default values.")
    create_default_config()
    config.read(CONFIG_FILE, encoding='utf-8')
    FLAMENCO_URL = config.get('Settings', 'flamenco_url')
    LISTEN_PORT = config.getint('Settings', 'listen_port')

if not FLAMENCO_URL.strip():
    print(f"错误: '{CONFIG_FILE}' 中的 'flamenco_url' 不能为空。请填写正确的地址后重启程序。")
    input("按回车键退出...")
    sys.exit()

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

app = FastAPI(
    title="Flamenco Insights API",
    description="A proxy and data processing API for Flamenco",
    version="1.2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
async_client = httpx.AsyncClient(base_url=FLAMENCO_URL, timeout=15.0)
NOTES_FILE = "worker_notes.json"

class NotePayload(BaseModel):
    note: str

async def read_notes():
    with open(NOTES_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    data = json.loads(content)
    return data

async def write_notes(notes_data: dict):
    try:
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(notes_data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"Error writing notes file: {e}")

class JobStatusPayload(BaseModel):
    status: str

class WorkerActionPayload(BaseModel):
    worker_ids: List[str]
    action: str

@app.get("/api/jobs")
async def get_all_jobs():
    try:
        response = await async_client.get("/api/v3/jobs")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Could not connect to Flamenco Manager: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Error from Flamenco API: {e.response.text}")

@app.get("/api/jobs/with-progress")
async def get_jobs_with_progress():
    try:
        jobs_resp = await async_client.get("/api/v3/jobs")
        jobs_resp.raise_for_status()
        jobs_data = jobs_resp.json().get("jobs", [])

        jobs_to_enrich = [job for job in jobs_data if job.get("status") in ["active", "paused", "queued", "error"]]

        async def get_task_summary(job_id):
            try:
                tasks_resp = await async_client.get(f"/api/v3/jobs/{job_id}/tasks")
                tasks_resp.raise_for_status()
                tasks_list = tasks_resp.json().get("tasks", [])
                total = len(tasks_list)
                completed = sum(1 for t in tasks_list if t.get("status") == "completed")
                return {"total": total, "completed": completed}
            except Exception:
                return {"total": 0, "completed": 0}

        tasks_requests = [get_task_summary(job["id"]) for job in jobs_to_enrich]
        tasks_summaries = await asyncio.gather(*tasks_requests)

        job_to_summary_map = {job["id"]: summary for job, summary in zip(jobs_to_enrich, tasks_summaries)}
        
        for job in jobs_data:
            if job["id"] in job_to_summary_map:
                summary = job_to_summary_map[job["id"]]
                job["tasks_total"] = summary["total"]
                job["tasks_completed"] = summary["completed"]

        return {"jobs": jobs_data}

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Flamenco API 错误: {e.response.text}")

@app.post("/api/jobs/{job_id}/status")
async def set_job_status(job_id: str, payload: JobStatusPayload):
    flamenco_status_map = {
        "pause": "paused",
        "cancel": "canceled",
        "requeue": "queued",
        "resume": "active"
    }
    status_to_set = flamenco_status_map.get(payload.status)
    if not status_to_set:
        raise HTTPException(status_code=400, detail="无效的任务操作")
    try:
        response = await async_client.post(f"/api/v3/jobs/{job_id}/setstatus", json={"status": status_to_set,"reason": f"Action '{payload.status}' triggered from Flamenco Insights UI"})
        response.raise_for_status()
        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": f"Job status change to '{payload.status}' accepted."}
        )
    except httpx.HTTPStatusError as e:
        error_detail = f"Flamenco API Error: {e.response.status_code} - {e.response.text}"
        raise HTTPException(status_code=e.response.status_code, detail=error_detail)

@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    try:
        response = await async_client.delete(f"/api/v3/jobs/{job_id}")
        response.raise_for_status()
        return {"status": "success", "message": "任务已标记为删除"}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Flamenco API 错误: {e.response.text}")


@app.get("/api/jobs/{job_id}/details")
async def get_job_details(job_id: str):
    try:
        job_info_req = async_client.get(f"/api/v3/jobs/{job_id}")
        tasks_summary_req = async_client.get(f"/api/v3/jobs/{job_id}/tasks")
        job_info_resp, tasks_summary_resp = await asyncio.gather(job_info_req, tasks_summary_req)
        
        job_info_resp.raise_for_status()
        tasks_summary_resp.raise_for_status()
        
        job_info = job_info_resp.json()
        tasks_summary_data = tasks_summary_resp.json().get('tasks', [])

        worker_counts = Counter()
        frame_times = []
        
        detail_requests = []
        for task_summary in tasks_summary_data:
            task_id = task_summary.get('id')
            if task_id:
                detail_requests.append(async_client.get(f"/api/v3/tasks/{task_id}"))

        if detail_requests:
            detailed_task_responses = await asyncio.gather(*detail_requests, return_exceptions=True)
            for detailed_resp in detailed_task_responses:
                if isinstance(detailed_resp, Exception) or detailed_resp.status_code != 200: continue
                task_detail = detailed_resp.json()
                if task_detail.get('status') == 'completed':
                    worker_name = task_detail.get('worker', {}).get('name', 'Unknown')
                    worker_counts[worker_name] += 1
                    try:
                        frame_match = re.search(r'\d+$', task_detail.get('name', ''))
                        if not frame_match: continue
                        frame_number = int(frame_match.group(0))
                        start_str, end_str = task_detail.get('created'), task_detail.get('updated')
                        if start_str and end_str:
                            start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                            end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                            duration = (end_time - start_time).total_seconds()
                            if duration >= 0:
                                frame_times.append({"frame": frame_number, "time": round(duration, 2), "worker": worker_name})
                    except (ValueError, TypeError): continue
        
        frame_times.sort(key=lambda x: x['frame'])
        return {
            "job_info": job_info,
            "pie_chart_data": [{"name": name, "value": count} for name, count in worker_counts.items()],
            "tasks_summary": { "total": len(tasks_summary_data), "completed": sum(1 for t in tasks_summary_data if t.get('status') == 'completed'), "rendering": sum(1 for t in tasks_summary_data if t.get('status') == 'active'), "queued": sum(1 for t in tasks_summary_data if t.get('status') == 'queued'), "failed": sum(1 for t in tasks_summary_data if t.get('status') == 'error') },
            "frame_times": frame_times
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing job details: {str(e)}")


@app.get("/api/workers")
async def get_all_workers():
    try:
        response = await async_client.get("/api/v3/worker-mgt/workers")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Flamenco API 错误: {e.response.text}")
@app.get("/api/workers/notes")
async def get_all_worker_notes():
    if not os.path.exists(NOTES_FILE):
        await write_notes({})
        return {}
    try:
        notes = await read_notes()
        return notes
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading or parsing notes file: {e}, returning empty notes.")
        return {}

@app.post("/api/workers/{worker_id}/note")
async def save_worker_note(worker_id: str, payload: NotePayload):
    notes = {}
    if os.path.exists(NOTES_FILE):
        try:
            notes = await read_notes()
        except (json.JSONDecodeError, IOError):
            print("Notes file is corrupted, starting fresh.")
            notes = {}

    notes[worker_id] = payload.note
    await write_notes(notes)
    return {"status": "success", "worker_id": worker_id, "note": payload.note}
@app.get("/api/workers/{worker_id}")
async def get_worker_details(worker_id: str):
    try:
        response = await async_client.get(f"/api/v3/worker-mgt/workers/{worker_id}")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Flamenco API 错误: {e.response.text}")

@app.post("/api/workers/batch-action")
async def worker_batch_action(payload: WorkerActionPayload):
    # New mapping based on the Swagger UI screenshot
    action_map = {
        'wake_up':            {'status': 'awake', 'is_lazy': False},
        'sleep_after_task':   {'status': 'asleep', 'is_lazy': True},
        'sleep_immediately':  {'status': 'asleep', 'is_lazy': False},
        'shutdown_after_task':{'status': 'offline', 'is_lazy': True},
        'shutdown_immediately':{'status': 'offline', 'is_lazy': False},
    }
    results = []

    async def perform_action(worker_id):
        try:
            if payload.action == 'remove':
                resp = await async_client.delete(f"/api/v3/worker-mgt/workers/{worker_id}")
            elif payload.action in action_map:
                request_body = action_map[payload.action]
                resp = await async_client.post(f"/api/v3/worker-mgt/workers/{worker_id}/setstatus", json=request_body)
            else:
                return {"worker_id": worker_id, "status": "error", "detail": "无效的操作"}

            resp.raise_for_status()
            return {"worker_id": worker_id, "status": "success"}
        except httpx.HTTPStatusError as exc:
            error_detail = f"API Error {exc.response.status_code}: {exc.response.text}"
            return {"worker_id": worker_id, "status": "error", "detail": error_detail}
        except Exception as exc:
            return {"worker_id": worker_id, "status": "error", "detail": str(exc)}

    tasks = [perform_action(wid) for wid in payload.worker_ids]
    results = await asyncio.gather(*tasks)
    
    return {"results": results}


dist_dir = resource_path("dist")
assets_dir = os.path.join(dist_dir, "assets")
app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join(dist_dir, 'favicon.ico'))
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    return FileResponse(os.path.join(dist_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    print(f"Starting server on http://127.0.0.1:{LISTEN_PORT}")
    print(f"Connecting to Flamenco Manager at: {FLAMENCO_URL}")
    uvicorn.run(app, host="0.0.0.0", port=LISTEN_PORT, log_config=None)