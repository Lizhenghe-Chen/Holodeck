from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import uuid
import os
import asyncio
from concurrent.futures import ProcessPoolExecutor
import compress_json
from ai2holodeck.constants import HOLODECK_BASE_DATA_DIR, OBJATHOR_ASSETS_DIR
from ai2holodeck.generation.holodeck import Holodeck

app = FastAPI(title="Holodeck Scene Generator API")

# 使用进程池处理多个并发请求
process_pool = ProcessPoolExecutor(max_workers=4)

# 存储任务状态
tasks_status = {}


class SceneRequest(BaseModel):
    query: str
    add_ceiling: bool = False
    generate_image: bool = True
    generate_video: bool = False
    use_constraint: bool = True
    use_milp: bool = False
    random_selection: bool = False
    single_room: bool = False
    used_assets: List[str] = []


class TaskResponse(BaseModel):
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    message: str


def generate_scene_worker(
    query: str,
    task_id: str,
    openai_api_key: str,
    openai_api_base: str,
    model_name: str,
    add_ceiling: bool,
    generate_image: bool,
    generate_video: bool,
    use_constraint: bool,
    use_milp: bool,
    random_selection: bool,
    single_room: bool,
    used_assets: List[str],
):
    """独立进程中执行场景生成"""
    try:
        # 在子进程中初始化 Holodeck
        model = Holodeck(
            openai_api_key=openai_api_key,
            openai_org=None,
            openai_api_base=openai_api_base,
            model_name=model_name,
            objaverse_asset_dir=OBJATHOR_ASSETS_DIR,
            single_room=single_room,
        )

        scene = model.get_empty_scene()
        save_dir = os.path.join(HOLODECK_BASE_DATA_DIR, "scenes")

        _, result_dir = model.generate_scene(
            scene=scene,
            query=query,
            save_dir=save_dir,
            used_assets=used_assets,
            add_ceiling=add_ceiling,
            generate_image=generate_image,
            generate_video=generate_video,
            add_time=True,
            use_constraint=use_constraint,
            random_selection=random_selection,
            use_milp=use_milp,
        )

        # 读取生成的 JSON
        query_name = query.replace(" ", "_").replace("'", "")[:30]
        json_files = [f for f in os.listdir(result_dir) if f.endswith(".json")]
        if json_files:
            scene_json = compress_json.load(os.path.join(result_dir, json_files[0]))
            return {
                "status": "completed",
                "scene": scene_json,
                "output_dir": result_dir,
            }
        else:
            return {"status": "failed", "error": "Scene JSON not found"}

    except Exception as e:
        return {"status": "failed", "error": str(e)}


@app.post("/generate", response_model=TaskResponse)
async def generate_scene(request: SceneRequest, background_tasks: BackgroundTasks):
    """
    异步提交场景生成任务
    
    返回 task_id 用于查询生成结果
    """
    task_id = str(uuid.uuid4())
    tasks_status[task_id] = {"status": "pending", "result": None}

    # 从环境变量获取配置
    openai_api_key = os.environ.get("OPENAI_API_KEY", "sk-")
    openai_api_base = os.environ.get("OPENAI_API_BASE", "http://10.120.47.138:8000/v1")
    model_name = os.environ.get("LLM_MODEL_NAME", "./Qwen3-VL-8B-Instruct")

    # 后台执行任务
    async def run_task():
        tasks_status[task_id]["status"] = "processing"
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            process_pool,
            generate_scene_worker,
            request.query,
            task_id,
            openai_api_key,
            openai_api_base,
            model_name,
            request.add_ceiling,
            request.generate_image,
            request.generate_video,
            request.use_constraint,
            request.use_milp,
            request.random_selection,
            request.single_room,
            request.used_assets,
        )
        tasks_status[task_id]["result"] = result
        tasks_status[task_id]["status"] = result["status"]

    background_tasks.add_task(run_task)

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="Scene generation task submitted",
    )


@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """查询任务状态"""
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks_status[task_id]
    return {
        "task_id": task_id,
        "status": task["status"],
        "result": task.get("result"),
    }


@app.get("/result/{task_id}")
async def get_scene_result(task_id: str):
    """获取生成的场景 JSON"""
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks_status[task_id]

    if task["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task is {task['status']}, not yet completed",
        )

    result = task["result"]
    if "scene" not in result:
        raise HTTPException(status_code=500, detail="Scene data not available")

    return {
        "task_id": task_id,
        "scene": result["scene"],
        "output_dir": result.get("output_dir"),
    }


@app.on_event("shutdown")
def shutdown_event():
    """关闭进程池"""
    process_pool.shutdown(wait=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)