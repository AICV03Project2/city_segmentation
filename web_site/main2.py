import os
import cv2
import asyncio
import numpy as np
import torch
import base64
import uvicorn
import nest_asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime
from ultralytics import YOLO
from concurrent.futures import ThreadPoolExecutor

# =========================
# 1) 설정 및 초기화
# =========================
YOLO_PT_PATH = "/content/drive/MyDrive/Colab_Notebooks/Segmentation_pro/model_save/best_v8m.pt"
MASK_BASE_PATH = "/content/drive/MyDrive/Colab_Notebooks/Segmentation_pro/road_mask"
FRONT_ABS_PATH = "/content/drive/MyDrive/Colab_Notebooks/Segmentation_pro/web_site/front"

DEVICE = "cuda:0"
IMG_SIZE = 640       # A100의 경우 640이 속도와 정확도의 최적 지점입니다.
JPEG_QUALITY = 65    # CPU 부하를 줄이기 위해 품질을 65로 최적화
USE_HALF = True      # A100(FP16 가속) 사용 필수

# 전역 상태 관리
cached_urls = {}
latest_results = {}
preloaded_masks_gpu = {}

# [병렬화] A100의 자원을 활용하기 위해 이미지 인코딩 전용 쓰레드 풀 확장
thread_executor = ThreadPoolExecutor(max_workers=24)

print(f"🚀 A100 GPU 가속 모드 가동 중 (imgsz: {IMG_SIZE})...")
model = YOLO(YOLO_PT_PATH)
model.to(DEVICE)
if USE_HALF:
    model.half()  # 모델 가중치를 FP16으로 고정

# =========================
# 2) 수명 주기 관리 (Lifespan)
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 포트 충돌 방지를 위해 실행 전 기존 프로세스 종료 권장: !fuser -k 8000/tcp
    prepare_gpu_masks()
    # 분석 엔진을 백그라운드 태스크로 분리
    analysis_task = asyncio.create_task(global_analysis_engine())
    yield
    analysis_task.cancel()
    thread_executor.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)
nest_asyncio.apply()

def prepare_gpu_masks():
    """마스크를 FP16 타입으로 GPU에 미리 로드하여 연산 속도 극대화"""
    global preloaded_masks_gpu
    if not os.path.exists(MASK_BASE_PATH): return
    for i in range(1, 7):
        for direct in ['up', 'low']:
            path = f"{MASK_BASE_PATH}/{i}_{direct}.png"
            if os.path.exists(path):
                mask_img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                mask_img = cv2.resize(mask_img, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_NEAREST)
                
                # [에러 방지] 로드 단계부터 Half(FP16)로 강제 변환
                mask_tensor = torch.from_numpy(mask_img).to(DEVICE).half() / 255.0
                preloaded_masks_gpu[f"{i}_{direct}"] = (mask_tensor > 0.5).to(dtype=torch.float16)
    print(f"✅ {len(preloaded_masks_gpu)}개 ROI 마스크 FP16 준비 완료")

# =========================
# 3) 비동기 이미지 처리 (CPU 병목 분산)
# =========================
def process_and_update(res, cid, final_data):
    """별도 쓰레드에서 이미지 시각화 및 JPEG 인코딩 수행"""
    try:
        # 1. 시각화 (CPU)
        annotated = res.plot(boxes=False, masks=True)
        # 2. JPEG 압축 (가장 무거운 작업)
        _, buffer = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        img_str = base64.b64encode(buffer).decode('utf-8')
        
        # 3. 최신 결과 업데이트
        latest_results[cid] = {
            "channel_id": cid,
            "vehicle_total_count": len(res.boxes) if res.boxes is not None else 0,
            "results": final_data,
            "encoded_image": img_str,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        pass # 인코딩 도중 발생하는 사소한 에러 무시

# =========================
# 4) 통합 분석 엔진 (GPU 배치 추론)
# =========================

async def global_analysis_engine():
    caps = {}
    while True:
        if not cached_urls:
            await asyncio.sleep(0.5)
            continue

        cids = list(cached_urls.keys())
        batch_frames = []
        active_cids = []

        # 1. 프레임 캡처 및 전처리 (Resize)
        for cid in cids:
            if cid not in caps:
                caps[cid] = cv2.VideoCapture(cached_urls[cid])
                caps[cid].set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if caps[cid].grab():
                success, frame = caps[cid].retrieve()
                if success:
                    batch_frames.append(cv2.resize(frame, (IMG_SIZE, IMG_SIZE)))
                    active_cids.append(cid)

        if not batch_frames:
            await asyncio.sleep(0.01)
            continue

        try:
            # 2. GPU Batch Inference (A100의 병렬 연산 활용)
            results = model.predict(
                source=batch_frames, 
                imgsz=IMG_SIZE, 
                device=DEVICE, 
                half=USE_HALF, 
                verbose=False
            )

            # 3. 결과 분석 및 쓰레드 위임
            for i, res in enumerate(results):
                cid = active_cids[i]
                final_data = {}

                if res.masks is not None:
                    # [에러 방지 핵심] 모든 텐서 연산 직전에 FP16으로 강제 캐스팅
                    pred_masks = res.masks.data.to(dtype=torch.float16)
                    combined_mask = torch.any(pred_masks > 0.5, dim=0).to(dtype=torch.float16)
                    
                    for direct in ['up', 'low']:
                        m_key = f"{cid}_{direct}"
                        if m_key in preloaded_masks_gpu:
                            roi = preloaded_masks_gpu[m_key].to(dtype=torch.float16)
                            
                            # 텐서 연산을 통한 점유율 계산
                            overlap = (combined_mask * roi).sum().item()
                            roi_area = roi.sum().item()
                            occ_rate = overlap / (roi_area + 1e-6)
                            
                            final_data[direct] = {
                                "occupancy_rate": round(occ_rate * 100, 1),
                                "status": "원활" if occ_rate < 0.25 else "정체" if occ_rate > 0.5 else "서행"
                            }

                # 4. 무거운 인코딩 작업은 쓰레드 풀로 전달 (Fire-and-Forget)
                thread_executor.submit(process_and_update, res, cid, final_data)

        except Exception as e:
            print(f"⚠️ 분석 루프 오류: {e}")
        
        await asyncio.sleep(0) # 즉시 다음 루프 실행

# =========================
# 5) API 엔드포인트
# =========================
class URLUpdate(BaseModel):
    urls: Dict[str, str]

@app.post("/update_urls")
async def update_urls(data: URLUpdate):
    global cached_urls
    cached_urls = {int(k): v for k, v in data.urls.items()}
    return {"status": "success"}

@app.get("/api/v1/traffic/{channel_id}")
async def get_traffic_data(channel_id: int):
    data = latest_results.get(channel_id)
    if not data: return JSONResponse(content={"error": "no data"}, status_code=503)
    res_only = data.copy()
    if "encoded_image" in res_only: del res_only["encoded_image"]
    return res_only

@app.get("/video_feed/{channel_id}")
async def video_feed(channel_id: int):
    async def frame_generator():
        while True:
            data = latest_results.get(channel_id)
            if data and "encoded_image" in data:
                img_data = base64.b64decode(data["encoded_image"])
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + img_data + b'\r\n')
            await asyncio.sleep(0.04) # 약 25 FPS
    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/")
async def read_index():
    index_path = os.path.join(FRONT_ABS_PATH, "index.html")
    if os.path.exists(index_path): return FileResponse(index_path)
    return JSONResponse(content={"error": "index.html not found"}, status_code=404)

if os.path.exists(FRONT_ABS_PATH):
    app.mount("/front", StaticFiles(directory=FRONT_ABS_PATH), name="front")

if __name__ == "__main__":
    # 실행 전 반드시 !fuser -k 8000/tcp 실행하여 포트를 비워주세요.
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)